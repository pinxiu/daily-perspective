# Daily Perspective

A self-updating daily news digest across AI, tech, world affairs and humanitarian news, the economy, and stories chosen to widen perspective and build compassion.

Every morning a GitHub Action pulls the last ~30 hours of stories from RSS feeds, asks Claude to pick the most significant ones in each section and explain why they matter (and whose viewpoint is easy to miss), then publishes:

- `docs/index.html`: today's digest, served by GitHub Pages
- `docs/YYYY-MM-DD.html`: that day's page, kept forever and linked from every page's "Earlier days" footer
- `docs/feed.xml`: an RSS feed of daily digests, for any feed reader
- `digests/YYYY-MM-DD.md`: a Markdown archive that renders nicely on GitHub
- an email with that day's highlights, if SMTP is configured (see below)

Every Sunday, a second GitHub Action reads the full `digests/` archive, asks Claude how each category (AI, tech, world, economy, ...) has been trending over time — what's recurring, escalating, resolving, or new — and emails that summary. It's also archived to `digests/weekly/YYYY-MM-DD.md`.

The digest is bilingual: Claude writes a Simplified Chinese translation alongside every overview, story, and reflection. The site shows them side by side, stacking to English-then-Chinese on narrow screens; the Markdown archive and emails show English then Chinese underneath.

Without an API key it still works and produces a headlines-only digest with no translation (and the weekly job has nothing to summarize, so it skips itself).

## Setup

1. **Push this repo to GitHub** (see below).
2. **Add your API key:** Settings → Secrets and variables → Actions → New repository secret, named `ANTHROPIC_API_KEY`. Use a normal workspace API key (starts `sk-ant-api03-...`, created while inside a specific workspace in the Console) — not an Admin API key (`sk-ant-admin-...`), which can't call the model and fails with an "API key is not scoped to a workspace" error.
3. **Turn on Pages:** Settings → Pages → Deploy from a branch → `main`, folder `/docs`.
4. **Run it once:** Actions → Daily digest → Run workflow. Your digest will be at `https://<user>.github.io/<repo>/`.

### Email (optional)

Sent over Gmail SMTP using an [App Password](https://myaccount.google.com/apppasswords) (requires 2-Step Verification on the sending Google account — it can be the same Gmail account the digest goes to, or a separate one you send *from*).

1. Turn on 2-Step Verification on the sending Google account, then create an App Password for "Mail".
2. Add two repository secrets: `SMTP_USERNAME` (the sending Gmail address) and `SMTP_APP_PASSWORD` (the 16-character App Password).
3. Optionally add the repository *variable* `EMAIL_TO` to send somewhere other than `pinxiu.gong@gmail.com`.

Both the daily and weekly workflows check for these secrets and silently skip sending (still writing the archive) if they're not set.

Optional repository *variables* (same settings page, Variables tab):

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_MODEL` | `claude-sonnet-5` | Model used for summaries |
| `DIGEST_TZ` | `America/Los_Angeles` | Time zone used to date each digest |
| `EMAIL_TO` | `pinxiu.gong@gmail.com` | Where daily/weekly emails are sent |

To change the delivery time, edit the `cron` line in `.github/workflows/daily.yml` (daily digest) or `.github/workflows/weekly.yml` (weekly trends) — both are in UTC.

## Customizing

Everything editorial lives in `feeds.yaml`: add or remove feeds, add new sections, and adjust each section's `focus`, which tells Claude what to prioritize. New section ids get a neutral accent color; add one to `ACCENTS` in `daily_feed/render.py` if you like. Give a new section a `name_zh` too, for its Chinese heading.

The editor's voice (tone, the "perspective" line, the daily reflection) lives in the prompts at the top of `daily_feed/summarize.py`.

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # optional
export SMTP_USERNAME=you@gmail.com    # optional, to test email
export SMTP_APP_PASSWORD=...          # optional, to test email
python -m daily_feed
open docs/index.html

python -m daily_feed.weekly            # optional, needs a few days of digests/ archived first
```

## Cost

Six small Claude calls a day (one per section plus the reflection), on the order of 30–40k input tokens total. The weekly trends job adds one small call per category, once a week.

## Listening

- **Podcasts:** when a feed item carries an audio enclosure, the page shows a player so you can listen right there (and the email links to the episode).
- **Everything else:** each story has a "Read aloud" button, and the header has "Read today's briefing aloud". It uses your browser's built-in speech in English or 中文, so it costs nothing and needs no audio files. Chinese needs a Chinese voice installed on your device (standard on iOS, macOS, Android and Windows).

## Keeping AI costs low

- Each section is written in English with a compact prompt (at most 25 candidates, 200-character snippets).
- The whole day's Chinese is produced in **one** translation call on a cheaper model (default Claude Haiku 4.5; override with a `TRANSLATE_MODEL` env var).
- Scheduled runs skip a day that's already built; "Run workflow" always rebuilds.
- Weekly trends are one call over the last 28 days of English overviews.
- The Actions log prints tokens used per run.
