import os
import re
import subprocess
import logging
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from io import BytesIO

log = logging.getLogger(__name__)
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

def create_thumbnail(video_path, title, script="", output_path="output/thumbnail.jpg"):
    """
    Create a YouTube thumbnail by:
    1. Extracting the best frame from the actual video
    2. Enhancing it (brightness, contrast, saturation)
    3. Adding Malayalam title text overlay
    4. Adding ThreatLoopHQ branding
    """
    os.makedirs("output", exist_ok=True)

    # Step 1: Extract best frame from video (at 10% duration — usually good scene)
    frame_path = extract_best_frame(video_path)

    if not frame_path:
        log.warning("Could not extract frame — using Pexels fallback")
        frame_path = fetch_relevant_image(title)

    if not frame_path:
        log.warning("No image found — creating solid background")
        img = Image.new("RGB", (1280, 720), (30, 30, 80))
    else:
        img = Image.open(frame_path).convert("RGB")

    # Step 2: Resize to YouTube thumbnail size (1280x720)
    img = img.resize((1280, 720), Image.LANCZOS)

    # Step 3: Enhance image — make it pop
    img = ImageEnhance.Brightness(img).enhance(1.1)
    img = ImageEnhance.Contrast(img).enhance(1.3)
    img = ImageEnhance.Color(img).enhance(1.4)  # More vibrant colors

    # Step 4: Add gradient overlays for text readability
    overlay = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)

    # Bottom gradient for title text
    for y in range(400, 720):
        alpha = int(200 * (y - 400) / 320)
        draw_overlay.rectangle([0, y, 1280, y+1], fill=(0, 0, 0, alpha))

    # Top gradient for channel name
    for y in range(0, 120):
        alpha = int(160 * (1 - y / 120))
        draw_overlay.rectangle([0, y, 1280, y+1], fill=(0, 0, 0, alpha))

    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Step 5: Load fonts
    try:
        font_title   = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 72)
        font_channel = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
        font_badge   = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 42)
    except:
        try:
            font_title   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
            font_channel = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
            font_badge   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
        except:
            font_title = font_channel = font_badge = ImageFont.load_default()

    # Step 6: Clean title for display
    clean_title = clean_malayalam_title(title, script)

    # Step 7: Draw channel name at top
    draw_text_shadow(draw, "🌟 Malayalam Kids | മലയാളം", 30, 30,
                     font_channel, (255, 220, 50))

    # Step 8: Draw Malayalam title at bottom — wrapped
    draw_wrapped_shadow(draw, clean_title, 640, 580,
                        font_title, (255, 255, 255), max_width=1200)

    # Step 9: Add MALAYALAM badge
    badge_w, badge_h = 220, 60
    draw.rectangle([30, 620, 30+badge_w, 620+badge_h],
                   fill=(220, 30, 30))
    draw_text_shadow(draw, "മലയാളം DUBBED", 30 + badge_w//2,
                     620 + badge_h//2, font_badge, (255, 255, 255))

    # Step 10: Add kids emoji decoration
    emojis_text = "⭐ കുട്ടികൾക്കായി ⭐"
    draw_text_shadow(draw, emojis_text, 640, 670,
                     font_channel, (255, 220, 50))

    # Save thumbnail
    img.save(output_path, "JPEG", quality=95)
    size = os.path.getsize(output_path)
    log.info(f"Thumbnail created: {output_path} ({size:,} bytes)")

    # Cleanup temp frame
    if frame_path and frame_path != output_path and os.path.exists(frame_path):
        try: os.remove(frame_path)
        except: pass

    return output_path


def extract_best_frame(video_path):
    """Extract a good frame from the video at multiple timestamps and pick best."""
    if not video_path or not os.path.exists(video_path):
        return None

    try:
        # Get video duration
        probe = subprocess.run([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ], capture_output=True, text=True)
        duration = float(probe.stdout.strip())

        # Try multiple timestamps — 10%, 25%, 40% of video
        best_frame = None
        best_size = 0

        for pct in [0.10, 0.25, 0.40]:
            timestamp = duration * pct
            frame_path = f"output/frame_{int(pct*100)}.jpg"

            result = subprocess.run([
                "ffmpeg", "-y",
                "-ss", str(timestamp),
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "2",
                "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
                frame_path
            ], capture_output=True, text=True)

            if result.returncode == 0 and os.path.exists(frame_path):
                size = os.path.getsize(frame_path)
                if size > best_size:
                    best_size = size
                    best_frame = frame_path

        if best_frame:
            log.info(f"Best frame extracted: {best_frame} ({best_size:,} bytes)")
            return best_frame

    except Exception as e:
        log.warning(f"Frame extraction failed: {e}")

    return None


def fetch_relevant_image(title):
    """Fetch a relevant image from Pexels as fallback."""
    if not PEXELS_API_KEY:
        return None
    try:
        # Extract key words from title for search
        keywords = extract_search_keywords(title)
        query = f"kids {keywords}"
        log.info(f"Fetching Pexels image for: '{query}'")

        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "per_page": 3,
                    "orientation": "landscape"},
            timeout=10)
        r.raise_for_status()
        photos = r.json().get("photos", [])
        if photos:
            img_data = requests.get(
                photos[0]["src"]["large2x"], timeout=15).content
            img = Image.open(BytesIO(img_data))
            path = "output/thumbnail_bg.jpg"
            img.save(path)
            return path
    except Exception as e:
        log.warning(f"Pexels fallback failed: {e}")
    return None


def clean_malayalam_title(title, script=""):
    """Extract or generate a short Malayalam title for thumbnail."""
    # Try to get first line of Malayalam script
    if script:
        lines = [l.strip() for l in script.splitlines()
                 if l.strip() and not l.startswith("[")]
        if lines:
            first_line = lines[0][:60]
            # Check if it contains Malayalam characters
            if any('\u0d00' <= c <= '\u0d7f' for c in first_line):
                return first_line

    # Fallback: use original title with Malayalam suffix
    clean = title[:50]
    return f"{clean} | മലയാളം"


def extract_search_keywords(title):
    """Extract 2-3 key words from title for image search."""
    stop_words = {"the", "a", "an", "and", "or", "for", "in", "on",
                  "at", "to", "of", "with", "is", "are", "was", "were",
                  "kids", "children", "child", "video", "youtube", "2025"}
    words = re.findall(r'\b[a-zA-Z]{3,}\b', title.lower())
    keywords = [w for w in words if w not in stop_words][:3]
    return " ".join(keywords) if keywords else "children playing"


def draw_text_shadow(draw, text, x, y, font, color,
                     shadow_color=(0, 0, 0), offset=3):
    """Draw text with drop shadow, centered."""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    tx, ty = x - tw//2, y - th//2
    # Shadow
    draw.text((tx+offset, ty+offset), text, font=font, fill=shadow_color)
    # Main text
    draw.text((tx, ty), text, font=font, fill=color)


def draw_wrapped_shadow(draw, text, x, y, font, color, max_width=1200):
    """Draw wrapped text with shadow, centered."""
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current: lines.append(current)
            current = word
    if current: lines.append(current)

    lh = 80
    total_h = len(lines) * lh
    start_y = y - total_h // 2

    for i, line in enumerate(lines):
        draw_text_shadow(draw, line, x, start_y + i * lh, font, color)
