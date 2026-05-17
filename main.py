import os
import json
import shutil
import logging
import traceback
from datetime import datetime
from dotenv import load_dotenv

from modules.trends import get_top_trends
from modules.translator import generate_malayalam_kids_script
from modules.voiceover import generate_voiceover
from modules.visuals import get_visuals
from modules.video_builder import build_video
from modules.publisher import publish_youtube

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)
STATUS_FILE = "docs/status.json"

def cleanup():
    for f in ["output/voice.mp3", "output/video_final.mp4"]:
        if os.path.exists(f): os.remove(f)
    for d in ["output/images", "output/slides"]:
        if os.path.exists(d): shutil.rmtree(d)
        os.makedirs(d)

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
        log.info(f"{'='*60}")
        cleanup()

        log.info("STEP 1 — Generating Malayalam script...")
        script = generate_malayalam_kids_script(title, video_id)
        log.info(f"Script: {len(script)} chars")

        log.info("STEP 2 — Generating Malayalam voiceover...")
        audio = generate_voiceover(script)

        log.info("STEP 3 — Fetching kid-friendly visuals...")
        images = get_visuals(script, title)

        log.info("STEP 4 — Building video...")
        video = build_video(audio, images, title, script=script)

        log.info("STEP 5 — Uploading to YouTube...")
        url = publish_youtube(video, title, script)
        result["youtube_url"] = url
        result["status"] = "success"
        log.info(f"Live: {url}")

    except Exception as e:
        result["error"] = str(e)
        log.error(f"Failed: {e}")
        log.error(traceback.format_exc())
    return result

def run_pipeline():
    log.info("Malayalam Kids Channel — Daily Pipeline")
    trends = get_top_trends()
    log.info(f"Today's videos: {[t[0][:40] for t in trends]}")

    results = []
    for i, (title, video_id) in enumerate(trends[:3], 1):
        result = run_single(title, video_id, i, 3)
        results.append(result)
        if i < 3:
            import time
            time.sleep(15)

    write_status(results)
    success = sum(1 for r in results if r["status"] == "success")
    log.info(f"COMPLETE: {success}/3 videos posted")
    return success > 0

if __name__ == "__main__":
    exit(0 if run_pipeline() else 1)
