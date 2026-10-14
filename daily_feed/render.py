"""Write the digest as Markdown (archive), HTML (GitHub Pages) and RSS."""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from email.utils import format_datetime
from html import escape, unescape
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
nav.days{display:flex;justify-content:space-between;gap:1rem;margin:.25rem 0 1rem;font:500 .9rem/1.4 var(--sans)}
nav.days a{color:var(--muted)}
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
        parts.append("</li>")
    parts.append("</ol></section>")
    return "\n".join(parts)


def _page(day: date, reflection: str, reflection_zh: str, sections: list[dict], archive: list[str],
          audio: dict | None = None) -> str:
    audio = audio or {}
    player = ""
    if audio:   # story timestamps; the player itself is built by SPEECH_JS from audio/index.json
        offsets = json.dumps({lang: a["at"] for lang, a in audio.items()}, separators=(",", ":"))
        player = f'<script type="application/json" id="audio-at">{offsets}</script>'
    if reflection:
        refl = _bi("reflection", reflection, reflection_zh)
    else:
        refl = '<p class="reflection empty">Daily briefing</p>'
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
{APP_HEAD}
</head>
<body>
<main data-day="{day.isoformat()}">
<header>
<p class="date">{_long_date(day)}</p>
{_day_nav(day.isoformat(), archive)}
{refl}
<div class="controls" hidden>
{player}
</div>
</header>
{body}
{_footer(day.isoformat(), archive)}
</main>
<script>{SPEECH_JS}</script>
</body>
</html>
"""


SPEECH_JS = r"""
(() => {
  const main = document.querySelector("main");
  const controls = document.querySelector(".controls");
  if (!main || !controls || !window.fetch) return;

  // ---------- settings (prepared once, remembered on this device) ----------
  const SETTINGS = "dp-settings-v1", POS = "dp-position-v1";
  const read = (k, d) => { try { return { ...d, ...JSON.parse(localStorage.getItem(k) || "{}") }; } catch (e) { return d; } };
  const write = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} };
  const SPEEDS = [1, 1.15, 1.25, 1.5];
  let cfg = read(SETTINGS, { lang: "en", speed: 1, from: "resume", day: "", skip: [] });
  try { const old = localStorage.getItem("say-lang"); if (old && !localStorage.getItem(SETTINGS)) cfg.lang = old; } catch (e) {}
  // A setup link (?lang=zh&speed=1.25&skip=economy&from=latest) configures this device.
  const startKey = c => (c.from === "day" ? "day:" + c.day : c.from);
  const startBefore = startKey(cfg);
  const q = new URLSearchParams(location.search);
  if (q.has("lang")) cfg.lang = q.get("lang") === "zh" ? "zh" : "en";
  if (q.has("speed") && SPEEDS.includes(+q.get("speed"))) cfg.speed = +q.get("speed");
  if (q.has("skip")) cfg.skip = q.get("skip").split(",").filter(Boolean);
  if (q.has("from")) {
    const f = q.get("from");
    if (/^\d{4}-\d{2}-\d{2}$/.test(f)) { cfg.from = "day"; cfg.day = f; } else if (f === "latest" || f === "resume") cfg.from = f;
  }
  write(SETTINGS, cfg);
  if (cfg.from === "day" && startKey(cfg) !== startBefore) write(POS, { d: cfg.day, t: 0, done: false });
  // One-time fix for devices that chose a start day before it reset the listening spot.
  try {
    if (!localStorage.getItem("dp-fix-start-v1")) {
      if (cfg.from === "day" && cfg.day && read(POS, { d: "" }).d > cfg.day) write(POS, { d: cfg.day, t: 0, done: false });
      localStorage.setItem("dp-fix-start-v1", "1");
    }
  } catch (e) {}

  const DAY_LINK = /(?:^|\/)(\d{4}-\d{2}-\d{2})\.html$/;
  const fromPath = location.pathname.match(DAY_LINK);
  let pageDay = main.dataset.day || (fromPath && fromPath[1]) || "";

  // ---------- markup ----------
  const I = {
    play: '<path d="M8 5.5v13a1 1 0 0 0 1.5.86l11-6.5a1 1 0 0 0 0-1.72l-11-6.5A1 1 0 0 0 8 5.5z"/>',
    pause: '<rect x="6" y="5" width="4.5" height="14" rx="1.2"/><rect x="13.5" y="5" width="4.5" height="14" rx="1.2"/>',
    back: '<path d="M12 5V2L7 6l5 4V7a6 6 0 1 1-6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><text x="12" y="16.5" font-size="7" font-weight="700" text-anchor="middle" font-family="system-ui,sans-serif">15</text>',
    next: '<path d="M5 6.2v11.6a.8.8 0 0 0 1.2.7L15 13v4.5a1 1 0 0 0 2 0v-11a1 1 0 0 0-2 0V11L6.2 5.5a.8.8 0 0 0-1.2.7z"/>',
    tune: '<path d="M4 7h10M18 7h2M4 17h4M12 17h8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><circle cx="16" cy="7" r="2.2" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="10" cy="17" r="2.2" fill="none" stroke="currentColor" stroke-width="2"/>',
  };
  const svg = (k, s = 24) => `<svg viewBox="0 0 24 24" width="${s}" height="${s}" fill="currentColor" aria-hidden="true">${I[k]}</svg>`;

  const style = document.createElement("style");
  style.textContent = `
.controls{display:block!important;margin:0!important;gap:0!important}
.controls>:not(.dp){display:none!important}
.say,#briefing,#say-all,#say-lang{display:none!important}
.dp{width:100%;max-width:100%;min-width:0;box-sizing:border-box;overflow:hidden;overflow-wrap:anywhere;--dp-bg:color-mix(in srgb,var(--ink) 6%,var(--paper));font-family:var(--sans);color:var(--ink);margin:-1.5rem 0 2rem;
  background:var(--dp-bg);border-radius:22px;padding:1.1rem 1.1rem 1rem}
.dp[hidden]{display:none}
.dp-top{display:flex;justify-content:space-between;align-items:center;gap:.5rem;min-height:2.75rem}
.dp-kicker,.dp-sub{min-width:0}
.dp-kicker{font:600 .78rem/1.3 var(--sans);letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin:0}
.dp-icon{display:grid;place-items:center;width:2.75rem;height:2.75rem;border:0;border-radius:999px;background:transparent;color:var(--muted);cursor:pointer;padding:0}
.dp-icon:hover{color:var(--ink);background:color-mix(in srgb,var(--ink) 8%,transparent)}
.dp-title{font:600 clamp(1.3rem,5.2vw,1.65rem)/1.25 var(--sans);margin:.15rem 0 .35rem;
  display:block;max-height:3.75em;overflow:hidden;overflow-wrap:anywhere}
.dp-title.zh{font-family:var(--zh)}
.dp-sub{font:400 .95rem/1.45 var(--sans);color:var(--muted);margin:0}
.dp-bar{height:4px;border-radius:2px;background:color-mix(in srgb,var(--ink) 12%,transparent);margin:1rem 0 .35rem;overflow:hidden}
.dp-bar i{display:block;height:100%;width:0;background:var(--ink);border-radius:2px;transition:width .4s linear}
.dp-times{display:flex;justify-content:space-between;font:500 .8rem/1 var(--sans);color:var(--muted);font-variant-numeric:tabular-nums}
.dp-row{display:flex;align-items:center;justify-content:center;gap:clamp(1.25rem,8vw,2.75rem);margin:.9rem 0 .2rem}
.dp-btn{display:grid;place-items:center;border:0;cursor:pointer;color:var(--ink);background:transparent;border-radius:999px;padding:0;
  width:3.75rem;height:3.75rem;-webkit-tap-highlight-color:transparent}
.dp-btn:active{transform:scale(.94)}
.dp-btn.dp-main{width:5.25rem;height:5.25rem;background:var(--ink);color:var(--paper);box-shadow:0 6px 18px color-mix(in srgb,var(--ink) 22%,transparent)}
.dp-btn:disabled{opacity:.35;cursor:default}
.dp button:focus-visible,.dp-mini button:focus-visible,.dp-sheet :focus-visible{outline:3px solid var(--ink);outline-offset:3px}
.dp-mini{position:fixed;z-index:20;left:50%;transform:translateX(-50%);bottom:calc(.75rem + env(safe-area-inset-bottom,0px));
  width:min(46rem,calc(100% - 1.5rem));display:flex;align-items:center;gap:.5rem;padding:.45rem .45rem .45rem 1.1rem;
  background:var(--ink);color:var(--paper);border-radius:999px;box-shadow:0 8px 24px rgba(0,0,0,.25);font-family:var(--sans)}
.dp-mini[hidden]{display:none}
.dp-mini p{flex:1;min-width:0;margin:0;font:600 .95rem/1.3 var(--sans);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.dp-mini .dp-btn{color:var(--paper);width:3.25rem;height:3.25rem}
body.dp-docked main{padding-bottom:7rem}
li.dp-now{position:relative}
li.dp-now::before{content:"";position:absolute;left:-1.6rem;top:.55rem;width:.5rem;height:.5rem;border-radius:50%;background:var(--accent,var(--ink))}
.dp-story{display:inline-flex;align-items:center;gap:.35rem;margin-top:.5rem;border:1px solid var(--rule);border-radius:999px;
  padding:.3rem .8rem .3rem .6rem;background:transparent;color:var(--muted);font:500 .8rem/1.2 var(--sans);cursor:pointer}
.dp-story:hover{color:var(--ink);border-color:var(--muted)}
nav.days{display:flex;justify-content:space-between;gap:1rem;margin:.25rem 0 1rem;font:500 .9rem/1.4 var(--sans)}
nav.days a{color:var(--muted)}
main.swapping{opacity:.5;transition:opacity .15s}
.dp-sheet{border:0;padding:0;width:min(30rem,100%);max-height:92vh;margin:auto auto 0;border-radius:22px 22px 0 0;
  background:var(--paper);color:var(--ink);font-family:var(--sans)}
@media (min-width:700px){.dp-sheet{margin:auto;border-radius:22px}}
.dp-sheet::backdrop{background:rgba(0,0,0,.45)}
.dp-sheet form{padding:1.25rem 1.25rem calc(1.25rem + env(safe-area-inset-bottom,0px))}
.dp-sheet h3{font:600 1.2rem/1.3 var(--sans);margin:0 0 1rem}
.dp-sheet fieldset{border:0;margin:0 0 1.25rem;padding:0}
.dp-sheet legend{font:600 .78rem/1.3 var(--sans);letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-bottom:.5rem;padding:0}
.dp-seg{display:flex;gap:.4rem;flex-wrap:wrap}
.dp-seg label,.dp-opt{position:relative;cursor:pointer}
.dp-seg input,.dp-opt input{position:absolute;opacity:0;pointer-events:none}
.dp-seg span{display:block;min-width:3.25rem;text-align:center;padding:.6rem .9rem;border-radius:999px;border:1px solid var(--rule);font:500 .95rem/1.2 var(--sans)}
.dp-seg input:checked+span{background:var(--ink);color:var(--paper);border-color:var(--ink)}
.dp-seg input:focus-visible+span,.dp-opt input:focus-visible+span{outline:3px solid var(--ink);outline-offset:2px}
.dp-opt{display:block;margin:0 0 .4rem}
.dp-opt span{display:block;padding:.7rem .9rem;border-radius:14px;border:1px solid var(--rule);font:500 .95rem/1.3 var(--sans)}
.dp-opt small{display:block;font-weight:400;color:var(--muted);font-size:.82rem;margin-top:.1rem}
.dp-opt input:checked+span{border-color:var(--ink);box-shadow:inset 0 0 0 1px var(--ink)}
.dp-sheet select{font:inherit;color:var(--ink);background:var(--paper);border:1px solid var(--rule);border-radius:10px;padding:.5rem .6rem;margin:.4rem 0 0 .2rem}
.dp-skip span{text-decoration:none}
.dp-skip input:not(:checked)+span{color:var(--muted);text-decoration:line-through}
.dp-link{display:flex;gap:.5rem;align-items:center}
.dp-link button,.dp-done{font:600 .95rem/1 var(--sans);border-radius:999px;padding:.75rem 1.1rem;cursor:pointer;border:1px solid var(--rule);background:transparent;color:var(--ink)}
.dp-done{display:block;width:100%;margin-top:.5rem;background:var(--ink);color:var(--paper);border-color:var(--ink)}
.dp-note{font-size:.82rem;color:var(--muted);margin:.4rem 0 0}`;
  document.head.append(style);

  const card = document.createElement("div");
  card.className = "dp";
  card.hidden = true;
  card.innerHTML = `
<div class="dp-top"><p class="dp-kicker"></p>
<button class="dp-icon dp-open" type="button" aria-label="Listening settings">${svg("tune")}</button></div>
<p class="dp-title"></p>
<p class="dp-sub"></p>
<div class="dp-bar" aria-hidden="true"><i></i></div>
<div class="dp-times"><span class="dp-at"></span><span class="dp-left"></span></div>
<div class="dp-row">
<button class="dp-btn dp-back" type="button" aria-label="Back 15 seconds">${svg("back", 30)}</button>
<button class="dp-btn dp-main dp-toggle" type="button" aria-label="Play">${svg("play", 38)}</button>
<button class="dp-btn dp-next" type="button" aria-label="Next story">${svg("next", 30)}</button>
</div>`;
  controls.replaceChildren(card);
  controls.hidden = false;
  const headerEl = main.querySelector("header");
  if (headerEl) headerEl.prepend(controls);   // Play is the first thing on every page

  const mini = document.createElement("div");
  mini.className = "dp-mini";
  mini.hidden = true;
  mini.innerHTML = `<p></p>
<button class="dp-btn dp-toggle" type="button" aria-label="Play">${svg("play", 28)}</button>
<button class="dp-btn dp-next" type="button" aria-label="Next story">${svg("next", 26)}</button>`;
  document.body.append(mini);

  const $ = s => card.querySelector(s);
  const audio = new Audio();
  audio.preload = "none";

  // ---------- data ----------
  let days = [];           // manifest, oldest first
  let qi = -1;             // index of the day loaded in `audio`
  let segs = [];           // [{t, id, sec}] for the loaded track, in order
  let curSeg = null;
  let caughtUp = false;
  let pendingSeek = null;
  const fmtDay = d => new Date(d + "T12:00:00").toLocaleDateString(cfg.lang === "zh" ? "zh-CN" : undefined, { weekday: "short", month: "short", day: "numeric" });
  const mmss = s => { s = Math.max(0, Math.round(s || 0)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };
  const lang = () => cfg.lang;
  const trackLang = day => (day[lang()] ? lang() : "en");
  const position = () => read(POS, { d: "", t: 0, done: false });

  function segsOf(day) {
    const L = trackLang(day), at = (day.at || {})[L] || {};
    const secs = (day.s || []).map(x => x[0]);
    return Object.entries(at).map(([id, t]) => {
      const m = id.match(/^s(\d+)-\d+$/);
      return { t, id, sec: id === "top" ? null : m ? secs[+m[1]] : id };
    }).sort((a, b) => a.t - b.t);
  }
  const included = s => !s || s.sec == null || !cfg.skip.includes(s.sec);
  const segAt = t => { let c = segs[0] || null; for (const s of segs) { if (s.t <= t + 0.05) c = s; else break; } return c; };
  function label(day, seg) {
    if (!day) return "";
    if (!seg || seg.id === "top") return lang() === "zh" ? "今日反思" : "Today's reflection";
    const t = (day.t || {})[seg.id];
    if (t) return (lang() === "zh" && t[1]) || t[0];
    const s = (day.s || []).find(x => x[0] === seg.id);
    return s ? ((lang() === "zh" && s[2]) || s[1]) : "";
  }
  const sectionName = (day, seg) => {
    const s = seg && (day.s || []).find(x => x[0] === seg.sec);
    return s ? ((lang() === "zh" && s[2]) || s[1]) : "";
  };

  // Where one tap of Play should start.
  function plan() {
    if (!days.length) return null;
    const last = days.length - 1;
    const floor = cfg.from === "latest" ? last
      : cfg.from === "day" ? Math.max(0, days.findIndex(x => x.d >= cfg.day) < 0 ? last : days.findIndex(x => x.d >= cfg.day))
      : 0;
    const p = position();
    const pi = days.findIndex(x => x.d === p.d);
    if (pi >= floor && pi >= 0) {
      if (!p.done) return { i: pi, t: p.t };
      if (pi < last) return { i: pi + 1, t: 0 };
      return { i: last, t: 0, caughtUp: true };
    }
    if (cfg.from === "resume" && pi < 0) return { i: last, t: 0 };
    return { i: floor, t: 0 };
  }
  function minutesFrom(i, t) {
    let s = 0;
    for (let k = i; k < days.length; k++) s += ((days[k].dur || {})[trackLang(days[k])] || 0) - (k === i ? t : 0);
    return Math.max(1, Math.round(s / 60));
  }

  // ---------- rendering ----------
  const playing = () => !audio.paused && !audio.ended;
  function paint() {
    const p = qi >= 0 ? { i: qi, t: audio.currentTime } : plan();
    if (!p) { card.hidden = true; return; }
    card.hidden = false;
    const day = days[p.i];
    const active = qi >= 0;
    const title = $(".dp-title");
    title.classList.toggle("zh", lang() === "zh");
    const left = days.length - 1 - p.i;
    const more = left ? (lang() === "zh" ? `之后还有 ${left} 天` : `then ${left} more day${left > 1 ? "s" : ""}`) : "";
    if (active && curSeg) {
      $(".dp-kicker").textContent = [fmtDay(day.d), sectionName(day, curSeg)].filter(Boolean).join(" · ");
      title.textContent = label(day, curSeg);
      $(".dp-sub").textContent = more ? (lang() === "zh" ? `${more}，直到最新` : `${more[0].toUpperCase() + more.slice(1)} to the latest`) : (lang() === "zh" ? "最新一期" : "Latest briefing");
    } else {
      caughtUp = !!(p && p.caughtUp);
      const n = days.length - p.i;
      $(".dp-kicker").textContent = caughtUp ? (lang() === "zh" ? "已全部收听" : "All caught up")
        : p.t > 5 ? (lang() === "zh" ? "继续收听" : "Pick up where you left off") : (lang() === "zh" ? "接下来" : "Up next");
      title.textContent = caughtUp ? (lang() === "zh" ? "再听一遍最新简报" : "Replay the latest briefing")
        : n > 1 ? (lang() === "zh" ? `${n} 期简报待听` : `${n} briefings to catch up on`) : fmtDay(day.d);
      const range = n > 1 ? `${fmtDay(day.d)} → ${fmtDay(days[days.length - 1].d)}` : (lang() === "zh" ? "最新一期" : "Latest briefing");
      const bits = [range, `${lang() === "zh" ? "约" : "about"} ${minutesFrom(p.i, p.t)} min`,
                    lang() === "zh" ? "中文" : "English", `${cfg.speed}×`];
      if (cfg.skip.length) bits.push(lang() === "zh" ? `跳过 ${cfg.skip.length} 个栏目` : `skipping ${cfg.skip.length} section${cfg.skip.length > 1 ? "s" : ""}`);
      $(".dp-sub").textContent = bits.join(" · ");
    }
    const dur = audio.duration || (day.dur || {})[trackLang(day)] || 0;
    const t = active ? audio.currentTime : p.t;
    $(".dp-bar i").style.width = dur ? `${Math.min(100, 100 * t / dur)}%` : "0";
    $(".dp-at").textContent = active || t ? mmss(t) : "";
    $(".dp-left").textContent = dur && (active || t) ? `-${mmss(dur - t)}` : "";
    const isPlaying = playing();
    document.querySelectorAll(".dp-toggle").forEach(b => {
      b.innerHTML = svg(isPlaying ? "pause" : "play", b.classList.contains("dp-main") ? 38 : 28);
      b.setAttribute("aria-label", isPlaying ? "Pause" : "Play");
    });
    document.querySelectorAll(".dp-next").forEach(b => { b.disabled = !active; });
    $(".dp-back").disabled = !active;
    mini.querySelector("p").textContent = active && curSeg ? label(day, curSeg) : "";
    highlight();
  }
  function highlight() {
    document.querySelectorAll("li.dp-now").forEach(li => li.classList.remove("dp-now"));
    if (qi >= 0 && curSeg && days[qi].d === pageDay) {
      const li = document.querySelector(`li[data-id="${curSeg.id}"]`);
      if (li) li.classList.add("dp-now");
    }
  }
  // Mini player whenever the big card is scrolled away during playback.
  let cardVisible = true;
  if ("IntersectionObserver" in window) {
    new IntersectionObserver(es => { cardVisible = es[0].isIntersecting; dock(); }).observe(card);
  }
  function dock() {
    const show = qi >= 0 && !cardVisible && !audio.ended;
    mini.hidden = !show;
    document.body.classList.toggle("dp-docked", show);
  }

  // ---------- playback ----------
  function load(i, t, autoplay) {
    const day = days[i], src = day[trackLang(day)];
    const followPage = qi < 0 || days[qi].d === pageDay;   // the page shows the day being played
    qi = i;
    segs = segsOf(day);
    pendingSeek = t;
    if (audio.getAttribute("src") !== src) { audio.src = src; audio.load(); }
    else if (audio.readyState >= 1) applySeek();
    audio.playbackRate = audio.defaultPlaybackRate = cfg.speed;
    curSeg = segAt(t || 0);
    if (autoplay) audio.play().catch(() => {});
    meta();
    if (followPage && day.d !== pageDay) go(day.d, true);
    paint();
  }
  function applySeek() {
    if (pendingSeek == null) return;
    let t = pendingSeek;
    pendingSeek = null;
    const s = segAt(t);
    if (!included(s)) { const n = segs.find(x => x.t > t && included(x)); if (n) t = n.t; }
    try { audio.currentTime = t; } catch (e) {}
  }
  audio.addEventListener("loadedmetadata", () => { audio.playbackRate = cfg.speed; applySeek(); paint(); });

  function start() {
    const p = plan();
    if (!p) return;
    if (p.caughtUp) write(POS, { d: days[p.i].d, t: 0, done: false });
    load(p.i, p.t, true);
  }
  function toggle() {
    if (qi < 0) return start();
    if (audio.paused) audio.play().catch(() => {}); else audio.pause();
  }
  function endDay() {
    write(POS, { d: days[qi].d, t: 0, done: true });
    if (qi + 1 < days.length) return load(qi + 1, 0, true);
    audio.pause();
    qi = -1; curSeg = null;
    paint(); dock();
  }
  function nextStory() {
    if (qi < 0) return;
    const now = audio.currentTime;
    const n = segs.find(s => s.t > now + 0.5 && included(s));
    if (n) audio.currentTime = n.t; else endDay();
  }
  function prevStory() {
    if (qi < 0) return;
    const now = audio.currentTime, cur = segAt(now);
    if (cur && now - cur.t > 3) { audio.currentTime = cur.t; return; }
    const before = segs.filter(s => cur && s.t < cur.t && included(s));
    if (before.length) audio.currentTime = before[before.length - 1].t;
    else if (qi > 0) { const prev = segsOf(days[qi - 1]).filter(included); load(qi - 1, prev.length ? prev[prev.length - 1].t : 0, true); }
    else audio.currentTime = 0;
  }
  const seekBy = d => { if (qi >= 0) audio.currentTime = Math.max(0, Math.min((audio.duration || 1e9) - 0.5, audio.currentTime + d)); };

  let lastSave = 0;
  audio.addEventListener("timeupdate", () => {
    if (qi < 0) return;
    const s = segAt(audio.currentTime);
    if (!included(s)) {   // skipped section: jump past it
      const n = segs.find(x => x.t > s.t && included(x));
      if (n) audio.currentTime = n.t; else endDay();
      return;
    }
    if (s !== curSeg) { curSeg = s; meta(); }
    if (Math.abs(audio.currentTime - lastSave) > 4) {
      lastSave = audio.currentTime;
      write(POS, { d: days[qi].d, t: Math.max(0, audio.currentTime - 2), done: false });
    }
    paint();
  });
  audio.addEventListener("ended", endDay);
  audio.addEventListener("play", () => { paint(); dock(); });
  audio.addEventListener("pause", () => {
    if (qi >= 0) write(POS, { d: days[qi].d, t: Math.max(0, audio.currentTime - 2), done: false });
    paint();
  });
  audio.addEventListener("error", () => {
    if (qi < 0 || !audio.getAttribute("src")) return;
    days.splice(qi, 1);              // that day's file is gone: drop it and move on
    const i = qi; qi = -1;
    if (i < days.length) load(i, 0, true); else { paint(); dock(); }
  });

  function meta() {
    if (!("mediaSession" in navigator) || !window.MediaMetadata || qi < 0) return;
    const day = days[qi];
    navigator.mediaSession.metadata = new MediaMetadata({
      title: label(day, curSeg) || "Daily Perspective",
      artist: "Daily Perspective · " + fmtDay(day.d),
      album: sectionName(day, curSeg) || "Daily Perspective",
    });
  }
  if ("mediaSession" in navigator) {
    const on = (a, f) => { try { navigator.mediaSession.setActionHandler(a, f); } catch (e) {} };
    on("play", () => (qi < 0 ? start() : audio.play()));
    on("pause", () => audio.pause());
    on("nexttrack", nextStory);        // steering-wheel / lock-screen ⏭ = next story
    on("previoustrack", prevStory);
    on("seekbackward", () => seekBy(-15));
    on("seekforward", () => seekBy(30));
  }

  // ---------- buttons ----------
  document.addEventListener("click", e => {
    const b = e.target.closest("button");
    if (b && b.classList.contains("dp-toggle")) return toggle();
    if (b && b.classList.contains("dp-next")) return nextStory();
    if (b && b.classList.contains("dp-back")) return seekBy(-15);
    if (b && b.classList.contains("dp-open")) return openSheet();
    if (b && b.classList.contains("dp-story")) {
      const i = days.findIndex(x => x.d === pageDay);
      const seg = i >= 0 && segsOf(days[i]).find(s => s.id === b.dataset.id);
      if (seg) load(i, seg.t, true);
      return;
    }
    const link = e.target.closest("nav.days a, footer a");
    if (link && !e.metaKey && !e.ctrlKey && !e.shiftKey && !e.altKey) {
      const m = (link.getAttribute("href") || "").match(DAY_LINK);
      if (m) { e.preventDefault(); go(m[1], true); }
    }
  });
  function storyButtons() {
    const i = days.findIndex(x => x.d === pageDay);
    const ids = i >= 0 ? new Set(segsOf(days[i]).map(s => s.id)) : new Set();
    document.querySelectorAll("li[data-id]").forEach(li => {
      if (li.querySelector(".dp-story") || !ids.has(li.dataset.id)) return;
      const b = document.createElement("button");
      b.type = "button";
      b.className = "dp-story";
      b.dataset.id = li.dataset.id;
      b.innerHTML = svg("play", 14) + (lang() === "zh" ? "从这里开始播放" : "Play from here");
      li.append(b);
    });
  }

  // ---------- settings sheet ----------
  const sheet = document.createElement("dialog");
  sheet.className = "dp-sheet";
  document.body.append(sheet);
  function openSheet() {
    const sections = new Map();
    days.forEach(d => (d.s || []).forEach(s => sections.set(s[0], s)));
    const opt = (v, t, small) => `<label class="dp-opt"><input type="radio" name="from" value="${v}"${cfg.from === v ? " checked" : ""}><span>${t}${small ? `<small>${small}</small>` : ""}</span></label>`;
    const dayOptions = days.map(d => `<option value="${d.d}"${d.d === cfg.day ? " selected" : ""}>${fmtDay(d.d)}</option>`).join("");
    sheet.innerHTML = `<form method="dialog">
<h3>Listening setup</h3>
<fieldset><legend>When I press play</legend>
${opt("resume", "Continue where I left off", "Then every newer day, until I'm caught up")}
${opt("latest", "Latest briefing only", "Skip anything older")}
${opt("day", "Start from a day", `<select name="day" aria-label="Start day">${dayOptions}</select>`)}
</fieldset>
<fieldset><legend>Language</legend><div class="dp-seg">
<label><input type="radio" name="lang" value="en"${lang() === "en" ? " checked" : ""}><span>English</span></label>
<label><input type="radio" name="lang" value="zh"${lang() === "zh" ? " checked" : ""}><span>中文</span></label></div></fieldset>
<fieldset><legend>Speed</legend><div class="dp-seg">
${SPEEDS.map(s => `<label><input type="radio" name="speed" value="${s}"${cfg.speed === s ? " checked" : ""}><span>${s}×</span></label>`).join("")}</div></fieldset>
<fieldset><legend>Sections</legend><div class="dp-seg dp-skip">
${[...sections.values()].map(s => `<label><input type="checkbox" name="sec" value="${s[0]}"${cfg.skip.includes(s[0]) ? "" : " checked"}><span>${s[1]}</span></label>`).join("")}</div>
<p class="dp-note">Unchecked sections are skipped automatically.</p></fieldset>
<fieldset><legend>Use this setup on another device</legend>
<div class="dp-link"><button type="button" class="dp-copy">Copy setup link</button></div>
<p class="dp-note">Open it on your phone, then Share → Add to Home Screen. After that it's one tap to open and one tap to play.</p></fieldset>
<button class="dp-done" value="done">Done</button></form>`;
    const f = sheet.querySelector("form");
    // Picking a date means "start from that day", even if that option wasn't selected yet.
    f.day.addEventListener("change", () => { f.from.value = "day"; });
    f.addEventListener("change", () => {
      const was = { lang: cfg.lang, start: startKey(cfg) };
      cfg = {
        lang: f.lang.value, speed: +f.speed.value, from: f.from.value, day: f.day.value,
        skip: [...f.querySelectorAll('input[name="sec"]')].filter(x => !x.checked).map(x => x.value),
      };
      write(SETTINGS, cfg);
      audio.playbackRate = audio.defaultPlaybackRate = cfg.speed;
      if (startKey(cfg) !== was.start && cfg.from === "day") {
        // A chosen start day means "start there": move the listening spot to it.
        const i = days.findIndex(x => x.d >= cfg.day);
        write(POS, { d: i >= 0 ? days[i].d : cfg.day, t: 0, done: false });
        if (qi >= 0) { const wasPlaying = playing(); qi = -1; const p = plan(); load(p.i, p.t, wasPlaying); }
      } else if (qi >= 0 && was.lang !== cfg.lang) {     // same story, other language
        const id = curSeg && curSeg.id, wasPlaying = playing();
        const seg = segsOf(days[qi]).find(s => s.id === id);
        load(qi, seg ? seg.t : 0, wasPlaying);
      }
      paint();
    });
    sheet.querySelector(".dp-copy").addEventListener("click", e => {
      const u = new URL(location.href.split("?")[0].replace(/\d{4}-\d{2}-\d{2}\.html$/, ""));
      u.search = new URLSearchParams({ lang: cfg.lang, speed: cfg.speed,
        from: cfg.from === "day" ? cfg.day : cfg.from, ...(cfg.skip.length ? { skip: cfg.skip.join(",") } : {}) });
      const done = () => { e.target.textContent = "Copied"; setTimeout(() => { e.target.textContent = "Copy setup link"; }, 1800); };
      (navigator.clipboard ? navigator.clipboard.writeText(u.href).then(done) : Promise.reject())
        .catch(() => prompt("Copy this link:", u.href));
    });
    if (sheet.showModal) sheet.showModal(); else sheet.setAttribute("open", "");
  }
  sheet.addEventListener("click", e => { if (e.target === sheet) sheet.close(); });   // tap outside closes

  // ---------- switching days without reloading (audio keeps playing) ----------
  async function go(day, push) {
    if (!day || day === pageDay) return;
    main.classList.add("swapping");
    try {
      const r = await fetch(`${day}.html`, { cache: "no-cache" });
      if (!r.ok) throw new Error(r.status);
      const doc = new DOMParser().parseFromString(await r.text(), "text/html");
      const newMain = doc.querySelector("main"), newHeader = newMain && newMain.querySelector("header");
      const header = main.querySelector("header");
      if (!newHeader || !header) throw new Error("unexpected page");
      [...header.children].forEach(el => { if (el !== controls) el.remove(); });
      [...newHeader.children].forEach(el => {
        if (!el.classList.contains("controls")) header.append(document.importNode(el, true));
      });
      [...main.children].forEach(el => { if (el !== header) el.remove(); });
      [...newMain.children].forEach(el => { if (el.tagName !== "HEADER") main.append(document.importNode(el, true)); });
      pageDay = day;
      main.dataset.day = day;
      document.title = doc.title;
      if (push) history.pushState({ day }, "", `${day}.html${location.search}`);
      storyButtons();
      paint();
      window.scrollTo(0, 0);
    } catch (e) {
      location.href = `${day}.html`;
    } finally {
      main.classList.remove("swapping");
    }
  }
  history.replaceState({ day: pageDay }, "");
  window.addEventListener("popstate", e => { if (e.state && e.state.day) go(e.state.day, false); });

  // ---------- go ----------
  fetch("audio/index.json", { cache: "no-cache" })
    .then(r => (r.ok ? r.json() : null))
    .then(m => {
      if (!m || !Array.isArray(m.days) || !m.days.length) return;
      days = m.days;
      storyButtons();
      paint();
    })
    .catch(() => {});
  document.addEventListener("keydown", e => {
    if (e.code === "Space" && !/INPUT|SELECT|TEXTAREA|BUTTON/.test(document.activeElement.tagName)) { e.preventDefault(); toggle(); }
  });
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


BITRATE_KBPS = 32   # matches audio.BITRATE; used to estimate durations from file size


def _short(d: str) -> str:
    return date.fromisoformat(d).strftime("%a, %b %-d")


def _day_nav(day: str, all_days: list[str]) -> str:
    """Previous / next day links; all_days in any order."""
    ordered = sorted(set(all_days) | {day})
    i = ordered.index(day)
    prev = f'<a href="{ordered[i - 1]}.html" rel="prev">&larr; {_short(ordered[i - 1])}</a>' if i else "<span></span>"
    nxt = (f'<a href="{ordered[i + 1]}.html" rel="next">{_short(ordered[i + 1])} &rarr;</a>'
           if i + 1 < len(ordered) else "<span></span>")
    return f'<nav class="days" aria-label="Other days">{prev}{nxt}</nav>'


def _footer(day: str, all_days: list[str]) -> str:
    others = sorted((d for d in set(all_days) if d != day), reverse=True)[:60]
    items = "".join(f'<li><a href="{d}.html">{_short(d)}</a></li>' for d in others)
    return (f'<footer>\n<h2>Other days</h2>\n<ul class="archive">{items}</ul>\n'
            f'<p>Subscribe in any reader with <a href="feed.xml">feed.xml</a>.</p>\n</footer>')


APP_HEAD = """<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" sizes="180x180" href="apple-touch-icon.png">
<link rel="icon" type="image/png" sizes="32x32" href="favicon-32.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Perspective">
<meta name="theme-color" content="#F2F4F1" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#151B20" media="(prefers-color-scheme: dark)">"""

# No start_url on purpose: the Home Screen app then opens the exact link it was
# added from, so a setup link (?lang=zh&speed=1.25...) keeps its settings.
WEB_MANIFEST = {
    "name": "Daily Perspective", "short_name": "Perspective", "display": "standalone",
    "background_color": "#151B20", "theme_color": "#151B20",
    "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
              {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}],
}


def _write_app_files(docs: Path) -> None:
    (docs / "manifest.webmanifest").write_text(json.dumps(WEB_MANIFEST, indent=1), encoding="utf-8")
    names = ("icon-512.png", "icon-192.png", "apple-touch-icon.png", "favicon-32.png")
    if not all((docs / n).exists() for n in names):
        try:
            from .icon import make_icons
        except ImportError:   # Pillow not installed: keep whatever icons exist
            return
        make_icons(docs)


_LI = re.compile(r'<li data-id="(s\d+-\d+)"[^>]*>(.*?)</li>', re.S)
_SEC = re.compile(r'<section [^>]*data-id="([^"]+)"[^>]*>\s*<h2[^>]*>(.*?)</h2>', re.S)
_AT = re.compile(r'<script type="application/json" id="audio-at">(.*?)</script>', re.S)


def _text(fragment: str) -> str:
    return " ".join(unescape(re.sub(r"<[^>]+>", "", fragment)).split())


def _day_index(html: str) -> dict:
    """Story titles, section names and timestamps, so the player can label and skip."""
    out: dict = {}
    m = _AT.search(html)
    if m:
        try:
            out["at"] = json.loads(m.group(1))
        except ValueError:
            pass
    secs = []
    for sid, h2 in _SEC.findall(html):
        zh = re.search(r'<span class="zh-name">(.*?)</span>', h2, re.S)
        secs.append([sid, _text(re.sub(r'<span class="zh-name">.*?</span>', "", h2, flags=re.S)),
                     _text(zh.group(1)) if zh else ""])
    out["s"] = secs
    titles = {}
    for sid, body in _LI.findall(html):
        en = re.search(r'<p class="title"><a [^>]*>(.*?)</a>', body, re.S)
        zh = re.search(r'<p class="title-zh">(.*?)</p>', body, re.S)
        if en:
            titles[sid] = [_text(en.group(1)), _text(zh.group(1)) if zh else ""]
    out["t"] = titles
    return out


_APP_HEAD_OLD = re.compile(r'<link rel="manifest".*?media="\(prefers-color-scheme: dark\)">\n?', re.S)
_FOOTER = re.compile(r"<footer>.*?</footer>", re.S)
_NAV = re.compile(r'<nav class="days".*?</nav>\n?', re.S)
_DATE_P = re.compile(r'(<p class="date">[^<]*</p>\n?)')
_SCRIPT = re.compile(r"<script>(?:(?!</script>).)*</script>(\s*</body>)", re.S)
_DAY_PAGE = re.compile(r"\d{4}-\d{2}-\d{2}\.html$")


def refresh_archive(docs: Path) -> None:
    """Write audio/index.json and give every page the current player script.

    Pages are static, so without this older days would keep the player code
    they were built with and couldn't replay forward to today.
    """
    audio_dir = docs / "audio"
    days: dict[str, dict] = {}
    for f in sorted(audio_dir.glob("*.mp3")) if audio_dir.exists() else []:
        m = re.match(r"(\d{4}-\d{2}-\d{2})-(en|zh)\.mp3$", f.name)
        if m:
            day = days.setdefault(m.group(1), {"d": m.group(1), "dur": {}})
            day[m.group(2)] = f"audio/{f.name}"
            day["dur"][m.group(2)] = round(f.stat().st_size * 8 / (BITRATE_KBPS * 1000))
    for d, day in days.items():
        page = docs / f"{d}.html"
        if page.exists():
            day.update(_day_index(page.read_text(encoding="utf-8")))
    if audio_dir.exists():
        manifest = {"days": [days[d] for d in sorted(days) if days[d].get("at")]}
        (audio_dir / "index.json").write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")),
                                              encoding="utf-8")
    _write_app_files(docs)

    script = f"<script>{SPEECH_JS}</script>"
    pages = sorted(f for f in docs.glob("*.html") if _DAY_PAGE.search(f.name))
    all_days = [f.stem for f in pages]
    for f in pages:
        html = f.read_text(encoding="utf-8")
        new = _FOOTER.sub(lambda m: _footer(f.stem, all_days), html, count=1)
        new = _NAV.sub("", new, count=1)
        new = _DATE_P.sub(lambda m: m.group(1).rstrip("\n") + "\n" + _day_nav(f.stem, all_days) + "\n", new, count=1)
        new = new.replace("Read today's briefing aloud", "Read this briefing aloud")
        new = new.replace('<p class="reflection empty">Today\'s briefing</p>', '<p class="reflection empty">Daily briefing</p>')
        if 'class="controls"' in new:       # pages built before listening existed have no player
            new = _SCRIPT.sub(lambda m: script + m.group(1), new, count=1)
        new = _APP_HEAD_OLD.sub("", new, count=1)
        new = new.replace("</head>", APP_HEAD + "\n</head>", 1)
        new = new.replace("<main>\n<header>", f'<main data-day="{f.stem}">\n<header>', 1)
        if new != html:
            f.write_text(new, encoding="utf-8")
    if pages:   # index.html is a copy of the newest day
        (docs / "index.html").write_text(pages[-1].read_text(encoding="utf-8"), encoding="utf-8")


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
    refresh_archive(docs)
    (docs / "feed.xml").write_text(_rss(docs, site_url), encoding="utf-8")
    (docs / ".nojekyll").touch()
