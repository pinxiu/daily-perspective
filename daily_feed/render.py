"""Write the digest as Markdown (archive), HTML (GitHub Pages) and RSS."""
from __future__ import annotations

import json
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

def to_markdown(day: date, reflection: str, reflection_zh: str, sections: list[dict]) -> str:
    lines = [f"# {_long_date(day)}", ""]
    if reflection:
        lines += [f"> {reflection}"]
        if reflection_zh:
            lines += [f"> {reflection_zh}"]
        lines.append("")
    for s in sections:
        if not s["stories"]:
            continue
        name = f"{s['name']} {s['name_zh']}" if s.get("name_zh") else s["name"]
        lines += [f"## {name}", ""]
        if s["overview"]:
            lines.append(s["overview"])
            if s.get("overview_zh"):
                lines.append(s["overview_zh"])
            lines.append("")
        for st in s["stories"]:
            it = st["item"]
            title = f"{it.title} {st['title_zh']}" if st.get("title_zh") else it.title
            lines.append(f"- **[{title}]({it.url})** ({it.source})")
            if it.audio:
                lines.append(f"  [Listen to the episode]({it.audio})")
            if st.get("why_it_matters"):
                lines.append(f"  {st['why_it_matters']}")
                if st.get("why_it_matters_zh"):
                    lines.append(f"  {st['why_it_matters_zh']}")
            if st.get("perspective"):
                lines.append(f"  *{st['perspective']}*")
                if st.get("perspective_zh"):
                    lines.append(f"  *{st['perspective_zh']}*")
        lines.append("")
    return "\n".join(lines)


# ---------- HTML ----------

CSS = """
:root{
  --paper:#F2F4F1; --ink:#1E2830; --muted:#5B6770; --rule:#D5DAD6; --link:#1E2830;
  --serif:"Literata",Georgia,"Times New Roman",serif;
  --sans:"Figtree",system-ui,-apple-system,"Segoe UI",sans-serif;
  --zh:"Noto Sans SC","PingFang SC","Microsoft YaHei",sans-serif;
}
@media (prefers-color-scheme:dark){
  :root{--paper:#151B20;--ink:#E4E8EA;--muted:#9AA6AE;--rule:#2C353C;--link:#E4E8EA;}
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);font:1.0625rem/1.7 var(--serif)}
main{max-width:48rem;margin:0 auto;padding:3.5rem 1.25rem 4rem}
a{color:var(--link);text-decoration-thickness:1px;text-underline-offset:3px}
a:hover{text-decoration-thickness:2px}
a:focus-visible{outline:2px solid currentColor;outline-offset:3px;border-radius:2px}
.date{font:500 .95rem/1.4 var(--sans);color:var(--muted);margin:0 0 1.25rem}
.bi{display:grid;grid-template-columns:1fr 1fr;gap:0 2rem;align-items:start}
.bi>*,.bi>p.overview{margin:0}
div.bi:has(>.overview){margin-bottom:1.25rem}
.zh{font-family:var(--zh)}
@media (max-width:640px){.bi{grid-template-columns:1fr;row-gap:.3rem}}
.reflection{font:400 clamp(1.35rem,3.6vw,2.1rem)/1.35 var(--serif);font-style:italic;
  margin:0;letter-spacing:-.005em;text-wrap:balance}
header{margin:0 0 3rem}
.reflection.empty{font-style:normal}
section{margin:0 0 3rem;padding-left:1.1rem;border-left:3px solid var(--accent)}
h2{font:600 1.15rem/1.3 var(--sans);margin:0 0 .5rem;color:var(--accent)}
h2 .zh-name{font-weight:400;color:var(--muted);margin-left:.5rem;font-size:.9em}
.overview{margin:0 0 1.25rem;color:var(--ink)}
ol{list-style:none;margin:0;padding:0}
li{margin:0 0 1.35rem}
.title{font:600 1.05rem/1.45 var(--sans);margin:0}
.title-zh{font:600 1.05rem/1.45 var(--zh);margin:0;color:var(--ink)}
.source{font:400 .85rem/1.4 var(--sans);color:var(--muted);margin:.15rem 0 .35rem}
.why{margin:0}
.lens{margin:.35rem 0 0;color:var(--muted);font-style:italic}
.controls{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem .75rem;margin:1.5rem 0 0;font:500 .9rem/1.4 var(--sans)}
.controls[hidden],.say[hidden]{display:none}
button,select{font:inherit;color:var(--ink);background:transparent;border:1px solid var(--rule);border-radius:999px;padding:.3rem .85rem;cursor:pointer}
button:hover,select:hover{border-color:var(--muted)}
button:focus-visible,select:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
button[aria-pressed="true"]{background:var(--ink);color:var(--paper);border-color:var(--ink)}
.say{font:500 .8rem/1.3 var(--sans);padding:.2rem .7rem;margin-top:.5rem;color:var(--accent);border-color:var(--accent)}
.say[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:var(--paper)}
audio{display:block;width:100%;max-width:26rem;height:2.25rem;margin:.5rem 0 .25rem}
#briefing{flex:1 1 100%;max-width:none;margin:0}
#briefing[hidden],#say-all[hidden]{display:none}
#briefing.docked{position:fixed;z-index:10;left:50%;transform:translateX(-50%);
  bottom:calc(.75rem + env(safe-area-inset-bottom, 0px));width:min(46rem,calc(100% - 1.5rem));
  height:3rem;border-radius:999px;background:var(--paper);box-shadow:0 4px 18px rgba(0,0,0,.18)}
body.has-dock main{padding-bottom:6rem}
footer{border-top:1px solid var(--rule);padding-top:1.5rem;font:400 .9rem/1.6 var(--sans);color:var(--muted)}
footer h2{color:var(--ink);font-size:.95rem}
.archive{display:flex;flex-wrap:wrap;gap:.25rem 1rem;padding:0;margin:0;list-style:none}
.archive li{margin:0}
.archive a{color:var(--muted)}
@media (max-width:480px){main{padding-top:2.25rem}section{padding-left:.85rem}}
"""


def _bi(cls: str, en: str, zh: str) -> str:
    """One paragraph of English, and (if present) its Chinese translation beside/below it."""
    if not en:
        return ""
    if not zh or zh.strip() == en.strip():
        return f'<p class="{cls}">{escape(en)}</p>'
    return (f'<div class="bi"><p class="{cls}">{escape(en)}</p>'
            f'<p class="{cls} zh">{escape(zh)}</p></div>')


def _section_html(s: dict, si: int = 0) -> str:
    if not s["stories"]:
        return ""
    accent = ACCENTS.get(s["id"], DEFAULT_ACCENT)
    name_zh = f' <span class="zh-name">{escape(s["name_zh"])}</span>' if s.get("name_zh") else ""
    sec_en = f'{s["name"]}. {s["overview"]}'
    sec_zh = f'{s.get("name_zh", "")}。{s.get("overview_zh", "")}' if s.get("overview_zh") else ""
    parts = [f'<section style="--accent:{accent}" aria-labelledby="h-{escape(s["id"])}" '
             f'data-id="{escape(s["id"])}" data-en="{escape(sec_en)}" data-zh="{escape(sec_zh)}">',
             f'<h2 id="h-{escape(s["id"])}">{escape(s["name"])}{name_zh}</h2>']
    parts.append(_bi("overview", s["overview"], s.get("overview_zh", "")))
    parts.append("<ol>")
    for ti, st in enumerate(s["stories"]):
        it = st["item"]
        say_en = " ".join(x for x in (it.title + ".", st.get("why_it_matters", ""), st.get("perspective", "")) if x)
        say_zh = "".join(x for x in (st.get("title_zh", "") and st["title_zh"] + "。",
                                      st.get("why_it_matters_zh", ""), st.get("perspective_zh", "")) if x)
        parts.append(f'<li data-id="s{si}-{ti}" data-en="{escape(say_en)}" data-zh="{escape(say_zh)}">')
        title_zh = st.get("title_zh", "")
        if title_zh:
            parts.append('<div class="bi">')
            parts.append(f'<p class="title"><a href="{escape(it.url)}">{escape(it.title)}</a></p>')
            parts.append(f'<p class="title-zh">{escape(title_zh)}</p>')
            parts.append("</div>")
        else:
            parts.append(f'<p class="title"><a href="{escape(it.url)}">{escape(it.title)}</a></p>')
        parts.append(f'<p class="source">{escape(it.source)}</p>')
        if it.audio:
            parts.append(f'<audio controls preload="none" src="{escape(it.audio)}" '
                         f'aria-label="Listen to the episode: {escape(it.title)}"></audio>')
        if st.get("why_it_matters"):
            parts.append(_bi("why", st["why_it_matters"], st.get("why_it_matters_zh", "")))
        elif it.summary:
            parts.append(f'<p class="why">{escape(it.summary)}</p>')
        if st.get("perspective"):
            parts.append(_bi("lens", st["perspective"], st.get("perspective_zh", "")))
        parts.append('<button class="say" type="button" aria-pressed="false" hidden>Listen</button>')
        parts.append("</li>")
    parts.append("</ol></section>")
    return "\n".join(parts)


def _page(day: date, reflection: str, reflection_zh: str, sections: list[dict], archive: list[str],
          audio: dict | None = None) -> str:
    audio = audio or {}
    player = ""
    if audio:
        srcs = " ".join(f'data-{lang}="{escape(a["file"])}"' for lang, a in audio.items())
        offsets = json.dumps({lang: a["at"] for lang, a in audio.items()}, separators=(",", ":"))
        player = (f'<audio id="briefing" controls preload="metadata" {srcs} hidden></audio>\n'
                  f'<script type="application/json" id="audio-at">{offsets}</script>')
    if reflection:
        refl = _bi("reflection", reflection, reflection_zh)
    else:
        refl = '<p class="reflection empty">Today\'s briefing</p>'
    arch = "".join(f'<li><a href="{d}.html">{d}</a></li>' for d in archive[:60])
    body = "\n".join(_section_html(s, i) for i, s in enumerate(sections)) or "<p>No stories found today. Check the Actions log for feed errors.</p>"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Daily Perspective, {day.isoformat()}</title>
<link rel="alternate" type="application/rss+xml" title="Daily Perspective" href="feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600&family=Literata:ital,opsz,wght@0,7..72,400;1,7..72,400&family=Noto+Sans+SC:wght@400;600&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<main>
<header>
<p class="date">{_long_date(day)}</p>
{refl}
<div class="controls" hidden>
{player}
<button id="say-all" type="button" aria-pressed="false">Read today's briefing aloud</button>
<select id="say-lang" aria-label="Listening language"><option value="en">English</option><option value="zh">中文</option></select>
</div>
</header>
{body}
<footer>
<h2>Earlier days</h2>
<ul class="archive">{arch}</ul>
<p>Subscribe in any reader with <a href="feed.xml">feed.xml</a>.</p>
</footer>
</main>
<script>{SPEECH_JS}</script>
</body>
</html>
"""


SPEECH_JS = r"""
(() => {
  const langSel = document.getElementById("say-lang");
  const allBtn = document.getElementById("say-all");
  const player = document.getElementById("briefing");
  const atEl = document.getElementById("audio-at");
  const at = atEl ? JSON.parse(atEl.textContent) : {};
  const synth = window.speechSynthesis;
  const canSpeak = !!(synth && window.SpeechSynthesisUtterance);
  let fileOk = !!player;   // turns false if the MP3 is missing (older days are pruned)
  if (!fileOk && !canSpeak) return;

  document.querySelector(".controls").hidden = false;
  document.querySelectorAll(".say").forEach(b => { b.hidden = false; });
  try { langSel.value = localStorage.getItem("say-lang") || "en"; } catch (e) {}

  const lang = () => langSel.value;
  const useFile = () => fileOk && !!player.dataset[lang()];
  const load = l => {
    const src = player.dataset[l];
    if (src && player.getAttribute("src") !== src) player.setAttribute("src", src);
  };
  function refresh() {
    if (player) {
      player.hidden = !useFile();
      if (useFile()) load(lang());
    }
    allBtn.hidden = useFile() || !canSpeak;
  }

  // ---- browser speech (fallback) ----
  let active = null;
  const text = el => (lang() === "zh" && el.dataset.zh) || el.dataset.en || "";
  const chunks = t => t.match(/[^.!?。！？]+[.!?。！？]*/g) || [t];
  function stopSpeech() {
    if (canSpeak) synth.cancel();
    if (active) active.setAttribute("aria-pressed", "false");
    active = null;
  }
  function speak(parts, btn) {
    stopSpeech();
    if (!canSpeak) return;
    const l = lang() === "zh" ? "zh-CN" : "en-US";
    const voice = synth.getVoices().find(v => v.lang.replace("_", "-").startsWith(l.slice(0, 2)));
    const queue = parts.flatMap(chunks).map(s => s.trim()).filter(Boolean);
    if (!queue.length) return;
    active = btn;
    btn.setAttribute("aria-pressed", "true");
    queue.forEach((s, i) => {
      const u = new SpeechSynthesisUtterance(s);
      u.lang = l;
      if (voice) u.voice = voice;
      if (i === queue.length - 1) u.onend = () => { if (active === btn) stopSpeech(); };
      synth.speak(u);
    });
  }

  // ---- recorded briefing ----
  function playFrom(id) {
    const t = (at[lang()] || {})[id];
    load(lang());
    player.hidden = false;
    // Start playback inside the tap (required on iOS), then seek once we can.
    const seek = () => { if (t != null) player.currentTime = t; };
    if (player.readyState >= 1) seek(); else player.addEventListener("loadedmetadata", seek, { once: true });
    player.play().catch(() => {});
  }

  document.querySelectorAll(".say").forEach(btn =>
    btn.addEventListener("click", () => {
      const li = btn.closest("li");
      if (useFile()) return playFrom(li.dataset.id);
      active === btn ? stopSpeech() : speak([text(li)], btn);
    }));

  allBtn.addEventListener("click", () => {
    if (active === allBtn) return stopSpeech();
    const parts = [];
    const r = document.querySelector(".reflection:not(.empty)" + (lang() === "zh" ? ".zh" : ""))
           || document.querySelector(".reflection:not(.empty)");
    if (r) parts.push(r.textContent);
    document.querySelectorAll("section[data-en]").forEach(sec => {
      parts.push(text(sec));
      sec.querySelectorAll("li[data-en]").forEach(li => parts.push(text(li)));
    });
    speak(parts, allBtn);
  });

  langSel.addEventListener("change", () => {
    try { localStorage.setItem("say-lang", lang()); } catch (e) {}
    stopSpeech();
    if (player) player.pause();
    refresh();
  });

  if (player) {
    player.addEventListener("error", () => { fileOk = false; refresh(); });
    // Once playing, keep the player on screen so it can be paused from anywhere.
    player.addEventListener("play", () => {
      stopSpeech();
      player.classList.add("docked");
      document.body.classList.add("has-dock");
    });
    player.addEventListener("ended", () => {
      player.classList.remove("docked");
      document.body.classList.remove("has-dock");
    });
    if ("mediaSession" in navigator && window.MediaMetadata) {
      navigator.mediaSession.metadata = new MediaMetadata({
        title: "Daily Perspective",
        artist: document.querySelector(".date")?.textContent || "",
      });
    }
  }
  document.querySelectorAll("audio:not(#briefing)").forEach(a => a.addEventListener("play", () => {
    stopSpeech();
    if (player) player.pause();
  }));
  window.addEventListener("pagehide", stopSpeech);
  refresh();
})();
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
            f"<pubDate>{pub}</pubDate><description>{xml_escape(refl)}</description>"
            f"{_enclosure(docs, d, site_url)}</item>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>'
        f"<title>Daily Perspective</title><link>{xml_escape(site_url or '')}</link>"
        "<description>A daily digest of tech, world, economy and perspective.</description>"
        + "".join(items) + "</channel></rss>\n"
    )


def _enclosure(docs: Path, d: str, site_url: str) -> str:
    mp3 = docs / "audio" / f"{d}-en.mp3"
    if not mp3.exists():
        return ""
    url = f"{site_url.rstrip('/')}/audio/{mp3.name}" if site_url else f"audio/{mp3.name}"
    return f'<enclosure url="{xml_escape(url)}" length="{mp3.stat().st_size}" type="audio/mpeg"/>'


def _archive_dates(docs: Path) -> list[str]:
    return sorted((m.group(1) for p in docs.glob("*.html") if (m := DATE_FILE.match(p.name))), reverse=True)


def write_all(
    root: Path, day: date, reflection: str, reflection_zh: str, sections: list[dict], site_url: str = "",
    audio: dict | None = None,
) -> None:
    docs, digests = root / "docs", root / "digests"
    docs.mkdir(exist_ok=True)
    digests.mkdir(exist_ok=True)

    (digests / f"{day.isoformat()}.md").write_text(
        to_markdown(day, reflection, reflection_zh, sections), encoding="utf-8"
    )
    # write today's page first so it shows up in its own archive list
    (docs / f"{day.isoformat()}.html").write_text("", encoding="utf-8")
    archive = _archive_dates(docs)
    page = _page(day, reflection, reflection_zh, sections, archive, audio)
    (docs / f"{day.isoformat()}.html").write_text(page, encoding="utf-8")
    (docs / "index.html").write_text(page, encoding="utf-8")
    (docs / "feed.xml").write_text(_rss(docs, site_url), encoding="utf-8")
    (docs / ".nojekyll").touch()
