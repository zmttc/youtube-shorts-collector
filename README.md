# YouTube Shorts Collector FOR FREE

Collect metadata (title, views, likes, release date) and transcripts for all YouTube Shorts from any channel — **no API keys required**.

Uses free, open-source libraries: [scrapetube](https://github.com/dermasmid/scrapetube), [yt-dlp](https://github.com/yt-dlp/yt-dlp), [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api), and optionally [OpenAI Whisper](https://github.com/openai/whisper) for local transcription when no captions exist.

## Requirements

- Python 3.8+
- ffmpeg on PATH (required for Whisper fallback)

## Setup

```bash
pip install scrapetube yt-dlp youtube-transcript-api

# Optional: for Whisper transcription fallback
pip install openai-whisper
```

## Usage

### Free collector (recommended)

```bash
# Basic — uses YouTube captions for transcripts
python youtube_shorts_free.py --channel "https://www.youtube.com/@channelname/shorts"

# With Whisper fallback for videos without captions
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

### Apify-based collector (alternative, requires paid API key)

```bash
pip install apify-client

python youtube_shorts_collector.py --api-key YOUR_KEY --channel "https://www.youtube.com/@channelname/shorts"
```

### As a Claude Code skill

If you use [Claude Code](https://claude.ai/code), the `.claude/commands/` folder includes two skills:

```
/project:collect-shorts-free https://www.youtube.com/@channelname/shorts
/project:collect-shorts https://www.youtube.com/@channelname/shorts
```

## Output

A JSON file (named after the channel handle) containing an array of objects:

```json
{
  "title": "Video Title",
  "views": 12345,
  "likes": 678,
  "release_date": "2025-01-01",
  "video_url": "https://www.youtube.com/shorts/...",
  "video_id": "abc123",
  "transcript": "Full transcript text..."
}
```

## How it works

### Free pipeline (`youtube_shorts_free.py`)

1. **List shorts** — `scrapetube` enumerates all video IDs from the channel's Shorts tab
2. **Collect metadata** — `yt-dlp` extracts title, view count, like count, and upload date per video (no download)
3. **Collect transcripts** — Two-phase approach:
   - **Phase 1:** `youtube-transcript-api` fetches YouTube captions (auto-generated or manual)
   - **Phase 2:** For videos without captions, downloads audio via `yt-dlp` and transcribes locally with OpenAI Whisper
4. **Export** — Merges metadata and transcripts into a single JSON file

### Apify pipeline (`youtube_shorts_collector.py`)

Uses a cascading fallback strategy — tries multiple Apify actors in sequence for both metadata scraping and transcription, using the first one that succeeds.
