"""
Full automated YouTube Shorts pipeline — one command, one topic.

Usage:
  python run.py --topic "why 99% of people stay broke"
  python run.py --topic "morning habits of millionaires" --privacy unlisted
"""
import argparse
from pathlib import Path

from script_generator import generate_script, generate_pexels_query, _keyword_fallback
from downloader import download_clips
from batch_compose import batch_compose
from voiceover import generate_voiceover
from captioner import add_subtitles_and_audio
from uploader import upload_short

BASE_DIR = Path(__file__).parent
VIDEO_IN  = BASE_DIR / "output" / "Output.mp4"
AUDIO_OUT = BASE_DIR / "output" / "voiceover.mp3"
FINAL_OUT = BASE_DIR / "output" / "Final_Short.mp4"


def banner(step: int, total: int, label: str) -> None:
    print(f"\n{'='*54}")
    print(f"  STEP {step}/{total}: {label}")
    print(f"{'='*54}")


def run(topic: str, privacy: str) -> None:
    print(f"\n{'='*54}")
    print(f"  TOPIC : {topic}")
    print(f"{'='*54}")

    # ── Step 1: Derive Pexels query from topic ──────────
    banner(1, 5, "Generating visual search query")
    try:
        query = generate_pexels_query(topic)
        print(f"  Gemini query: '{query}'")
    except Exception as e:
        query = _keyword_fallback(topic)
        print(f"  Gemini unavailable — keyword fallback: '{query}'")

    # ── Step 2: Download related clips ─────────────────
    banner(2, 5, f"Downloading clips from Pexels <- '{query}'")
    import random
    download_clips(query=query, count=random.randint(7, 10))

    # ── Step 3: Crop to 9:16 + assemble ────────────────
    banner(3, 5, "Cropping to 9:16 & assembling Output.mp4")
    batch_compose(fps=30)

    # ── Step 4: Script → Voiceover → Subtitles ─────────
    banner(4, 5, f"Generating script <- '{topic}'")
    try:
        script = generate_script(topic)
        print(f"\nScript (Gemini):\n{script}\n")
    except Exception as e:
        print(f"  Gemini unavailable ({e.__class__.__name__}) — writing script from topic keywords.")
        script = _build_fallback_script(topic)
        print(f"\nScript (fallback):\n{script}\n")

    print("Generating voiceover...")
    _, word_timings = generate_voiceover(script, AUDIO_OUT)

    print("\nAdding voice + subtitles...")
    add_subtitles_and_audio(VIDEO_IN, AUDIO_OUT, script, FINAL_OUT, word_timings=word_timings)

    # ── Step 5: Upload to YouTube ───────────────────────
    banner(5, 5, "Uploading to YouTube")
    yt_title = f"{topic.title()} #Shorts"
    yt_desc  = f"{script}\n\n#Shorts #MoneyTips #Finance #Motivation"

    video_id = upload_short(
        video_path=FINAL_OUT,
        title=yt_title,
        description=yt_desc,
        privacy=privacy,
    )

    print(f"\n{'='*54}")
    print(f"  DONE!")
    print(f"  YouTube URL : https://www.youtube.com/shorts/{video_id}")
    print(f"{'='*54}\n")


def _build_fallback_script(topic: str) -> str:
    return (
        f"Most people never think about {topic}. "
        "But the ones who do? They change their lives. "
        "The secret isn't working harder. "
        "It's working smarter with what you already have. "
        "Small decisions made every day compound into massive results over time. "
        "Start with one habit. One shift. One decision. "
        "That's all it takes to get ahead of 99% of people. "
        "Follow for more tips that actually change your life."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated YouTube Shorts pipeline")
    parser.add_argument("--topic", help='e.g. "why 99%% of people stay broke"')
    parser.add_argument("--privacy", default="public", choices=["public", "private", "unlisted"])
    parser.add_argument("--ui", action="store_true", help="Launch desktop UI mode")
    args = parser.parse_args()

    if args.ui:
        from ui import main as ui_main

        ui_main()
    else:
        if not args.topic:
            parser.error("--topic is required unless --ui is provided")
        run(topic=args.topic, privacy=args.privacy)
