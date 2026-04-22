import os
import pickle
from pathlib import Path
from dotenv import load_dotenv

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRETS = Path(__file__).parent / "client_secrets.json"
TOKEN_FILE = Path(__file__).parent / "token.pickle"
OUTPUT_FILE = Path(__file__).parent / "output" / "Final_Short.mp4"


def get_authenticated_service():
    creds = None

    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)

    return build("youtube", "v3", credentials=creds)


def upload_short(
    video_path: Path,
    title: str = "Cyberpunk City 🌆 #Shorts",
    description: str = "Cinematic Cyberpunk City vibes.\n\n#Shorts #Cyberpunk #CinematicVideo",
    tags: list[str] | None = None,
    category_id: str = "22",  # 22 = People & Blogs, 1 = Film & Animation
    privacy: str = "public",
) -> str:
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    if tags is None:
        tags = ["Shorts", "Cyberpunk", "CinematicVideo", "YouTubeShorts"]

    print("Authenticating with YouTube...")
    youtube = get_authenticated_service()

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True)

    print(f"Uploading '{video_path.name}' to YouTube as a Short...")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"\r  Upload progress: {pct}%", end="", flush=True)

    print()
    video_id = response["id"]
    print(f"\nUpload complete!")
    print(f"  Video ID : {video_id}")
    print(f"  URL      : https://www.youtube.com/shorts/{video_id}")
    return video_id


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--video", default=str(OUTPUT_FILE))
    parser.add_argument("--title", default="Cyberpunk City 🌆 #Shorts")
    parser.add_argument("--description", default="Cinematic Cyberpunk City vibes.\n\n#Shorts #Cyberpunk #CinematicVideo")
    parser.add_argument("--privacy", default="public", choices=["public", "private", "unlisted"])
    args = parser.parse_args()

    upload_short(
        video_path=Path(args.video),
        title=args.title,
        description=args.description,
        privacy=args.privacy,
    )
