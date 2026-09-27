"""Turn raw headlines into a short, thoughtful digest with Claude.

If ANTHROPIC_API_KEY is not set, falls back to the most recent headlines.
"""
from __future__ import annotations

import json
import os
import re
from datetime import date

from .fetch import Item

MODEL = os.environ.get("ANTHROPIC_MODEL") or "claude-sonnet-5"

SYSTEM = """You are the editor of a private daily digest for one reader: a thoughtful \
software engineer who wants to stay informed and to grow in perspective and compassion. \
Be accurate and even-handed. Never invent facts beyond the headlines and snippets you \
are given; if a snippet is thin, say less rather than guess. Write plainly, without \
hype, and remember that behind conflict and economic stories are real people. \
Respond with JSON only, no prose and no code fences."""

CATEGORY_PROMPT = """Section: {name}
Editorial focus: {focus}

Today's candidate stories as JSON (index, title, source, snippet):
{items}

Pick the {n} most significant stories for this reader (fewer if there aren't {n} good ones). \
Avoid near-duplicates about the same event. Return JSON of this shape:
{{
  "overview": "2-3 sentences on what matters in this area today",
  "stories": [
    {{
      "index": <int from the list>,
      "why_it_matters": "1-2 sentences",
      "perspective": "1 sentence on who is affected or whose viewpoint is easy to miss, or an empty string"
    }}
  ]
}}"""

REFLECTION_PROMPT = """Today's section overviews:
{overviews}

Write one short reflection for the reader to carry through the day: a question or \
thought (max 40 words) that connects something in today's news to empathy, humility, \
or seeing the world through someone else's eyes. Avoid preachiness and platitudes. \
Return JSON: {{"reflection": "..."}}"""

TREND_PROMPT = """Category: {name}

Here is a chronological log of this section's daily "what matters" overview, oldest first:
{entries}

In 3-5 sentences, describe how this topic has been trending: what themes are recurring \
or escalating, what has resolved or faded, and anything notably different in the most \
recent entries compared to earlier ones. If there isn't enough history yet to see a real \
trend, say so plainly instead of inventing one. Return JSON: {{"trend": "..."}}"""


def _parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(text)


def _fallback(items: list[Item], n: int) -> dict:
    return {
        "overview": "",
        "stories": [{"item": i, "why_it_matters": "", "perspective": ""} for i in items[:n]],
    }


class Summarizer:
    def __init__(self) -> None:
        self.client = None
        if os.environ.get("ANTHROPIC_API_KEY"):
            import anthropic

            self.client = anthropic.Anthropic()

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def _ask(self, prompt: str, max_tokens: int = 2000) -> dict:
        resp = self.client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
        return _parse_json(text)

    def category(self, name: str, focus: str, items: list[Item], n: int) -> dict:
        if not items:
            return {"overview": "", "stories": []}
        if not self.enabled:
            return _fallback(items, n)
        candidates = items[:40]
        payload = json.dumps(
            [
                {"index": idx, "title": it.title, "source": it.source, "snippet": it.summary}
                for idx, it in enumerate(candidates)
            ],
            ensure_ascii=False,
        )
        try:
            data = self._ask(CATEGORY_PROMPT.format(name=name, focus=focus, items=payload, n=n))
        except Exception as e:  # one bad section shouldn't sink the whole digest
            print(f"  ! summarizing {name} failed: {e}")
            return _fallback(items, n)
        stories = []
        for s in data.get("stories", []):
            idx = s.get("index")
            if isinstance(idx, int) and 0 <= idx < len(candidates):
                stories.append({**s, "item": candidates[idx]})
        return {"overview": data.get("overview", ""), "stories": stories[:n]}

    def reflection(self, sections: list[dict]) -> str:
        if not self.enabled:
            return ""
        overviews = "\n".join(f"- {s['name']}: {s['overview']}" for s in sections if s["overview"])
        if not overviews:
            return ""
        try:
            return self._ask(REFLECTION_PROMPT.format(overviews=overviews), 300).get("reflection", "")
        except Exception as e:
            print(f"  ! reflection failed: {e}")
            return ""

    def trend(self, name: str, entries: list[tuple[date, str]]) -> str:
        if not self.enabled or not entries:
            return ""
        formatted = "\n".join(f"- {d.isoformat()}: {overview}" for d, overview in entries)
        try:
            return self._ask(TREND_PROMPT.format(name=name, entries=formatted), 500).get("trend", "")
        except Exception as e:
            print(f"  ! trend for {name} failed: {e}")
            return ""
