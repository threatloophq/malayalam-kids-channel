import os
import pickle
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

log = logging.getLogger(__name__)

def get_youtube_client():
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as f:
            creds = pickle.load(f)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open("token.pickle", "wb") as f:
            pickle.dump(creds, f)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            "client_secrets.json",
            ["https://www.googleapis.com/auth/youtube.upload",
             "https://www.googleapis.com/auth/youtube"])
        creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as f:
            pickle.dump(creds, f)
    return build("youtube", "v3", credentials=creds)

def publish_youtube(video_path, title, script, thumbnail_path=None):
    youtube = get_youtube_client()

    tags = [
        "malayalam kids", "malayalam cartoon", "kids malayalam",
        "children malayalam", "kerala kids", "malayalam animation",
        "kids stories malayalam", "malayalam nursery rhymes",
        "മലയാളം കുട്ടികൾ", "കുട്ടികളുടെ വീഡിയോ",
    ]

    malayalam_title = f"{title[:60]} | മലയാളം | Malayalam Kids"

    body = {
        "snippet": {
            "title": malayalam_title,
            "description": (
                f"{title}\n\n"
                f"മലയാളത്തിൽ കുട്ടികൾക്കായുള്ള വീഡിയോ 🌟\n\n"
                f"Malayalam dubbed kids video for children in Kerala.\n\n"
                f"#MalayalamKids #KeralaKids #MalayalamCartoon "
                f"#കുട്ടികൾ #മലയാളം #MalayalamDubbed"
            ),
            "tags": tags,
            "categoryId": "1",
            "defaultLanguage": "ml",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": True,
        },
    }

    log.info(f"Uploading: {malayalam_title}")
    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True,
                            chunksize=5*1024*1024)
    request = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            log.info(f"Upload: {int(status.progress()*100)}%")

    video_id = response["id"]
    url = f"https://www.youtube.com/watch?v={video_id}"
    log.info(f"YouTube live: {url}")

    # Upload custom thumbnail
    if thumbnail_path and os.path.exists(thumbnail_path):
        try:
            log.info("Uploading thumbnail...")
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
            ).execute()
            log.info("Thumbnail uploaded!")
        except Exception as e:
            log.warning(f"Thumbnail upload failed: {e}")

    return url
