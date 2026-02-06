# Collect YouTube Shorts Data (Free)

Collect metadata (title, views, likes, release date) and transcripts for all shorts from a YouTube channel using free, open-source libraries. No API keys required.

## Instructions

Run the full YouTube Shorts data collection pipeline using `youtube_shorts_free.py`.

### Step 1: Gather inputs

Ask the user for any missing inputs before running the script:

1. **Channel URL** — Use the argument provided below. If blank, ask the user which YouTube channel to scrape. The URL should look like `https://www.youtube.com/@channelname/shorts`.
2. **Output filename** — Optionally ask if they want a custom output filename, otherwise it auto-derives from the channel handle.
3. **Whisper fallback** — Ask if they want Whisper transcription for videos without YouTube captions (requires `openai-whisper` and `ffmpeg`). Default: yes if available.
4. **Browser cookies** — Ask if they want to use browser cookies to avoid YouTube bot detection (e.g. `chrome`, `firefox`, `edge`). Default: no.

### Step 2: Verify dependencies

Run `pip install scrapetube yt-dlp youtube-transcript-api` to ensure the core dependencies are installed.

If the user wants Whisper fallback, also run `pip install openai-whisper` and verify `ffmpeg` is on PATH (`ffmpeg -version`).

### Step 3: Run the collector

Run the script with the gathered inputs:

```
python youtube_shorts_free.py --channel "<CHANNEL_URL>"
```

Add optional flags as needed:
- `--output <FILENAME>` for custom output filename
- `--whisper-model <SIZE>` to change Whisper model (tiny/base/small/medium/large)
- `--no-whisper` to skip Whisper fallback
- `--cookies-from-browser <BROWSER>` to use browser cookies

### Step 4: Report results

After the script completes:
- Report how many shorts were collected and how many have transcripts
- Show a sample entry from the output JSON
- If the script failed, inspect the error output and suggest fixes (common issues: YouTube rate limiting, ffmpeg not found, missing dependencies)

### Step 5: Follow-up

Ask the user if they want to:
- Inspect or filter the collected data
- Re-run for a different channel
- Retry any failed transcripts
- Export to a different format (CSV, etc.)

## Arguments

Channel URL: $ARGUMENTS
