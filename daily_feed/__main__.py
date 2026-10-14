"""Build today's digest:  python -m daily_feed [--config feeds.yaml]"""
from __future__ import annotations

import argparse
import os
import re
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from .audio import build_audio
from .fetch import Item, fetch_category
from .notify import send_daily_email
from .render import write_all
from .summarize import Summarizer


def _force() -> bool:
    """Rebuild an existing day on manual "Run workflow" runs or when FORCE is set."""
    return bool(os.environ.get("FORCE")) or os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"


_ITEM = re.compile(r"^- \*\*\[(.+?)\]\((\S+?)\)\*\* \((.*)\)\s*$")


def _archived_items(md_path: Path, categories: list[dict]) -> dict[str, list[Item]]:
    """Recover a past day's stories from its Markdown archive (for --rebuild)."""
    by_name = {c["name"]: c["id"] for c in categories}
    items: dict[str, list[Item]] = {c["id"]: [] for c in categories}
    current = None
    for line in md_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            heading = line[3:].strip()
            current = next((cid for name, cid in by_name.items() if heading.startswith(name)), None)
        elif current and (m := _ITEM.match(line)):
            items[current].append(Item(title=m.group(1), url=m.group(2), source=m.group(3),
                                       summary="", published=None))
    return items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="feeds.yaml")
    ap.add_argument("--out", default=".")
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    tz = ZoneInfo(os.environ.get("DIGEST_TZ") or "America/Los_Angeles")
    today = datetime.now(tz).date()
    rebuild = os.environ.get("REBUILD_DATE", "").strip()
    archived = None
    if rebuild:
        # Re-summarize a past day from its archived headlines (no feed fetch, no email).
        today = date.fromisoformat(rebuild)
        md = Path(args.out) / "digests" / f"{rebuild}.md"
        archived = _archived_items(md, cfg["categories"])
        print(f"Rebuilding {rebuild} from {md}")
    if not rebuild and (Path(args.out) / "digests" / f"{today.isoformat()}.md").exists() and not _force():
        print(f"Digest for {today} already exists; set FORCE=1 to rebuild. Skipping (no API calls).")
        return
    summarizer = Summarizer()
    if not summarizer.enabled:
        print("ANTHROPIC_API_KEY not set: building a headlines-only digest.")

    sections = []
    for cat in cfg["categories"]:
        print(f"• {cat['name']}")
        if archived is not None:
            items = archived.get(cat["id"], [])
        else:
            items = fetch_category(cat["feeds"], cfg.get("lookback_hours", 30), cfg.get("max_items_per_feed", 10))
        print(f"  {len(items)} candidate stories")
        result = summarizer.category(cat["name"], cat.get("focus", ""), items, cfg.get("stories_per_category", 5))
        sections.append({"id": cat["id"], "name": cat["name"], "name_zh": cat.get("name_zh", ""), **result})

    reflection = summarizer.reflection(sections)
    reflection_zh = summarizer.translate_day(sections, reflection)
    if summarizer.enabled:
        print(f"Tokens used: {summarizer.usage['in']} in / {summarizer.usage['out']} out")
    site_url = os.environ.get("SITE_URL", "")
    print("• Narrating")
    audio = build_audio(Path(args.out) / "docs", today, reflection, reflection_zh, sections,
                        cfg.get("voices"))
    write_all(Path(args.out), today, reflection, reflection_zh, sections, site_url, audio)
    print(f"Wrote digest for {today}")
    if not rebuild:
        send_daily_email(today, reflection, reflection_zh, sections, site_url)


if __name__ == "__main__":
    main()
