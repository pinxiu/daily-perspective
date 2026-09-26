"""Write the digest as Markdown (archive), HTML (GitHub Pages) and RSS."""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from email.utils import format_datetime
from html import escape
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

ACCENTS = {
    "ai": "#2F6690",
    "tech": "#3A7D7C",
    "world": "#8C3F5D",
    "economy": "#5A7B3A",
    "perspective": "#A86B12",
}
DEFAULT_ACCENT = "#56636B"
DATE_FILE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.html$")


def _long_date(d: date) -> str:
    return f"{d:%A}, {d:%B} {d.day}, {d.year}"


# ---------- Markdown ----------

def to_markdown(day: date, reflection: str, sections: list[dict]) -> str:
    lines = [f"# {_long_date(day)}", ""]
    if reflection:
        lines += [f"> {reflection}", ""]
    for s in sections:
        if not s["stories"]:
            continue
        lines += [f"## {s['name']}", ""]
        if s["overview"]:
            lines += [s["overview"], ""]
        for st in s["stories"]:
            it = st["item"]
            lines.append(f"- **[{it.title}]({it.url})** ({it.source})")
            if st.get("why_it_matters"):
                lines.append(f"  {st['why_it_matters']}")
            if st.get("perspective"):
                lines.append(f"  *{st['perspective']}*")
        lines.append("")
    return "\n".join(lines)


# ---------- HTML ----------

CSS = """
:root{
  --paper:#F2F4F1; --ink:#1E2830; --muted:#5B6770; --rule:#D5DAD6; --link:#1E2830;
  --serif:"Literata",Georgia,"Times New Roman",serif;
  --sans:"Figtree",system-ui,-apple-system,"Segoe UI",sans-serif;
}
@media (prefers-color-scheme:dark){
  :root{--paper:#151B20;--ink:#E4E8EA;--muted:#9AA6AE;--rule:#2C353C;--link:#E4E8EA;}
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);font:1.0625rem/1.7 var(--serif)}
main{max-width:42rem;margin:0 auto;padding:3.5rem 1.25rem 4rem}
a{color:var(--link);text-decoration-thickness:1px;text-underline-offset:3px}
a:hover{text-decoration-thickness:2px}
a:focus-visible{outline:2px solid currentColor;outline-offset:3px;border-radius:2px}
.date{font:500 .95rem/1.4 var(--sans);color:var(--muted);margin:0 0 1.25rem}
.reflection{font:400 clamp(1.5rem,4.2vw,2.1rem)/1.35 var(--serif);font-style:italic;
  margin:0 0 3rem;letter-spacing:-.005em;text-wrap:balance}
.reflection.empty{font-style:normal}
section{margin:0 0 3rem;padding-left:1.1rem;border-left:3px solid var(--accent)}
h2{font:600 1.15rem/1.3 var(--sans);margin:0 0 .5rem;color:var(--accent)}
.overview{margin:0 0 1.25rem;color:var(--ink)}
ol{list-style:none;margin:0;padding:0}
li{margin:0 0 1.35rem}
.title{font:600 1.05rem/1.45 var(--sans);margin:0}
.source{font:400 .85rem/1.4 var(--sans);color:var(--muted);margin:.15rem 0 .35rem}
.why{margin:0}
.lens{margin:.35rem 0 0;color:var(--muted);font-style:italic}
footer{border-top:1px solid var(--rule);padding-top:1.5rem;font:400 .9rem/1.6 var(--sans);color:var(--muted)}
footer h2{color:var(--ink);font-size:.95rem}
.archive{display:flex;flex-wrap:wrap;gap:.25rem 1rem;padding:0;margin:0;list-style:none}
.archive li{margin:0}
.archive a{color:var(--muted)}
@media (max-width:480px){main{padding-top:2.25rem}section{padding-left:.85rem}}
"""


def _section_html(s: dict) -> str:
    if not s["stories"]:
        return ""
    accent = ACCENTS.get(s["id"], DEFAULT_ACCENT)
    parts = [f'<section style="--accent:{accent}" aria-labelledby="h-{escape(s["id"])}">',
             f'<h2 id="h-{escape(s["id"])}">{escape(s["name"])}</h2>']
    if s["overview"]:
        parts.append(f'<p class="overview">{escape(s["overview"])}</p>')
    parts.append("<ol>")
    for st in s["stories"]:
        it = st["item"]
        parts.append("<li>")
        parts.append(f'<p class="title"><a href="{escape(it.url)}">{escape(it.title)}</a></p>')
        parts.append(f'<p class="source">{escape(it.source)}</p>')
        if st.get("why_it_matters"):
            parts.append(f'<p class="why">{escape(st["why_it_matters"])}</p>')
        elif it.summary:
            parts.append(f'<p class="why">{escape(it.summary)}</p>')
        if st.get("perspective"):
            parts.append(f'<p class="lens">{escape(st["perspective"])}</p>')
        parts.append("</li>")
    parts.append("</ol></section>")
    return "\n".join(parts)


def _page(day: date, reflection: str, sections: list[dict], archive: list[str]) -> str:
    refl = (f'<p class="reflection">{escape(reflection)}</p>' if reflection
            else '<p class="reflection empty">Today\'s briefing</p>')
    arch = "".join(f'<li><a href="{d}.html">{d}</a></li>' for d in archive[:60])
    body = "\n".join(_section_html(s) for s in sections) or "<p>No stories found today. Check the Actions log for feed errors.</p>"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Daily Perspective, {day.isoformat()}</title>
<link rel="alternate" type="application/rss+xml" title="Daily Perspective" href="feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600&family=Literata:ital,opsz,wght@0,7..72,400;1,7..72,400&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<main>
<header>
<p class="date">{_long_date(day)}</p>
{refl}
</header>
{body}
<footer>
<h2>Earlier days</h2>
<ul class="archive">{arch}</ul>
<p>Subscribe in any reader with <a href="feed.xml">feed.xml</a>.</p>
</footer>
</main>
</body>
</html>
"""


# ---------- RSS ----------

def _rss(docs: Path, site_url: str) -> str:
    items = []
    for d in _archive_dates(docs)[:30]:
        md = docs.parent / "digests" / f"{d}.md"
        refl = ""
        if md.exists():
            m = re.search(r"^> (.+)$", md.read_text(encoding="utf-8"), re.MULTILINE)
            refl = m.group(1) if m else ""
        link = f"{site_url.rstrip('/')}/{d}.html" if site_url else f"{d}.html"
        pub = format_datetime(datetime.fromisoformat(d).replace(hour=12, tzinfo=timezone.utc))
        items.append(
            f"<item><title>{xml_escape(_long_date(date.fromisoformat(d)))}</title>"
            f"<link>{xml_escape(link)}</link><guid>{xml_escape(link)}</guid>"
            f"<pubDate>{pub}</pubDate><description>{xml_escape(refl)}</description></item>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>'
        f"<title>Daily Perspective</title><link>{xml_escape(site_url or '')}</link>"
        "<description>A daily digest of tech, world, economy and perspective.</description>"
        + "".join(items) + "</channel></rss>\n"
    )


def _archive_dates(docs: Path) -> list[str]:
    return sorted((m.group(1) for p in docs.glob("*.html") if (m := DATE_FILE.match(p.name))), reverse=True)


def write_all(root: Path, day: date, reflection: str, sections: list[dict], site_url: str = "") -> None:
    docs, digests = root / "docs", root / "digests"
    docs.mkdir(exist_ok=True)
    digests.mkdir(exist_ok=True)

    (digests / f"{day.isoformat()}.md").write_text(to_markdown(day, reflection, sections), encoding="utf-8")
    # write today's page first so it shows up in its own archive list
    (docs / f"{day.isoformat()}.html").write_text("", encoding="utf-8")
    archive = _archive_dates(docs)
    page = _page(day, reflection, sections, archive)
    (docs / f"{day.isoformat()}.html").write_text(page, encoding="utf-8")
    (docs / "index.html").write_text(page, encoding="utf-8")
    (docs / "feed.xml").write_text(_rss(docs, site_url), encoding="utf-8")
    (docs / ".nojekyll").touch()
