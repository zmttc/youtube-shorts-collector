# Collect YouTube Shorts Data

Collect metadata (title, views, likes, release date) and transcripts for all shorts from a YouTube channel using Apify.

## Instructions

Run the full YouTube Shorts data collection pipeline using `youtube_shorts_collector.py`.

### Step 1: Gather inputs

Ask the user for any missing inputs before running the script:

1. **Apify API key** — Check if the environment variable `APIFY_API_KEY` is set. If not, ask the user to provide their key. Get one at https://console.apify.com/account/integrations. Never store or display the key in files.
2. **Channel URL** — Use the argument provided below. If blank, ask the user which YouTube channel to scrape. The URL should look like `https://www.youtube.com/@channelname/shorts`.
3. **Output filename** — Optionally ask if they want a custom output filename, otherwise it auto-derives from the channel handle.

### Step 2: Verify dependencies

Run `pip install apify-client` to ensure the dependency is installed.

### Step 3: Run the collector

Run the script with the gathered inputs:

```
python youtube_shorts_collector.py --api-key <KEY> --channel "<CHANNEL_URL>"
```

If the user provided a custom output filename, add `--output <FILENAME>`.

### Step 4: Report results

After the script completes:
- Report how many shorts were collected and how many have transcripts
- Show a sample entry from the output JSON
- If the script failed, inspect the error output and suggest fixes (common issues: invalid API key, channel URL format, Apify rate limits)

### Step 5: Follow-up

Ask the user if they want to:
- Inspect or filter the collected data
- Re-run for a different channel
- Export to a different format (CSV, etc.)

## Arguments

Channel URL: $ARGUMENTS
