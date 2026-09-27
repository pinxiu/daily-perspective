"""Build and email the weekly trend summary:  python -m daily_feed.weekly"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .notify import send_weekly_email
from .summarize import Summarizer
from .trends import load_history


def main() -> None:
    root = Path(".")
    digests_dir = root / "digests"
    tz = ZoneInfo(os.environ.get("DIGEST_TZ") or "America/Los_Angeles")
    today = datetime.now(tz).date()

    summarizer = Summarizer()
    if not summarizer.enabled:
        print("ANTHROPIC_API_KEY not set: skipping weekly trends (nothing to summarize without it).")
        return

    history = load_history(digests_dir)
    if not history:
        print("No archived digests yet: skipping weekly trends.")
        return

    trends = {}
    for name, entries in history.items():
        print(f"• {name} ({len(entries)} days of history)")
        t = summarizer.trend(name, entries)
        if t:
            trends[name] = t

    if not trends:
        print("No trends produced.")
        return

    weekly_dir = digests_dir / "weekly"
    weekly_dir.mkdir(exist_ok=True)
    lines = [f"# Weekly trends — {today.isoformat()}", ""]
    for name, t in trends.items():
        lines += [f"## {name}", "", t, ""]
    (weekly_dir / f"{today.isoformat()}.md").write_text("\n".join(lines), encoding="utf-8")

    send_weekly_email(today, trends)
    print(f"Wrote weekly trends for {today}")


if __name__ == "__main__":
    main()
