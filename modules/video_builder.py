import os
import re
import subprocess
import logging
import shutil
from PIL import Image, ImageDraw, ImageFont

log = logging.getLogger(__name__)

def build_video(audio_path, image_paths, title,
                script="", output_path="output/video_final.mp4"):
    os.makedirs("output/slides", exist_ok=True)
    for f in os.listdir("output/slides"):
        os.remove(f"output/slides/{f}")

    if not image_paths:
        raise RuntimeError("No images provided")
    if len(image_paths) < 3:
        image_paths = (image_paths * 8)[:8]

    duration  = get_audio_duration(audio_path)
    n         = len(image_paths)
    per_image = round(duration / n, 3)
    log.info(f"Audio: {duration:.1f}s | {n} images | {per_image:.1f}s each")

    for i, img_path in enumerate(image_paths):
        out = f"output/slides/img{i:04d}.png"
        img = Image.open(img_path).convert("RGB").resize((1080, 1920), Image.LANCZOS)

        # Colorful gradient overlay for kids
        overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        ov = ImageDraw.Draw(overlay)
        # Bottom gradient for text
        for y in range(1500, 1920):
            alpha = int(200 * (y - 1500) / 420)
            ov.rectangle([0, y, 1080, y+1], fill=(0, 0, 50, alpha))
        # Top gradient for title
        for y in range(0, 200):
            alpha = int(180 * (1 - y / 200))
            ov.rectangle([0, y, 1080, y+1], fill=(50, 0, 80, alpha))

        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

        # Load fonts
        try:
            font_title = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 56)
            font_sub   = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 38)
        except:
            try:
                font_title = ImageFont.truetype(
                    "/System/Library/Fonts/Helvetica.ttc", 56)
                font_sub   = ImageFont.truetype(
                    "/System/Library/Fonts/Helvetica.ttc", 38)
            except:
                font_title = font_sub = ImageFont.load_default()

        # Channel name at top
        draw_centered(draw, "🌟 Malayalam Kids", 540, 80,
                      font_sub, (255, 220, 50))

        # Video title at top
        draw_wrapped(draw, title[:50], 540, 150,
                     font_title, (255, 255, 255), max_width=960)

        # Malayalam subtitle at bottom
        malayalam_lines = extract_current_line(script, i, n)
        if malayalam_lines:
            draw_wrapped(draw, malayalam_lines, 540, 1780,
                         font_sub, (255, 255, 150), max_width=960)

        # Progress bar — colorful for kids
        bar_w = int((i + 1) / n * 1080)
        colors = [(255,100,100), (255,165,0), (255,255,0),
                  (100,255,100), (100,100,255), (200,100,255)]
        color = colors[i % len(colors)]
        draw.rectangle([0, 1900, 1080, 1920], fill=(40, 40, 40))
        draw.rectangle([0, 1900, bar_w, 1920], fill=color)

        img.save(out, "PNG")

    log.info(f"Built {n} slides")

    cmd = [
        "ffmpeg", "-y",
        "-framerate", f"1/{int(per_image)}",
        "-i", "output/slides/img%04d.png",
        "-i", audio_path,
        "-c:v", "libx264", "-preset", "fast",
        "-b:v", "6M", "-maxrate", "6M", "-bufsize", "12M",
        "-vf", "fps=30,format=yuv420p,scale=1080:1920",
        "-profile:v", "high", "-level", "4.2",
        "-r", "30", "-g", "30",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-map", "0:v", "-map", "1:a",
        "-shortest", "-movflags", "+faststart",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {result.stderr[-300:]}")

    log.info(f"Video ready: {output_path} ({os.path.getsize(output_path):,} bytes)")
    shutil.rmtree("output/slides", ignore_errors=True)
    return output_path

def extract_current_line(script, slide_idx, total_slides):
    """Extract relevant script line for current slide."""
    if not script:
        return ""
    lines = [l.strip() for l in script.splitlines() if l.strip()
             and not l.strip().startswith("[")]
    if not lines:
        return ""
    idx = int(slide_idx / total_slides * len(lines))
    return lines[min(idx, len(lines)-1)][:80]

def draw_centered(draw, text, x, y, font, color):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    draw.text((x-tw//2+2, y-th//2+2), text, font=font, fill=(0,0,0))
    draw.text((x-tw//2,   y-th//2),   text, font=font, fill=color)

def draw_wrapped(draw, text, x, y, font, color, max_width=960):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        if draw.textbbox((0,0), test, font=font)[2] <= max_width:
            current = test
        else:
            if current: lines.append(current)
            current = word
    if current: lines.append(current)
    lh = 65
    sy = y - (len(lines)*lh)//2
    for i, line in enumerate(lines):
        draw_centered(draw, line, x, sy+i*lh, font, color)

def get_audio_duration(audio_path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        capture_output=True, text=True, check=True)
    return float(result.stdout.strip())
