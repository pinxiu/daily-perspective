"""Pull recent items from RSS/Atom feeds."""
from __future__ import annotations

import calendar
import html
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, urlunsplit

import feedparser

USER_AGENT = "daily-perspective/1.0"
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


@dataclass
class Item:
    title: str
    url: str
    source: str
    summary: str
    published: datetime | None
    audio: str = ""        # podcast/audio enclosure URL, if the feed provides one


def _clean(text: str, limit: int = 400) -> str:
    text = html.unescape(_TAG_RE.sub(" ", text or ""))
    text = _WS_RE.sub(" ", text).strip()
    return text if len(text) <= limit else text[: limit - 1].rsplit(" ", 1)[0] + "…"


def _published(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            # feedparser normalizes to UTC struct_time
            return datetime.fromtimestamp(calendar.timegm(t), tz=timezone.utc)
    return None


_AUDIO_EXT = re.compile(r"\.(mp3|m4a|aac|ogg|opus|wav)(\?|$)", re.I)


def _audio(entry) -> str:
    """Return the entry's audio URL from enclosures or media:content, if any."""
    candidates = list(entry.get("enclosures", []))
    candidates += [l for l in entry.get("links", []) if l.get("rel") == "enclosure"]
    candidates += list(entry.get("media_content", []))
    for c in candidates:
        url = c.get("href") or c.get("url") or ""
        kind = (c.get("type") or c.get("medium") or "").lower()
        if url.startswith("http") and (kind.startswith("audio") or _AUDIO_EXT.search(url)):
            return url
    return ""


def _norm_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path.rstrip("/"), "", ""))


def fetch_feed(url: str, since: datetime, limit: int) -> list[Item]:
    parsed = feedparser.parse(url, agent=USER_AGENT)
    if parsed.bozo and not parsed.entries:
        print(f"  ! could not read {url}: {parsed.get('bozo_exception')}")
        return []
    source = parsed.feed.get("title") or urlsplit(url).netloc
    items: list[Item] = []
    for entry in parsed.entries:
        pub = _published(entry)
        if pub and pub < since:
            continue
        link = entry.get("link")
        title = _clean(entry.get("title", ""), 200)
        if not link or not title:
            continue
        items.append(
            Item(
                title=title,
                url=link,
                source=_clean(source, 60),
                summary=_clean(entry.get("summary", "")),
                published=pub,
                audio=_audio(entry),
            )
        )
        if len(items) >= limit:
            break
    return items


def fetch_category(feeds: list[str], lookback_hours: int, per_feed: int) -> list[Item]:
    """Fetch every feed in a category, drop duplicates, newest first."""
    since = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    out: list[Item] = []
    for url in feeds:
        for item in fetch_feed(url, since, per_feed):
            key_url, key_title = _norm_url(item.url), item.title.lower()
            if key_url in seen_urls or key_title in seen_titles:
                continue
            seen_urls.add(key_url)
            seen_titles.add(key_title)
            out.append(item)
    epoch = datetime.min.replace(tzinfo=timezone.utc)
    out.sort(key=lambda i: i.published or epoch, reverse=True)
    return out
