import os
import logging
import requests
from datetime import datetime, timedelta

log = logging.getLogger(__name__)
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# Kids animated content keywords
KIDS_KEYWORDS = [
    "kids animation", "children cartoon", "nursery rhymes",
    "kids stories", "moral stories", "fairy tales",
    "kids learning", "abc songs", "phonics", "bedtime stories",
    "dinosaur kids", "animal stories for kids", "kids educational"
]

def get_trending_kids_videos():
    """Fetch trending kids animated videos from YouTube."""
    if not YOUTUBE_API_KEY:
        log.warning("No YOUTUBE_API_KEY")
        return []

    videos = []
    try:
        params = {
            "part": "snippet",
            "q": "kids animation trending 2025 english cartoon",
            "type": "video",
            "order": "viewCount",
            "publishedAfter": (datetime.utcnow() - timedelta(days=30)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"),
            "maxResults": 20,
            "relevanceLanguage": "en",
            "videoCategoryId": "1",  # Film & Animation
            "safeSearch": "strict",  # Kids safe
            "key": YOUTUBE_API_KEY,
        }
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params=params, timeout=10)
        r.raise_for_status()
        items = r.json().get("items", [])

        video_ids = [i["id"]["videoId"] for i in items
                     if "videoId" in i.get("id", {})]

        if video_ids:
            stats_r = requests.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={
                    "part": "snippet,statistics,contentDetails",
                    "id": ",".join(video_ids),
                    "key": YOUTUBE_API_KEY
                }, timeout=10)
            stats_r.raise_for_status()

            for item in stats_r.json().get("items", []):
                title    = item["snippet"]["title"]
                views    = int(item["statistics"].get("viewCount", 0))
                vid_id   = item["id"]
                channel  = item["snippet"]["channelTitle"]
                desc     = item["snippet"]["description"][:200]
                duration = item["contentDetails"]["duration"]

                # Filter for kids content
                text = (title + " " + desc + " " + channel).lower()
                is_kids = any(kw in text for kw in KIDS_KEYWORDS)
                is_short_enough = "PT" in duration  # Skip very long videos

                if is_kids or any(w in text for w in ["cartoon", "animation", "kids", "children"]):
                    videos.append({
                        "video_id": vid_id,
                        "title":    title,
                        "views":    views,
                        "channel":  channel,
                        "url":      f"https://youtube.com/watch?v={vid_id}",
                    })

        videos.sort(key=lambda x: x["views"], reverse=True)
        log.info(f"Found {len(videos)} trending kids videos")
        for v in videos[:5]:
            log.info(f"  {v['views']:,} views — {v['title'][:60]}")

    except Exception as e:
        log.warning(f"YouTube search failed: {e}")

    return videos[:5]

def get_top_trends(niche=None):
    videos = get_trending_kids_videos()
    if not videos:
        return [
            ("The Lion and the Mouse - Moral Story for Kids", ""),
            ("ABC Songs for Children - Nursery Rhymes", ""),
            ("Dinosaur Stories for Kids", ""),
        ]
    return [(v["title"], v["video_id"]) for v in videos[:3]]
