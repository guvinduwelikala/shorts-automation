import os
import requests
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"
RAW_CLIPS_DIR = Path(__file__).parent / "raw_clips"


def search_videos(query: str, count: int = 5) -> list[dict]:
    if not PEXELS_API_KEY:
        raise ValueError("PEXELS_API_KEY not found in .env file")

    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": query,
        "orientation": "portrait",
        "per_page": count,
        "page": 1,
    }

    response = requests.get(PEXELS_SEARCH_URL, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()

    videos = data.get("videos", [])
    if not videos:
        raise RuntimeError(f"No portrait videos found for query: '{query}'")

    return videos


def pick_best_file(video: dict) -> str | None:
    """Return the HD or highest-quality .mp4 link from a Pexels video entry."""
    files = video.get("video_files", [])
    # Prefer hd, then sd, then whatever is available
    for quality in ("hd", "sd", "uhd"):
        for f in files:
            if f.get("quality") == quality and f.get("file_type") == "video/mp4":
                return f["link"]
    # Fallback: first mp4 found
    for f in files:
        if f.get("file_type") == "video/mp4":
            return f["link"]
    return None


def download_video(url: str, dest: Path, max_retries: int = 3) -> None:
    for attempt in range(max_retries):
        try:
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                downloaded = 0
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 64):
                        if chunk:  # filter out keep-alive new chunks
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total:
                                pct = downloaded / total * 100
                                print(f"\r  {dest.name}: {pct:.1f}%", end="", flush=True)
            print()
            return  # Success, exit the function
        except requests.exceptions.RequestException as e:
            print(f"\n  [!] Download error: {e}")
            if attempt < max_retries - 1:
                print(f"  Retrying ({attempt + 1}/{max_retries}) in 3 seconds...")
                time.sleep(3)
            else:
                print("  Max retries reached. Failing download.")
                raise


def download_clips(query: str = "cinematic nature", count: int = 5) -> list[Path]:
    RAW_CLIPS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Searching Pexels for '{query}' (portrait, {count} videos)...")
    videos = search_videos(query, count)
    print(f"Found {len(videos)} video(s). Downloading...\n")

    saved = []
    for i, video in enumerate(videos, start=1):
        url = pick_best_file(video)
        if not url:
            print(f"  clip{i}: no suitable .mp4 found, skipping.")
            continue

        dest = RAW_CLIPS_DIR / f"clip{i}.mp4"
        print(f"  Downloading clip{i}.mp4  (Pexels ID: {video['id']})")
        try:
            download_video(url, dest)
            saved.append(dest)
        except Exception as e:
            print(f"  Skipping clip{i} due to final download failure.")

    print(f"\nDone. {len(saved)} clip(s) saved to '{RAW_CLIPS_DIR}'.")
    return saved


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default="cinematic nature")
    parser.add_argument("--count", type=int, default=5)
    args = parser.parse_args()
    download_clips(query=args.query, count=args.count)
