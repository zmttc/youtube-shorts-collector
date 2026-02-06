"""
YouTube Shorts Data Collector
Collects metadata (title, views, likes, release date) and transcripts
for all shorts from a given YouTube channel using Apify actors.

Usage:
    python youtube_shorts_collector.py
    python youtube_shorts_collector.py --channel "https://www.youtube.com/@channelname/shorts"
    python youtube_shorts_collector.py --api-key YOUR_KEY --channel "https://www.youtube.com/@channelname/shorts"

Environment variable:
    Set APIFY_API_KEY to skip the interactive prompt.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

try:
    from apify_client import ApifyClient
except ImportError:
    print("Missing dependency. Install it with:")
    print("  pip install apify-client")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Metadata collection
# ---------------------------------------------------------------------------

METADATA_ACTORS = [
    {
        "name": "streamers/youtube-scraper",
        "build_input": lambda url: {
            "startUrls": [{"url": url}],
            "maxResults": 1000,
        },
    },
    {
        "name": "apidojo/youtube-scraper",
        "build_input": lambda url: {
            "startUrls": [{"url": url}],
            "maxResultsShorts": 1000,
            "scrapeShorts": True,
        },
    },
    {
        "name": "clockworks/youtube-channel-scraper",
        "build_input": lambda url: {
            "startUrls": [{"url": url}],
            "maxResults": 1000,
        },
    },
]


def collect_shorts_metadata(client, channel_url):
    """Try each metadata actor in order; return results from the first that succeeds."""
    print(f"[{_ts()}] Starting shorts metadata collection...")
    print(f"Channel URL: {channel_url}")

    for actor_cfg in METADATA_ACTORS:
        actor_name = actor_cfg["name"]
        run_input = actor_cfg["build_input"](channel_url)
        try:
            print(f"  Trying {actor_name}...")
            run = client.actor(actor_name).call(run_input=run_input)
            data = list(client.dataset(run["defaultDatasetId"]).iterate_items())
            if data:
                print(f"  Success — {len(data)} shorts collected")
                return data
        except Exception as e:
            print(f"  Failed: {e}")

    return []


# ---------------------------------------------------------------------------
# Transcript collection
# ---------------------------------------------------------------------------

# Each entry: (actor_name, build_input_fn, batch?)
# batch=True  -> send all URLs at once
# batch=False -> send one URL per call
TRANSCRIPT_ACTORS = [
    ("tictechid/anoxvanzi-Transcriber",              lambda urls: {"start_urls": [{"url": u} for u in urls]}, True),
    ("stanvanrooy6/youtube-transcriber-gpt4o",        lambda urls: {"urls": urls},                            True),
    ("vittuhy/audio-and-video-transcript",            lambda urls: {"urls": urls},                            True),
    ("practicaltools/apify-youtube-transcribe",       lambda urls: {"videoUrl": urls[0]},                     False),
    ("aizen0/video-to-text-transcription",            lambda urls: {"urls": urls},                            True),
    ("cheapget/video-to-text",                        lambda urls: {"video_url": urls[0]},                    False),
    ("crawlmaster/youtube-transcript-fetcher",        lambda urls: {"startUrls": [{"url": u} for u in urls]}, True),
    ("starvibe/youtube-video-transcript",             lambda urls: {"videoUrls": urls},                       True),
    ("karamelo/youtube-transcripts",                  lambda urls: {"urls": urls},                            True),
    ("dz_omar/youtube-transcript-metadata-extractor", lambda urls: {"startUrls": [{"url": u} for u in urls]}, True),
    ("scrapestorm/Youtube-transcript-Videos",         lambda urls: {"startUrls": [{"url": u} for u in urls]}, True),
]


def _has_transcript(items):
    return items and any(
        t.get("transcript") or t.get("text") for t in items
    )


def _run_batch_actor(client, actor_name, build_input, urls):
    run = client.actor(actor_name).call(run_input=build_input(urls))
    return list(client.dataset(run["defaultDatasetId"]).iterate_items())


def _run_single_actor(client, actor_name, build_input, urls):
    all_items = []
    for url in urls:
        try:
            run = client.actor(actor_name).call(run_input=build_input([url]))
            all_items.extend(
                client.dataset(run["defaultDatasetId"]).iterate_items()
            )
        except Exception as e:
            print(f"    Failed for {url}: {e}")
    return all_items


def collect_transcripts(client, shorts_data):
    """Try each transcript actor in fallback order."""
    print(f"\n[{_ts()}] Starting transcript collection...")

    video_urls = []
    for short in shorts_data:
        url = short.get("url") or short.get("videoUrl")
        if not url:
            vid = short.get("id") or short.get("videoId")
            if vid:
                url = f"https://www.youtube.com/shorts/{vid}"
        if url:
            video_urls.append(url)

    if not video_urls:
        print("  No video URLs found")
        return []

    print(f"  {len(video_urls)} videos to transcribe")

    for actor_name, build_input, is_batch in TRANSCRIPT_ACTORS:
        try:
            print(f"  Trying {actor_name}...")
            if is_batch:
                items = _run_batch_actor(client, actor_name, build_input, video_urls)
            else:
                items = _run_single_actor(client, actor_name, build_input, video_urls)

            if _has_transcript(items):
                print(f"  Success — {len(items)} transcripts collected")
                return items
        except Exception as e:
            print(f"  Failed: {e}")

    return []


# ---------------------------------------------------------------------------
# Merging & export
# ---------------------------------------------------------------------------

def extract_video_id(item):
    """Extract a YouTube video ID from various field names and URL formats."""
    video_id = item.get("id") or item.get("videoId")
    if not video_id:
        url = item.get("url") or item.get("videoUrl") or ""
        for pattern, split_char in [
            ("youtube.com/shorts/", "?"),
            ("youtube.com/watch?v=", "&"),
            ("youtu.be/", "?"),
        ]:
            if pattern in url:
                video_id = url.split(pattern)[-1].split(split_char)[0]
                break
    return video_id


def extract_transcript_text(data):
    """Normalize transcript data (string | dict | list of segments) to plain text."""
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        return data.get("text", "") or data.get("content", "")
    if isinstance(data, list):
        parts = []
        for seg in data:
            if isinstance(seg, dict):
                parts.append(seg.get("text", "") or seg.get("content", ""))
            else:
                parts.append(str(seg))
        return " ".join(parts)
    return str(data)


def merge_data(shorts_data, transcripts):
    """Join metadata with transcripts by video ID."""
    print(f"\n[{_ts()}] Merging data...")

    transcript_map = {}
    for t in transcripts:
        vid = extract_video_id(t)
        if vid:
            text = extract_transcript_text(
                t.get("transcript") or t.get("text") or t.get("captions")
                or t.get("transcription") or t.get("content")
                or t.get("subtitles") or ""
            )
            transcript_map[vid] = text

    final = []
    for short in shorts_data:
        video_id = extract_video_id(short)

        views = short.get("viewCount") or short.get("views") or short.get("view_count")
        if isinstance(views, str):
            views = views.replace(",", "").replace(" views", "")
            try:
                views = int(views)
            except ValueError:
                pass

        likes = short.get("likeCount") or short.get("likes") or short.get("like_count")
        if isinstance(likes, str):
            likes = likes.replace(",", "")
            try:
                likes = int(likes)
            except ValueError:
                pass

        url = short.get("url") or short.get("videoUrl")
        if not url and video_id:
            url = f"https://www.youtube.com/shorts/{video_id}"

        final.append({
            "title": short.get("title") or short.get("name") or "N/A",
            "views": views,
            "likes": likes,
            "release_date": short.get("uploadDate") or short.get("date") or short.get("publishedAt") or "N/A",
            "video_url": url,
            "video_id": video_id,
            "transcript": transcript_map.get(video_id, "N/A"),
        })

    return final


def export_data(final_data, output_file):
    """Write the merged dataset to a JSON file."""
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    with_transcript = sum(1 for d in final_data if d.get("transcript") and d["transcript"] != "N/A")
    print(f"\n{'=' * 50}")
    print(f"Exported to {output_file}")
    print(f"Total shorts: {len(final_data)}")
    print(f"With transcripts: {with_transcript}")

    if final_data:
        s = final_data[0]
        preview = s["transcript"][:100] + "..." if len(str(s["transcript"])) > 100 else s["transcript"]
        print(f"\nSample entry:")
        print(f"  Title: {s['title']}")
        print(f"  Views: {s['views']}")
        print(f"  Likes: {s['likes']}")
        print(f"  Date:  {s['release_date']}")
        print(f"  URL:   {s['video_url']}")
        print(f"  Transcript: {preview}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts():
    return datetime.now().strftime("%H:%M:%S")


def get_api_key(args_key):
    """Resolve API key from CLI arg, env var, or interactive prompt."""
    if args_key:
        return args_key
    env_key = os.environ.get("APIFY_API_KEY")
    if env_key:
        return env_key
    key = input("Enter your Apify API key: ").strip()
    if not key:
        print("No API key provided. Exiting.")
        sys.exit(1)
    return key


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Collect YouTube Shorts data via Apify")
    parser.add_argument("--api-key", help="Apify API key (or set APIFY_API_KEY env var)")
    parser.add_argument("--channel", help="YouTube channel shorts URL")
    parser.add_argument("--output", default=None, help="Output JSON filename")
    args = parser.parse_args()

    api_key = get_api_key(args.api_key)

    channel_url = args.channel
    if not channel_url:
        channel_url = input("Enter the YouTube channel shorts URL (e.g. https://www.youtube.com/@channelname/shorts): ").strip()
    if not channel_url:
        print("No channel URL provided. Exiting.")
        sys.exit(1)

    # Derive a default output filename from the channel handle
    if args.output:
        output_file = args.output
    else:
        handle = channel_url.rstrip("/").split("@")[-1].split("/")[0] if "@" in channel_url else "channel"
        output_file = f"{handle}_shorts_data.json"

    client = ApifyClient(token=api_key)

    print("=" * 50)
    print("YouTube Shorts Data Collector")
    print("=" * 50)

    start = time.time()

    shorts_data = collect_shorts_metadata(client, channel_url)
    if not shorts_data:
        print("\nERROR: Could not collect shorts data. Check channel URL and API key.")
        sys.exit(1)

    transcripts = collect_transcripts(client, shorts_data)
    final_data = merge_data(shorts_data, transcripts)
    export_data(final_data, output_file)

    print(f"\nCompleted in {time.time() - start:.1f} seconds")


if __name__ == "__main__":
    main()
