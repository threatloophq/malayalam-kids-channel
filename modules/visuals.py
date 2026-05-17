import os
import re
import time
import logging
import requests
from PIL import Image
from io import BytesIO

log = logging.getLogger(__name__)
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
OUTPUT_DIR = "output/images"

KIDS_QUERIES = [
    "colorful cartoon animals", "kids playing outdoor",
    "children learning classroom", "fairy tale forest",
    "cute animals nature", "colorful flowers garden",
    "children happy smiling", "cartoon jungle animals",
    "kids reading books", "playground children fun",
]

def get_visuals(script, topic):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for f in os.listdir(OUTPUT_DIR):
        if f.endswith((".jpg", ".png")):
            os.remove(os.path.join(OUTPUT_DIR, f))

    # Extract visual cues from script
    cues = re.findall(r'\[VISUAL CUE:\s*(.+?)\]', script, re.IGNORECASE)
    if not cues:
        cues = KIDS_QUERIES[:8]

    # Pad to 8
    while len(cues) < 8:
        cues.append(KIDS_QUERIES[len(cues) % len(KIDS_QUERIES)])
    cues = cues[:8]

    paths = []
    used_ids = set()
    for i, cue in enumerate(cues):
        path = f"{OUTPUT_DIR}/img_{i:02d}.jpg"
        img = (fetch_pexels(cue, used_ids) or
               fetch_pexels("kids " + cue.split()[0], used_ids) or
               fetch_picsum(i))
        if img:
            img.convert("RGB").resize((1080,1920), Image.LANCZOS).save(
                path, "JPEG", quality=92)
            paths.append(path)
        time.sleep(0.3)

    log.info(f"Images: {len(paths)}")
    return paths

def fetch_pexels(query, used_ids):
    if not PEXELS_API_KEY: return None
    try:
        for page in range(1, 3):
            r = requests.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={"query": query, "per_page": 5,
                        "page": page, "orientation": "portrait"},
                timeout=10)
            r.raise_for_status()
            for photo in r.json().get("photos", []):
                if photo["id"] not in used_ids:
                    used_ids.add(photo["id"])
                    return Image.open(BytesIO(
                        requests.get(photo["src"]["large"], timeout=15).content))
    except Exception as e:
        log.warning(f"Pexels failed '{query}': {e}")
    return None

def fetch_picsum(seed=0):
    try:
        r = requests.get(f"https://picsum.photos/seed/{seed*53+500}/1080/1920",
                         timeout=15)
        if r.status_code == 200:
            return Image.open(BytesIO(r.content))
    except: pass
    return None
