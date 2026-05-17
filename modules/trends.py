import os
import logging
import requests
from datetime import datetime, timedelta

log = logging.getLogger(__name__)
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

KIDS_SEARCH_QUERIES = [
    "kids cartoon english 2025",
    "nursery rhymes children songs",
    "moral stories kids english",
    "children educational animation",
    "kids learning videos english",
]

EXCLUDE_KEYWORDS = [
    "horror", "scary", "violence", "adult", "18+",
    "murder", "crime", "war", "drugs",
]

def search_youtube_kids(query, max_results=10):
    """Search YouTube for kids videos and return with video IDs."""
    if not YOUTUBE_API_KEY:
        log.warning("No YOUTUBE_API_KEY set")
        return []

    try:
        # Step 1: Search
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "order": "viewCount",
            "publishedAfter": (datetime.utcnow() - timedelta(days=30)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"),
            "maxResults": max_results,
            "relevanceLanguage": "en",
            "safeSearch": "strict",
            "key": YOUTUBE_API_KEY,
        }
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params=params, timeout=10)
        r.raise_for_status()
        items = r.json().get("items", [])
        log.info(f"Search '{query}': {len(items)} results")

        if not items:
            return []

        # Step 2: Get video IDs and stats
        video_ids = []
        for item in items:
            vid_id = item.get("id", {}).get("videoId", "")
            if vid_id:
                video_ids.append(vid_id)

        if not video_ids:
            log.warning(f"No video IDs found for '{query}'")
            return []

        log.info(f"Video IDs found: {video_ids[:3]}")

        # Step 3: Get full details
        stats_r = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part": "snippet,statistics,contentDetails",
                "id": ",".join(video_ids),
                "key": YOUTUBE_API_KEY,
            }, timeout=10)
        stats_r.raise_for_status()

        videos = []
        for item in stats_r.json().get("items", []):
            vid_id  = item["id"]
            title   = item["snippet"]["title"]
            views   = int(item["statistics"].get("viewCount", 0))
            channel = item["snippet"]["channelTitle"]

            # Skip excluded content
            text = title.lower()
            if any(ex in text for ex in EXCLUDE_KEYWORDS):
                continue

            videos.append({
                "video_id": vid_id,
                "title":    title,
                "views":    views,
                "channel":  channel,
                "url":      f"https://youtube.com/watch?v={vid_id}",
            })
            log.info(f"  ✅ {vid_id} | {views:,} views | {title[:50]}")

        return videos

    except Exception as e:
        log.error(f"YouTube search failed for '{query}': {e}")
        return []

def get_top_trends(niche=None):
    """Return top 3 trending kids videos with valid video IDs."""
    all_videos = []
    seen_ids = set()

    for query in KIDS_SEARCH_QUERIES[:3]:
        videos = search_youtube_kids(query)
        for v in videos:
            if v["video_id"] not in seen_ids:
                seen_ids.add(v["video_id"])
                all_videos.append(v)

    if not all_videos:
        log.warning("No videos found from YouTube API")
        # Return hardcoded popular kids video IDs as fallback
        return [
            ("Baby Shark Dance - Kids Song", "XqZsoesa55w"),
            ("Wheels on the Bus - Nursery Rhymes", "e_04ZrNroTo"),
            ("Five Little Ducks - Kids Song", "IO-tUpkygaI"),
        ]

    # Sort by views
    all_videos.sort(key=lambda x: x["views"], reverse=True)

    log.info(f"\nTop {min(3, len(all_videos))} trending kids videos:")
    for v in all_videos[:3]:
        log.info(f"  📺 {v['video_id']} | {v['views']:,} views | {v['title'][:50]}")

    return [(v["title"], v["video_id"]) for v in all_videos[:3]]
