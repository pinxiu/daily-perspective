"""Mine the archived daily digests for how each category has been trending."""
from __future__ import annotations

import re
from datetime import date

from .summarize import has_cjk
from pathlib import Path

DATE_FILE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")
SECTION_RE = re.compile(r"^## (.+)$", re.MULTILINE)


def _section_overviews(text: str) -> dict[str, str]:
    """{category name: overview paragraph} for one day's archived digest."""
    parts = SECTION_RE.split(text)
    out: dict[str, str] = {}
    for i in range(1, len(parts), 2):
        name = re.sub(r"\s*[\u3400-\u9fff].*$", "", parts[i]).strip()  # drop Chinese name
        overview_lines = []
        for line in parts[i + 1].strip().splitlines():
            line = line.strip()
            if not line or line.startswith("-"):
                break
            if not has_cjk(line):   # skip the Chinese translation line
                overview_lines.append(line)
        if overview_lines:
            out[name] = " ".join(overview_lines)
    return out


def load_history(digests_dir: Path, max_days: int = 28) -> dict[str, list[tuple[date, str]]]:
    """Per-category (date, overview) pairs across archived digests, oldest first."""
    dated = sorted(
        (m.group(1), p) for p in digests_dir.glob("*.md") if (m := DATE_FILE.match(p.name))
    )
    history: dict[str, list[tuple[date, str]]] = {}
    for iso, path in dated[-max_days:]:
        day = date.fromisoformat(iso)
        for name, overview in _section_overviews(path.read_text(encoding="utf-8")).items():
            history.setdefault(name, []).append((day, overview))
    return history
