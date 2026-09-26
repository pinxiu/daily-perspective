# Daily Perspective

A self-updating daily news digest across AI, tech, world affairs and humanitarian news, the economy, and stories chosen to widen perspective and build compassion.

Every morning a GitHub Action pulls the last ~30 hours of stories from RSS feeds, asks Claude to pick the most significant ones in each section and explain why they matter (and whose viewpoint is easy to miss), then publishes:

- `docs/index.html`: today's digest, served by GitHub Pages
- `docs/feed.xml`: an RSS feed of daily digests, for any feed reader
- `digests/YYYY-MM-DD.md`: a Markdown archive that renders nicely on GitHub

Without an API key it still works and produces a headlines-only digest.

## Setup

1. **Push this repo to GitHub** (see below).
2. **Add your API key:** Settings → Secrets and variables → Actions → New repository secret, named `ANTHROPIC_API_KEY`.
3. **Turn on Pages:** Settings → Pages → Deploy from a branch → `main`, folder `/docs`.
4. **Run it once:** Actions → Daily digest → Run workflow. Your digest will be at `https://<user>.github.io/<repo>/`.

Optional repository *variables* (same settings page, Variables tab):

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_MODEL` | `claude-sonnet-5` | Model used for summaries |
| `DIGEST_TZ` | `America/Los_Angeles` | Time zone used to date each digest |

To change the delivery time, edit the `cron` line in `.github/workflows/daily.yml` (it's in UTC).

## Customizing

Everything editorial lives in `feeds.yaml`: add or remove feeds, add new sections, and adjust each section's `focus`, which tells Claude what to prioritize. New section ids get a neutral accent color; add one to `ACCENTS` in `daily_feed/render.py` if you like.

The editor's voice (tone, the "perspective" line, the daily reflection) lives in the prompts at the top of `daily_feed/summarize.py`.

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # optional
python -m daily_feed
open docs/index.html
```

## Cost

Six small Claude calls a day (one per section plus the reflection), on the order of 30–40k input tokens total.
