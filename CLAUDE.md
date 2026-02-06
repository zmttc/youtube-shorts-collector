# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube Shorts data collection pipeline. Scrapes metadata (title, views, likes, release date) and transcripts for all shorts from a YouTube channel, then merges and exports to JSON. Two variants: a free collector using open-source libraries (no API keys) and an Apify-based collector (paid).

## Three Script Variants

- **`youtube_shorts_collector.py`** — The main public script. Accepts `--api-key`, `--channel`, and `--output` CLI args, or reads `APIFY_API_KEY` from env, or prompts interactively. Uses paid Apify actors.
- **`youtube_shorts_free.py`** — Free alternative that requires **no API keys**. Uses `scrapetube` (list shorts), `yt-dlp` (metadata), and `youtube-transcript-api` (transcripts). Same output format as the Apify-based collector.
- **`youtube_shorts_scraper.py`** — Original prototype with hardcoded API key and channel (`@zehuman0`). Listed in `.gitignore` along with the other helper scripts below.

## Running

### Free collector (no API keys)

```bash
pip install scrapetube yt-dlp youtube-transcript-api

# Basic usage (captions only)
python youtube_shorts_free.py --channel "https://www.youtube.com/@channelname/shorts"

# With Whisper fallback for videos without captions
pip install openai-whisper   # also requires ffmpeg on PATH
python youtube_shorts_free.py --channel "https://www.youtube.com/@channelname/shorts" --whisper-model base

# Skip Whisper, captions only
python youtube_shorts_free.py --channel "https://www.youtube.com/@channelname/shorts" --no-whisper

# Use browser cookies to avoid YouTube bot detection
python youtube_shorts_free.py --channel "https://www.youtube.com/@channelname/shorts" --cookies-from-browser chrome
```

**CLI options:**
| Flag | Default | Description |
|------|---------|-------------|
| `--channel` | *(interactive prompt)* | YouTube channel shorts URL |
| `--output` | `<handle>_shorts_data.json` | Output JSON filename |
| `--whisper-model` | `base` | Whisper model size: `tiny`, `base`, `small`, `medium`, `large` |
| `--no-whisper` | off | Skip Whisper fallback, only use YouTube captions |
| `--cookies-from-browser` | *(none)* | Browser to extract cookies from (`chrome`, `firefox`, `edge`) |

### Apify-based collector (requires paid API key)

```bash
pip install apify-client

python youtube_shorts_collector.py --api-key YOUR_KEY --channel "https://www.youtube.com/@channelname/shorts"

# Or via env var
set APIFY_API_KEY=YOUR_KEY
python youtube_shorts_collector.py --channel "https://www.youtube.com/@channelname/shorts"
```

No build step, no tests, no virtual environment required.

### Claude Code Skills

- **`/project:collect-shorts-free`** — Runs the free collector (no API keys). Invoke with:
  ```
  /project:collect-shorts-free https://www.youtube.com/@channelname/shorts
  ```
- **`/project:collect-shorts`** — Runs the Apify-based collector (requires paid API key). Invoke with:
  ```
  /project:collect-shorts https://www.youtube.com/@channelname/shorts
  ```

### Diagnostic Scripts (gitignored, hardcoded API key)

```bash
python find_actors.py               # Discover available Apify actors for transcription
python check_transcripts.py         # Inspect recent Apify run results
python check_transcript_structure.py # Debug transcript field format from a specific run
python get_full_transcripts.py      # Fetch transcripts from known run IDs and save to JSON
```

## Architecture

### Apify-based pipeline (`youtube_shorts_collector.py`)

1. `collect_shorts_metadata()` — Tries metadata actors in fallback order: `streamers/youtube-scraper` → `apidojo/youtube-scraper` → `clockworks/youtube-channel-scraper`
2. `collect_transcripts()` — Tries ~11 transcription actors in fallback order (speech-to-text, Whisper, GPT-4o, etc.). Some are batch (all URLs at once), some are single-URL-per-call.
3. `merge_data()` — Joins metadata and transcripts by video ID
4. `export_data()` — Writes output JSON

**Fallback pattern:** Both metadata and transcript collection try each Apify actor in sequence; the first successful result is returned. Actors are configured as data in `METADATA_ACTORS` and `TRANSCRIPT_ACTORS` lists. To add a new actor, append an entry to the relevant list.

### Free pipeline (`youtube_shorts_free.py`)

1. `list_shorts()` — Uses `scrapetube` to enumerate all video IDs from the channel's Shorts tab
2. `collect_metadata()` — Uses `yt-dlp` Python API to extract title, view count, like count, upload date per video (no download)
3. `collect_transcripts()` — Two-phase transcript collection:
   - **Phase 1:** `youtube-transcript-api` fetches auto-generated/manual YouTube captions
   - **Phase 2 (Whisper fallback):** For videos without captions, downloads audio via `yt-dlp` and transcribes locally with OpenAI Whisper. Requires `pip install openai-whisper` and `ffmpeg` on PATH. Disable with `--no-whisper`.
4. `merge_data()` + `export_data()` — Same merge and export as the Apify pipeline

**Rate limiting:** YouTube may throttle unauthenticated requests after many consecutive downloads. Use `--cookies-from-browser` to pass browser cookies, or wait for cooldown between runs.

**Transcript field normalization:** Transcripts arrive in varied formats (string, dict, or list of segments). `extract_transcript_text()` normalizes all three to plain text.

**Video ID extraction:** `extract_video_id()` handles multiple URL formats (`/shorts/`, `/watch?v=`, `youtu.be/`) and field names (`id`, `videoId`, `url`, `videoUrl`).

## Output

`<handle>_shorts_data.json` — Array of objects with fields: `title`, `views`, `likes`, `release_date`, `video_url`, `video_id`, `transcript`.
