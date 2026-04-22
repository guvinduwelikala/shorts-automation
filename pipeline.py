"""
Full pipeline:
  1. Generate script (OpenAI GPT-4o)
  2. Generate voiceover (OpenAI TTS)
  3. Add voice + centered subtitles to Output.mp4
  4. Save final Short-ready video
"""
from pathlib import Path
from script_generator import generate_script
from voiceover import generate_voiceover
from captioner import add_subtitles_and_audio

BASE_DIR = Path(__file__).parent
VIDEO_IN = BASE_DIR / "output" / "Output.mp4"
AUDIO_OUT = BASE_DIR / "output" / "voiceover.mp3"
FINAL_OUT = BASE_DIR / "output" / "Final_Short.mp4"


def run_pipeline(topic: str = "money habit most people ignore") -> Path:
    print("=" * 50)
    print(f"TOPIC: {topic}")
    print("=" * 50)

    # Step 1 — Script
    print("\n[1/3] Generating script...")
    try:
        script = generate_script(topic)
    except Exception as e:
        print(f"  Gemini unavailable ({e.__class__.__name__}), using fallback script.\n")
        script = (
            "Most people will never be rich. Not because they don't work hard. "
            "But because they ignore this one money habit. "
            "They spend first, then save what's left. "
            "Wealthy people do the opposite. They save first, then spend what's left. "
            "It's called paying yourself first. "
            "Set up an automatic transfer the moment your paycheck hits. "
            "Even ten percent changes everything over time. "
            "Stop waiting to have money left over. There never will be. "
            "Start today. Follow for more money tips."
        )
    print(f"\nScript:\n{script}\n")

    # Step 2 — Voiceover
    print("[2/3] Generating voiceover...")
    _, word_timings = generate_voiceover(script, AUDIO_OUT)

    # Step 3 — Subtitles + audio on video
    print("\n[3/3] Adding voice and subtitles to video...")
    add_subtitles_and_audio(VIDEO_IN, AUDIO_OUT, script, FINAL_OUT, word_timings=word_timings)

    print(f"\n✓ Final Short ready: {FINAL_OUT}")
    return FINAL_OUT


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default="money habit most people ignore")
    args = parser.parse_args()

    run_pipeline(topic=args.topic)
