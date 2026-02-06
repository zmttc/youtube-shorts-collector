# YouTube Shorts Data Collector

Collect metadata (title, views, likes, release date) and transcripts for all YouTube Shorts from any channel using [Apify](https://apify.com/) actors.

## Requirements

- Python 3.8+
- An [Apify API key](https://console.apify.com/account/integrations)

## Setup

```bash
pip install apify-client
```

## Usage

### As a standalone script

```bash
# Interactive — prompts for API key and channel
python youtube_shorts_collector.py

# Fully scripted
python youtube_shorts_collector.py --api-key YOUR_KEY --channel "https://www.youtube.com/@channelname/shorts"

# Via environment variable
export APIFY_API_KEY=YOUR_KEY
python youtube_shorts_collector.py --channel "https://www.youtube.com/@channelname/shorts" --output results.json
```

### As a Claude Code skill

If you use [Claude Code](https://claude.ai/code), drop the `.claude/commands/` folder into your project and run:

```
/project:collect-shorts https://www.youtube.com/@channelname/shorts
```

Claude will walk you through providing your API key, run the collector, and report the results.

## Output

A JSON file (named after the channel handle) containing an array of objects:

```json
{
  "title": "Video Title",
  "views": 12345,
  "likes": 678,
  "release_date": "2025-01-01T00:00:00+00:00",
  "video_url": "https://www.youtube.com/shorts/...",
  "video_id": "abc123",
  "transcript": "Full transcript text..."
}
```

## How it works

The script uses a cascading fallback strategy — it tries multiple Apify actors in sequence for both metadata scraping and transcription, using the first one that succeeds. This makes it resilient to individual actor outages or rate limits.
