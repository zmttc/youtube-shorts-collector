"""
YouTube Shorts Data Collector (Free Edition)
Collects metadata (title, views, likes, release date) and transcripts
for all shorts from a given YouTube channel using free, open-source libraries.

No API keys required.

Usage:
    python youtube_shorts_free.py
    python youtube_shorts_free.py --channel "https://www.youtube.com/@zehuman0/shorts"
    python youtube_shorts_free.py --channel "https://www.youtube.com/@zehuman0/shorts" --output my_data.json

Dependencies:
    pip install scrapetube yt-dlp youtube-transcript-api

Optional (for Whisper fallback when no captions exist):
    pip install openai-whisper
    Also requires ffmpeg on PATH: https://ffmpeg.org/download.html
"""

import argparse
import json
import os
import sys
import tempfile
import time
from datetime import datetime

try:
    import scrapetube
except ImportError:
    print("Missing dependency: scrapetube")
    print("  pip install scrapetube")
    sys.exit(1)

try:
    import yt_dlp
except ImportError:
    print("Missing dependency: yt-dlp")
    print("  pip install yt-dlp")
    sys.exit(1)

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    print("Missing dependency: youtube-transcript-api")
    print("  pip install youtube-transcript-api")
    sys.exit(1)

# Whisper is optional — only needed as fallback when captions are missing
try:
    import whisper as openai_whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False


# ---------------------------------------------------------------------------
# Step 1: List all shorts from a channel
# ---------------------------------------------------------------------------

def list_shorts(channel_url):
    """Use scrapetube to get all video IDs from the channel's Shorts tab."""
    print(f"[{_ts()}] Listing shorts from channel...")

    # scrapetube expects the channel URL or handle
    # It supports content_type="shorts" to filter for shorts only
    videos = scrapetube.get_channel(channel_url=channel_url, content_type="shorts")

    video_ids = []
    for video in videos:
        video_id = video.get("videoId")
        if video_id:
            video_ids.append(video_id)

    print(f"  Found {len(video_ids)} shorts")
    return video_ids


# ---------------------------------------------------------------------------
# Step 2: Get metadata for each video via yt-dlp
# ---------------------------------------------------------------------------

def _ydl_base_opts(cookies_browser=None):
    """Return base yt-dlp options, optionally with browser cookie auth."""
    opts = {"quiet": True, "no_warnings": True}
    if cookies_browser:
        opts["cookiesfrombrowser"] = (cookies_browser,)
    return opts


def get_video_metadata(video_id, cookies_browser=None):
    """Use yt-dlp to extract metadata for a single video (no download)."""
    url = f"https://www.youtube.com/shorts/{video_id}"
    ydl_opts = {**_ydl_base_opts(cookies_browser), "skip_download": True}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        upload_date = info.get("upload_date", "")
        if upload_date and len(upload_date) == 8:
            # Convert YYYYMMDD to YYYY-MM-DD
            upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"

        return {
            "title": info.get("title", "N/A"),
            "views": info.get("view_count"),
            "likes": info.get("like_count"),
            "release_date": upload_date or "N/A",
            "video_url": url,
            "video_id": video_id,
        }
    except Exception as e:
        print(f"    Failed to get metadata for {video_id}: {e}")
        return {
            "title": "N/A",
            "views": None,
            "likes": None,
            "release_date": "N/A",
            "video_url": url,
            "video_id": video_id,
        }


def collect_metadata(video_ids, cookies_browser=None):
    """Get metadata for all videos with progress reporting."""
    print(f"\n[{_ts()}] Collecting metadata for {len(video_ids)} videos...")

    results = []
    for i, video_id in enumerate(video_ids, 1):
        if i % 10 == 0 or i == 1:
            print(f"  Processing {i}/{len(video_ids)}...")

        metadata = get_video_metadata(video_id, cookies_browser)
        results.append(metadata)

        # Small delay to avoid rate limiting
        time.sleep(0.5)

    successful = sum(1 for r in results if r["title"] != "N/A")
    print(f"  Metadata collected: {successful}/{len(video_ids)} successful")
    return results


# ---------------------------------------------------------------------------
# Step 3: Get transcripts via youtube-transcript-api + Whisper fallback
# ---------------------------------------------------------------------------

def get_transcript_captions(video_id):
    """Fetch YouTube captions for a single video. Returns text or None."""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join(segment["text"] for segment in transcript_list)
        return text
    except Exception:
        return None


def download_audio(video_id, temp_dir, cookies_browser=None):
    """Download audio for a video using yt-dlp. Returns path to audio file or None."""
    url = f"https://www.youtube.com/shorts/{video_id}"
    output_path = os.path.join(temp_dir, f"{video_id}.%(ext)s")
    ydl_opts = {
        **_ydl_base_opts(cookies_browser),
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "96",
        }],
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        audio_path = os.path.join(temp_dir, f"{video_id}.mp3")
        if os.path.exists(audio_path):
            return audio_path
    except Exception as e:
        print(f"    Audio download failed for {video_id}: {e}")
    return None


def whisper_transcribe(audio_path, model):
    """Transcribe an audio file using Whisper. Returns text or None."""
    try:
        result = model.transcribe(audio_path)
        return result.get("text", "").strip() or None
    except Exception as e:
        print(f"    Whisper transcription failed: {e}")
        return None


def collect_transcripts(video_ids, whisper_model_name="base", use_whisper=True,
                        cookies_browser=None):
    """Get transcripts: try captions first, then Whisper fallback for failures."""
    print(f"\n[{_ts()}] Collecting transcripts for {len(video_ids)} videos...")
    print("  Phase 1: Fetching YouTube captions...")

    transcript_map = {}
    missing = []

    for i, video_id in enumerate(video_ids, 1):
        if i % 10 == 0 or i == 1:
            print(f"    Processing {i}/{len(video_ids)}...")

        text = get_transcript_captions(video_id)
        if text:
            transcript_map[video_id] = text
        else:
            missing.append(video_id)

        time.sleep(0.3)

    caption_count = len(transcript_map)
    print(f"  Captions found: {caption_count}/{len(video_ids)}")

    # Whisper fallback for videos without captions
    if missing and use_whisper:
        if not WHISPER_AVAILABLE:
            print(f"\n  {len(missing)} videos have no captions.")
            print("  Whisper not installed — install for local transcription fallback:")
            print("    pip install openai-whisper")
            for vid in missing:
                transcript_map[vid] = "N/A"
        else:
            print(f"\n  Phase 2: Whisper fallback for {len(missing)} videos without captions...")
            print(f"    Loading Whisper model '{whisper_model_name}'...")
            model = openai_whisper.load_model(whisper_model_name)

            with tempfile.TemporaryDirectory() as temp_dir:
                for i, video_id in enumerate(missing, 1):
                    if i % 5 == 0 or i == 1:
                        print(f"    Transcribing {i}/{len(missing)}...")

                    audio_path = download_audio(video_id, temp_dir, cookies_browser)
                    if audio_path:
                        text = whisper_transcribe(audio_path, model)
                        transcript_map[video_id] = text if text else "N/A"
                        # Clean up audio file immediately to save disk space
                        try:
                            os.remove(audio_path)
                        except OSError:
                            pass
                    else:
                        transcript_map[video_id] = "N/A"

            whisper_count = sum(1 for vid in missing if transcript_map.get(vid, "N/A") != "N/A")
            print(f"  Whisper transcribed: {whisper_count}/{len(missing)}")
    else:
        for vid in missing:
            transcript_map[vid] = "N/A"

    total = sum(1 for v in transcript_map.values() if v != "N/A")
    print(f"  Total with transcripts: {total}/{len(video_ids)}")
    return transcript_map


# ---------------------------------------------------------------------------
# Merge & export
# ---------------------------------------------------------------------------

def merge_data(metadata_list, transcript_map):
    """Attach transcripts to metadata entries."""
    for entry in metadata_list:
        entry["transcript"] = transcript_map.get(entry["video_id"], "N/A")
    return metadata_list


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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Collect YouTube Shorts data (free, no API keys)")
    parser.add_argument("--channel", default=None, help="YouTube channel shorts URL")
    parser.add_argument("--output", default=None, help="Output JSON filename")
    parser.add_argument("--whisper-model", default="base",
                        help="Whisper model size: tiny, base, small, medium, large (default: base)")
    parser.add_argument("--no-whisper", action="store_true",
                        help="Skip Whisper fallback, only use YouTube captions")
    parser.add_argument("--cookies-from-browser", default=None, metavar="BROWSER",
                        help="Browser to extract cookies from (e.g. chrome, firefox, edge) "
                             "to avoid YouTube bot detection")
    args = parser.parse_args()

    channel_url = args.channel
    if not channel_url:
        channel_url = input("Enter the YouTube channel shorts URL (e.g. https://www.youtube.com/@zehuman0/shorts): ").strip()
    if not channel_url:
        print("No channel URL provided. Exiting.")
        sys.exit(1)

    # Derive a default output filename from the channel handle
    if args.output:
        output_file = args.output
    else:
        handle = channel_url.rstrip("/").split("@")[-1].split("/")[0] if "@" in channel_url else "channel"
        output_file = f"{handle}_shorts_data.json"

    print("=" * 50)
    print("YouTube Shorts Data Collector (Free Edition)")
    print("=" * 50)

    start = time.time()

    # Step 1: List all shorts
    video_ids = list_shorts(channel_url)
    if not video_ids:
        print("\nERROR: Could not find any shorts. Check the channel URL.")
        sys.exit(1)

    cookies_browser = args.cookies_from_browser

    # Step 2: Get metadata
    metadata_list = collect_metadata(video_ids, cookies_browser)

    # Step 3: Get transcripts (captions first, Whisper fallback)
    transcript_map = collect_transcripts(
        video_ids,
        whisper_model_name=args.whisper_model,
        use_whisper=not args.no_whisper,
        cookies_browser=cookies_browser,
    )

    # Step 4: Merge and export
    final_data = merge_data(metadata_list, transcript_map)
    export_data(final_data, output_file)

    print(f"\nCompleted in {time.time() - start:.1f} seconds")


if __name__ == "__main__":
    main()
