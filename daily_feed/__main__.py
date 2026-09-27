"""Build today's digest:  python -m daily_feed [--config feeds.yaml]"""
from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from .fetch import fetch_category
from .notify import send_daily_email
from .render import write_all
from .summarize import Summarizer


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="feeds.yaml")
    ap.add_argument("--out", default=".")
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    tz = ZoneInfo(os.environ.get("DIGEST_TZ") or "America/Los_Angeles")
    today = datetime.now(tz).date()
    summarizer = Summarizer()
    if not summarizer.enabled:
        print("ANTHROPIC_API_KEY not set: building a headlines-only digest.")

    sections = []
    for cat in cfg["categories"]:
        print(f"• {cat['name']}")
        items = fetch_category(cat["feeds"], cfg.get("lookback_hours", 30), cfg.get("max_items_per_feed", 10))
        print(f"  {len(items)} candidate stories")
        result = summarizer.category(cat["name"], cat.get("focus", ""), items, cfg.get("stories_per_category", 5))
        sections.append({"id": cat["id"], "name": cat["name"], "name_zh": cat.get("name_zh", ""), **result})

    reflection, reflection_zh = summarizer.reflection(sections)
    site_url = os.environ.get("SITE_URL", "")
    write_all(Path(args.out), today, reflection, reflection_zh, sections, site_url)
    print(f"Wrote digest for {today}")
    send_daily_email(today, reflection, reflection_zh, sections, site_url)


if __name__ == "__main__":
    main()
