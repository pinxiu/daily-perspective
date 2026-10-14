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
</head>
<body>
<main data-day="{day.isoformat()}">
<header>
<p class="date">{_long_date(day)}</p>
{_day_nav(day.isoformat(), archive)}
{refl}
<div class="controls" hidden>
{player}
<button id="say-all" type="button" aria-pressed="false">Read this briefing aloud</button>
<select id="say-lang" aria-label="Listening language"><option value="en">English</option><option value="zh">中文</option></select>
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
  const langSel = document.getElementById("say-lang");
  const allBtn = document.getElementById("say-all");
  const controls = document.querySelector(".controls");
  const main = document.querySelector("main");
  if (!langSel || !allBtn || !controls || !main) return;
  const synth = window.speechSynthesis;
  const canSpeak = !!(synth && window.SpeechSynthesisUtterance);
  const DAY_LINK = /(?:^|\/)(\d{4}-\d{2}-\d{2})\.html$/;

  const readAt = root => {
    const el = root.querySelector("#audio-at");
    try { return el ? JSON.parse(el.textContent) : {}; } catch (e) { return {}; }
  };
  const fromPath = location.pathname.match(DAY_LINK);
  let pageDay = main.dataset.day || (fromPath && fromPath[1]) || "";
  let at = readAt(document);

  let player = document.getElementById("briefing");
  if (!player) {   // pages from before narration existed
    player = document.createElement("audio");
    player.id = "briefing";
    player.controls = true;
    player.preload = "none";
    player.hidden = true;
    controls.prepend(player);
  }

  const style = document.createElement("style");
  style.textContent = `
.replay{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem .75rem;flex:1 1 100%}
.replay[hidden],.replay-now:empty{display:none}
.replay-now{flex:1 1 100%;font-size:.85rem;color:var(--muted);margin:0}
nav.days{display:flex;justify-content:space-between;gap:1rem;margin:.25rem 0 1rem;font:500 .9rem/1.4 var(--sans)}
nav.days a{color:var(--muted)}
main.swapping{opacity:.5;transition:opacity .15s}`;
  document.head.append(style);
  const bar = document.createElement("div");
  bar.className = "replay";
  bar.hidden = true;
  bar.innerHTML = '<select id="replay-from" aria-label="Start replay from"></select>' +
    '<button id="replay-go" type="button">Play from this day to today</button>' +
    '<p class="replay-now" aria-live="polite"></p>';
  controls.append(bar);
  const fromSel = bar.querySelector("#replay-from");
  const goBtn = bar.querySelector("#replay-go");
  const nowEl = bar.querySelector(".replay-now");

  controls.hidden = false;
  const showSay = () => document.querySelectorAll(".say").forEach(b => { b.hidden = false; });
  showSay();
  try { langSel.value = localStorage.getItem("say-lang") || "en"; } catch (e) {}
  const lang = () => langSel.value;

  // ---- playlist: every day that has audio, oldest first ----
  let days = (player.dataset.en || player.dataset.zh)
    ? [{ d: pageDay, en: player.dataset.en, zh: player.dataset.zh }] : [];
  let cur = -1;          // index in `days` of the loaded track
  let chain = false;     // keep going into newer days when one ends
  let ownOk = true;      // false once this page's own MP3 turns out to be missing
  const ownIdx = () => days.findIndex(x => x.d === pageDay);
  const trackLang = i => (days[i][lang()] ? lang() : "en");   // fall back to English
  const fmt = d => new Date(d + "T12:00:00").toLocaleDateString(undefined,
    { weekday: "short", month: "short", day: "numeric" });

  function load(i) {
    const src = days[i][trackLang(i)];
    if (player.getAttribute("src") !== src) player.setAttribute("src", src);
    cur = i;
    status();
    if ("mediaSession" in navigator && window.MediaMetadata) {
      navigator.mediaSession.metadata = new MediaMetadata(
        { title: "Daily Perspective, " + fmt(days[i].d), artist: "Daily Perspective" });
    }
  }
  function status() {
    if (!chain || cur < 0) { nowEl.textContent = ""; return; }
    const left = days.length - 1 - cur;
    const fallback = trackLang(cur) !== lang() ? " (English only this day)" : "";
    nowEl.textContent = `Now playing ${fmt(days[cur].d)}${fallback}` +
      (left ? `, then ${left} more day${left > 1 ? "s" : ""} to the latest` : ", the latest");
  }
  function fillPicker() {
    if (!days.length) return;
    const keep = fromSel.value;
    fromSel.innerHTML = "";
    days.forEach(x => fromSel.add(new Option(fmt(x.d) + (x.d === pageDay ? " (this page)" : ""), x.d)));
    const start = days.find(x => x.d >= pageDay) || days[days.length - 1];
    fromSel.value = chain && keep ? keep : start.d;
  }
  function refresh() {
    const hasOwn = ownOk && ownIdx() >= 0;
    player.hidden = !(hasOwn || chain || (cur >= 0 && !player.paused));
    allBtn.hidden = hasOwn || !canSpeak;
    bar.hidden = days.length === 0;
  }
  function next(step) {
    const i = cur + step;
    if (i < 0 || i >= days.length) return false;
    const follow = cur >= 0 && days[cur].d === pageDay;   // page was showing what played
    load(i);
    player.play().catch(() => {});
    if (follow) go(days[i].d, true);
    return true;
  }

  // ---- move between days without reloading (audio keeps playing) ----
  async function go(day, push) {
    if (!day || day === pageDay) return;
    stopSpeech();
    main.classList.add("swapping");
    try {
      const r = await fetch(`${day}.html`, { cache: "no-cache" });
      if (!r.ok) throw new Error(r.status);
      const doc = new DOMParser().parseFromString(await r.text(), "text/html");
      const newMain = doc.querySelector("main");
      const newHeader = newMain && newMain.querySelector("header");
      const header = main.querySelector("header");
      if (!newHeader || !header) throw new Error("unexpected page");
      [...header.children].forEach(el => { if (el !== controls) el.remove(); });
      [...newHeader.children].forEach(el => {
        if (!el.classList.contains("controls")) header.insertBefore(document.importNode(el, true), controls);
      });
      [...main.children].forEach(el => { if (el !== header) el.remove(); });
      [...newMain.children].forEach(el => {
        if (el.tagName !== "HEADER") main.append(document.importNode(el, true));
      });
      pageDay = day;
      main.dataset.day = day;
      at = readAt(doc);
      ownOk = true;
      document.title = doc.title;
      if (push) history.pushState({ day }, "", `${day}.html`);
      showSay();
      fillPicker();
      refresh();
      window.scrollTo(0, 0);
    } catch (e) {
      location.href = `${day}.html`;   // fall back to a normal page load
    } finally {
      main.classList.remove("swapping");
    }
  }
  history.replaceState({ day: pageDay }, "");
  window.addEventListener("popstate", e => { if (e.state && e.state.day) go(e.state.day, false); });

  // ---- browser speech (fallback for days without audio) ----
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

  // ---- controls (delegated, so swapped-in content works too) ----
  document.addEventListener("click", e => {
    const link = e.target.closest("nav.days a, footer a");
    if (link && !e.metaKey && !e.ctrlKey && !e.shiftKey && !e.altKey) {
      const m = (link.getAttribute("href") || "").match(DAY_LINK);
      if (m) { e.preventDefault(); go(m[1], true); }
      return;
    }
    const btn = e.target.closest(".say");
    if (!btn) return;
    const li = btn.closest("li");
    const i = ownIdx();
    if (!(ownOk && i >= 0)) return active === btn ? stopSpeech() : speak([text(li)], btn);
    chain = false;
    load(i);
    refresh();
    const t = (at[trackLang(i)] || {})[li.dataset.id];
    // Start playback inside the tap (required on iOS), then seek once we can.
    const seek = () => { if (t != null) player.currentTime = t; };
    if (player.readyState >= 1) seek(); else player.addEventListener("loadedmetadata", seek, { once: true });
    player.play().catch(() => {});
  });

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

  goBtn.addEventListener("click", () => {
    const i = days.findIndex(x => x.d === fromSel.value);
    if (i < 0) return;
    stopSpeech();
    chain = true;
    load(i);
    refresh();
    if (player.currentTime) player.currentTime = 0;
    player.play().catch(() => {});
    go(days[i].d, true);   // show the day being played
  });

  langSel.addEventListener("change", () => {
    try { localStorage.setItem("say-lang", lang()); } catch (e) {}
    stopSpeech();
    player.pause();
    if (cur >= 0) load(cur);
    refresh();
  });

  player.addEventListener("play", () => {
    stopSpeech();
    player.classList.add("docked");
    document.body.classList.add("has-dock");
  });
  player.addEventListener("ended", () => {
    if (chain && next(1)) return;
    chain = false;
    status();
    player.classList.remove("docked");
    document.body.classList.remove("has-dock");
  });
  player.addEventListener("error", () => {
    if (!player.getAttribute("src")) return;
    if (chain && cur >= 0) {          // a day's file is gone: skip it
      days.splice(cur, 1);
      cur -= 1;
      if (!next(1)) { chain = false; status(); }
      return;
    }
    ownOk = false;
    refresh();
  });
  if ("mediaSession" in navigator) {
    try {
      navigator.mediaSession.setActionHandler("nexttrack", () => { chain = true; next(1); });
      navigator.mediaSession.setActionHandler("previoustrack", () => { chain = true; next(-1); });
    } catch (e) {}
  }
  document.addEventListener("play", e => {
    if (e.target !== player && e.target.tagName === "AUDIO") { stopSpeech(); player.pause(); }
  }, true);
  window.addEventListener("pagehide", stopSpeech);

  if (days.length) load(0);
  refresh();

  // The full list of days with audio, so replay can run up to the latest.
  fetch("audio/index.json", { cache: "no-cache" })
    .then(r => (r.ok ? r.json() : null))
    .then(m => {
      if (!m || !Array.isArray(m.days) || !m.days.length) return;
      const playingSrc = player.getAttribute("src");
      days = m.days;
      cur = days.findIndex(x => x.en === playingSrc || x.zh === playingSrc);
      if (cur < 0 && ownIdx() >= 0) load(ownIdx());
      fillPicker();
      refresh();
    })
    .catch(() => {});
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
            days.setdefault(m.group(1), {"d": m.group(1)})[m.group(2)] = f"audio/{f.name}"
    if audio_dir.exists():
        manifest = {"days": [days[d] for d in sorted(days)]}
        (audio_dir / "index.json").write_text(json.dumps(manifest, separators=(",", ":")), encoding="utf-8")

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
        if 'id="say-lang"' in new:          # pages built before listening controls existed have no script
            new = _SCRIPT.sub(lambda m: script + m.group(1), new, count=1)
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
