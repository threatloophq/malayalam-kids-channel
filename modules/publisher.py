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
            ["https://www.googleapis.com/auth/youtube.upload"])
        creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as f:
            pickle.dump(creds, f)
    return build("youtube", "v3", credentials=creds)

def publish_youtube(video_path, title, script):
    youtube = get_youtube_client()
    tags = ["malayalam kids", "malayalam cartoon", "kids malayalam",
            "children malayalam", "kerala kids", "malayalam animation",
            "kids stories malayalam", "malayalam nursery rhymes"]
    body = {
        "snippet": {
            "title": f"{title} | Malayalam | കുട്ടികൾക്കായി",
            "description": (
                f"{title}\n\nMalayalam kids content — "
                f"കുട്ടികൾക്കായുള്ള മലയാളം വീഡിയോ\n\n"
                f"#MalayalamKids #KeralaKids #MalayalamCartoon "
                f"#കുട്ടികൾ #മലയാളം"
            ),
            "tags": tags,
            "categoryId": "1",  # Film & Animation
            "defaultLanguage": "ml",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": True,  # Mark as kids content
        },
    }
    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        _, response = request.next_chunk()
    url = f"https://www.youtube.com/watch?v={response['id']}"
    log.info(f"YouTube live: {url}")
    return url
