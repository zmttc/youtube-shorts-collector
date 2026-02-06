# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube Shorts data collection pipeline for channel `@zehuman0`. Scrapes metadata (title, views, likes, release date) and transcripts for all shorts, then merges and exports them to JSON.

## Running Scripts

All scripts are standalone Python files run directly:

```bash
python youtube_shorts_scraper.py    # Main pipeline: metadata + transcripts + merge + export
python find_actors.py               # Discover available Apify actors for transcription
python check_transcripts.py         # Inspect recent Apify run results
python check_transcript_structure.py # Debug transcript field format from a specific run
python get_full_transcripts.py      # Fetch transcripts from known run IDs and save to JSON
```

No build step, no tests, no virtual environment setup beyond `pip install apify-client`.

## Architecture

**External dependency:** All scraping goes through [Apify](https://apify.com/) actors via the `apify_client` Python SDK. The API key is hardcoded in each script.

**Main pipeline (`youtube_shorts_scraper.py`):**
1. `collect_shorts_metadata()` — Tries multiple Apify YouTube scraper actors in fallback order (`streamers/youtube-scraper` → `apidojo/youtube-scraper` → `clockworks/youtube-channel-scraper`)
2. `collect_transcripts()` — Tries ~10 different Apify transcription actors in fallback order (speech-to-text, Whisper, GPT-4o based, etc.)
3. `merge_data()` — Joins metadata and transcripts by video ID
4. `export_data()` — Writes `zehuman0_shorts_data.json`

**Fallback pattern:** Both metadata and transcript collection use a cascading try/except pattern — each actor is attempted in sequence, and the first successful result is returned. When adding a new actor, append a new try/except block following the same structure.

**Transcript field normalization:** Transcripts can arrive as strings, dicts, or lists of segments. `merge_data()` and `get_full_transcripts.py:extract_transcript_text()` handle all three formats.

**Video ID extraction:** `extract_video_id()` handles multiple URL formats (`/shorts/`, `/watch?v=`, `youtu.be/`) and field names (`id`, `videoId`, `url`, `videoUrl`).

**Helper scripts** (`check_transcripts.py`, `check_transcript_structure.py`, `get_full_transcripts.py`) are diagnostic/one-off scripts for inspecting Apify run results by run ID.

## Output

`zehuman0_shorts_data.json` — Array of objects with fields: `title`, `views`, `likes`, `release_date`, `video_url`, `video_id`, `transcript`.
