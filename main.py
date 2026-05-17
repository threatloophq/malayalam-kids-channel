import os
import json
import shutil
import logging
import traceback
import subprocess
from datetime import datetime
from dotenv import load_dotenv

from modules.trends import get_top_trends
from modules.translator import generate_malayalam_kids_script
from modules.voiceover import generate_voiceover
from modules.publisher import publish_youtube
from modules.thumbnail import create_thumbnail

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)
STATUS_FILE = "docs/status.json"


def cleanup():
    for f in ["output/voice.mp3", "output/video_final.mp4",
              "output/original.mp4", "output/original.webm"]:
        if os.path.exists(f): os.remove(f)
    os.makedirs("output", exist_ok=True)


def download_video(video_id, output_path="output/original.mp4"):
    """Download YouTube video using yt-dlp."""
    if not video_id:
        log.warning("No video_id — skipping download")
        return None
    try:
        url = f"https://youtube.com/watch?v={video_id}"
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "-f", "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4][height<=720]/best",
            "--merge-output-format", "mp4",
            "-o", output_path,
            "--no-warnings",
            url
        ]
        log.info(f"Downloading video: {url}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and os.path.exists(output_path):
            size = os.path.getsize(output_path)
            log.info(f"Downloaded: {output_path} ({size:,} bytes)")
            return output_path
        else:
            log.error(f"yt-dlp failed: {result.stderr[-200:]}")
            return None
    except Exception as e:
        log.error(f"Download failed: {e}")
        return None


def replace_audio(video_path, audio_path, output_path="output/video_final.mp4"):
    """Replace video audio with Malayalam voiceover using FFmpeg."""
    try:
        # Get video duration
        probe = subprocess.run([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ], capture_output=True, text=True)
        video_duration = float(probe.stdout.strip())

        # Get audio duration
        probe2 = subprocess.run([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ], capture_output=True, text=True)
        audio_duration = float(probe2.stdout.strip())

        log.info(f"Video: {video_duration:.1f}s | Malayalam audio: {audio_duration:.1f}s")

        # If audio is shorter than video — pad with silence
        # If audio is longer than video — trim video or loop it
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",           # Keep original video quality
            "-c:a", "aac",
            "-b:a", "192k",
            "-map", "0:v:0",          # Video from original
            "-map", "1:a:0",          # Audio from Malayalam
            "-shortest",              # End at shorter stream
            "-movflags", "+faststart",
            output_path
        ]
        log.info("Replacing audio with Malayalam voiceover...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            log.error(f"FFmpeg failed: {result.stderr[-300:]}")
            raise RuntimeError("Audio replacement failed")

        size = os.path.getsize(output_path)
        log.info(f"Final video ready: {output_path} ({size:,} bytes)")
        return output_path

    except Exception as e:
        log.error(f"replace_audio failed: {e}")
        raise


def write_status(runs):
    os.makedirs("docs", exist_ok=True)
    existing = []
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE) as f:
                existing = json.load(f).get("history", [])
        except: existing = []
    for run in runs:
        existing.insert(0, {
            "last_run":    datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "status":      run.get("status"),
            "title":       run.get("title", ""),
            "youtube_url": run.get("youtube_url", ""),
            "error":       run.get("error", ""),
        })
    last = runs[-1] if runs else {}
    with open(STATUS_FILE, "w") as f:
        json.dump({
            "last_run":    datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "status":      last.get("status"),
            "title":       last.get("title", ""),
            "youtube_url": last.get("youtube_url", ""),
            "history":     existing[:30],
        }, f, indent=2)


def run_single(title, video_id, num, total):
    result = {"status": "failed", "title": title,
              "youtube_url": "", "error": ""}
    try:
        log.info(f"{'='*60}")
        log.info(f"VIDEO {num}/{total} — {title}")
        log.info(f"Video ID: {video_id}")
        log.info(f"{'='*60}")

        cleanup()

        # STEP 1: Download original video
        log.info("STEP 1 — Downloading original video...")
        video_path = download_video(video_id)
        if not video_path:
            raise RuntimeError("Could not download video — skipping")

        # STEP 2: Translate to Malayalam
        log.info("STEP 2 — Translating to Malayalam...")
        script = generate_malayalam_kids_script(title, video_id)
        log.info(f"Malayalam script: {len(script)} chars")

        # STEP 3: Generate Malayalam voiceover
        log.info("STEP 3 — Generating Malayalam voiceover...")
        audio_path = generate_voiceover(script)
        log.info(f"Audio: {audio_path}")

        # STEP 4: Replace audio in video
        log.info("STEP 4 — Replacing audio with Malayalam voiceover...")
        final_video = replace_audio(video_path, audio_path)

        # STEP 4.5: Create thumbnail from video frame
        log.info("STEP 4.5 — Creating thumbnail from video frame...")
        thumb_path = create_thumbnail(final_video, title, script)
        log.info(f"Thumbnail: {thumb_path}")

        # STEP 5: Upload to YouTube
        log.info("STEP 5 — Uploading to YouTube...")
        url = publish_youtube(final_video, title, script, thumbnail_path=thumb_path)
        result["youtube_url"] = url
        result["status"] = "success"
        log.info(f"Live: {url}")

    except Exception as e:
        result["error"] = str(e)
        result["status"] = "failed"
        log.error(f"Video {num}/{total} failed: {e}")
        log.error(traceback.format_exc())

    return result


def run_pipeline():
    log.info("Malayalam Kids Channel — Daily Pipeline")
    log.info("Fetching trending kids videos...")

    trends = get_top_trends()
    if not trends:
        log.error("No trends found")
        return False

    log.info(f"Today's videos ({len(trends)}):")
    for i, (title, vid_id) in enumerate(trends, 1):
        log.info(f"  {i}. {title[:60]} ({vid_id})")

    results = []
    for i, (title, video_id) in enumerate(trends[:3], 1):
        result = run_single(title, video_id, i, 3)
        results.append(result)
        if i < 3:
            import time
            log.info("Waiting 15s...")
            time.sleep(15)

    write_status(results)

    success = sum(1 for r in results if r["status"] == "success")
    log.info(f"\n{'='*60}")
    log.info(f"COMPLETE: {success}/3 videos posted to Malayalam Kids Channel")
    log.info(f"{'='*60}")
    return success > 0


if __name__ == "__main__":
    exit(0 if run_pipeline() else 1)
