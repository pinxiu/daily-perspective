"""Turn raw headlines into a short, thoughtful digest with Claude.

Token budget, per day:
  * one editorial call per section (English only, compact input)
  * one small reflection call
  * ONE translation call for the whole day, on a cheaper model
If ANTHROPIC_API_KEY is not set, falls back to the most recent headlines.
"""
from __future__ import annotations

import json
import os
import re
from datetime import date

from .fetch import Item

MODEL = os.environ.get("ANTHROPIC_MODEL") or "claude-sonnet-5"
TRANSLATE_MODEL = os.environ.get("TRANSLATE_MODEL") or "claude-haiku-4-5-20251001"
MAX_CANDIDATES = 25     # stories shown to the editor per section
SNIPPET_CHARS = 200     # feed snippet length sent to the editor

SYSTEM = """You edit a private daily news digest for a thoughtful software engineer who \
wants to stay informed and grow in perspective and compassion. Be accurate and \
even-handed; never invent facts beyond the given headlines and snippets. Write plainly, \
in English, remembering that real people are behind conflict and economic stories. \
Reply with JSON only."""

CATEGORY_PROMPT = """Section: {name}
Focus: {focus}
Candidates [index, title, source, snippet]:
{items}

Pick up to {n} most significant stories, no near-duplicates. JSON:
{{"overview":"2-3 sentences on what matters today","stories":[{{"i":<index>,"why":"1-2 sentences on why it matters","lens":"1 sentence on who is affected or whose view is easy to miss, or \\"\\""}}]}}"""

REFLECTION_PROMPT = """Today's overviews:
{overviews}

One reflection (max 40 words) for the reader to carry through the day: a question or \
thought linking today's news to empathy, humility, or seeing through someone else's \
eyes. No platitudes. JSON: {{"r":"..."}}"""

TRANSLATE_SYSTEM = """Translate English news-digest text into natural, fluent Simplified \
Chinese. Keep names, numbers and facts exact. Reply with JSON only."""

TRANSLATE_PROMPT = """Translate each value into Simplified Chinese. Return a JSON object \
with exactly the same keys.
{payload}"""

TREND_PROMPT = """Daily "what matters" overviews per section, oldest first:
{entries}

For each section, write 3-5 sentences on how it has been trending: recurring or \
escalating themes, what faded, what is new recently. If there isn't enough history, \
say so plainly. JSON: {{"<section name>":"..."}}"""

CJK = re.compile(r"[\u3400-\u9fff]")


def has_cjk(text: str) -> bool:
    return bool(CJK.search(text or ""))


def _parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(text)


def _compact(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _story(item: Item, why: str = "", lens: str = "") -> dict:
    return {"item": item, "title_zh": "", "why_it_matters": why, "why_it_matters_zh": "",
            "perspective": lens, "perspective_zh": ""}


def _fallback(items: list[Item], n: int) -> dict:
    return {"overview": "", "overview_zh": "", "stories": [_story(i) for i in items[:n]]}


class Summarizer:
    def __init__(self) -> None:
        self.client = None
        self.usage = {"in": 0, "out": 0}
        if os.environ.get("ANTHROPIC_API_KEY"):
            import anthropic

            # Only needed for an org-wide key not scoped to one workspace.
            workspace_id = os.environ.get("ANTHROPIC_WORKSPACE_ID")
            headers = {"anthropic-workspace-id": workspace_id} if workspace_id else None
            self.client = anthropic.Anthropic(default_headers=headers)

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def _ask(self, prompt: str, max_tokens: int, system: str = SYSTEM, model: str = MODEL) -> dict:
        resp = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        self.usage["in"] += resp.usage.input_tokens
        self.usage["out"] += resp.usage.output_tokens
        if resp.stop_reason == "max_tokens":
            raise RuntimeError(f"{model} hit max_tokens={max_tokens}; output truncated")
        text = "".join(b.text for b in resp.content if b.type == "text")
        return _parse_json(text)

    # ---- daily ----

    def category(self, name: str, focus: str, items: list[Item], n: int) -> dict:
        """English-only section. Chinese is added later by translate_day()."""
        if not items:
            return {"overview": "", "overview_zh": "", "stories": []}
        if not self.enabled:
            return _fallback(items, n)
        candidates = items[:MAX_CANDIDATES]
        rows = [[i, it.title, it.source, it.summary[:SNIPPET_CHARS]] for i, it in enumerate(candidates)]
        prompt = CATEGORY_PROMPT.format(name=name, focus=" ".join(focus.split()), items=_compact(rows), n=n)
        try:
            data = self._ask(prompt, 1500)
            if self._mixed(data):
                print(f"  ! {name}: non-English text in English fields, retrying")
                data = self._ask(prompt + "\nAll text must be English.", 1500)
        except Exception as e:  # one bad section shouldn't sink the whole digest
            print(f"  ! summarizing {name} failed: {e}")
            return _fallback(items, n)
        stories = []
        for st in data.get("stories", [])[:n]:
            i = st.get("i")
            if isinstance(i, int) and 0 <= i < len(candidates):
                stories.append(_story(candidates[i], st.get("why", ""), st.get("lens", "")))
        return {"overview": data.get("overview", ""), "overview_zh": "", "stories": stories}

    @staticmethod
    def _mixed(data: dict) -> bool:
        fields = [data.get("overview", "")]
        for st in data.get("stories", []):
            fields += [st.get("why", ""), st.get("lens", "")]
        return any(has_cjk(f) for f in fields)

    def reflection(self, sections: list[dict]) -> str:
        if not self.enabled:
            return ""
        overviews = "\n".join(f"- {s['name']}: {s['overview']}" for s in sections if s["overview"])
        if not overviews:
            return ""
        try:
            r = self._ask(REFLECTION_PROMPT.format(overviews=overviews), 200).get("r", "")
            return "" if has_cjk(r) else r
        except Exception as e:
            print(f"  ! reflection failed: {e}")
            return ""

    def translate_day(self, sections: list[dict], reflection: str) -> str:
        """Fill every *_zh field in place with one cheap call; returns reflection_zh.

        Bad translations (no Chinese, or an echo of the English) are dropped so
        the page shows English alone rather than a broken pair.
        """
        if not self.enabled:
            return ""
        texts: dict[str, str] = {}
        if reflection:
            texts["r"] = reflection
        for si, s in enumerate(sections):
            if s["overview"]:
                texts[f"{si}o"] = s["overview"]
            for ti, st in enumerate(s["stories"]):
                for key, val in (("t", st["item"].title), ("w", st["why_it_matters"]), ("l", st["perspective"])):
                    if val:
                        texts[f"{si}.{ti}{key}"] = val
        if not texts:
            return ""
        # max_tokens is only a ceiling (you pay for tokens actually produced), so be generous.
        prompt = TRANSLATE_PROMPT.format(payload=_compact(texts))
        out = None
        for model in dict.fromkeys((TRANSLATE_MODEL, MODEL)):   # fall back to the main model
            try:
                out = self._ask(prompt, 32000, TRANSLATE_SYSTEM, model)
                break
            except Exception as e:
                print(f"  ! translation with {model} failed: {e}")
        if out is None:
            return ""
        zh = {k: v for k, v in out.items()
              if k in texts and isinstance(v, str) and has_cjk(v) and v.strip() != texts[k].strip()}
        for si, s in enumerate(sections):
            s["overview_zh"] = zh.get(f"{si}o", "")
            for ti, st in enumerate(s["stories"]):
                st["title_zh"] = zh.get(f"{si}.{ti}t", "")
                st["why_it_matters_zh"] = zh.get(f"{si}.{ti}w", "")
                st["perspective_zh"] = zh.get(f"{si}.{ti}l", "")
        return zh.get("r", "")

    # ---- weekly ----

    def trends(self, history: dict[str, list[tuple[date, str]]]) -> dict[str, str]:
        """All sections' trends in a single call."""
        if not self.enabled or not history:
            return {}
        blocks = []
        for name, entries in history.items():
            lines = "\n".join(f"{d.isoformat()}: {o}" for d, o in entries)
            blocks.append(f"## {name}\n{lines}")
        try:
            out = self._ask(TREND_PROMPT.format(entries="\n\n".join(blocks)), 400 * len(history) + 200)
        except Exception as e:
            print(f"  ! trends failed: {e}")
            return {}
        return {k: v for k, v in out.items() if k in history and isinstance(v, str) and v}
