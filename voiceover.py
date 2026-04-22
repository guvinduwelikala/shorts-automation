import asyncio
from pathlib import Path
import edge_tts

# en-US-ChristopherNeural: deep, authoritative male — great for finance content
VOICE = "en-US-ChristopherNeural"
OUTPUT_AUDIO = Path(__file__).parent / "output" / "voiceover.mp3"
OUTPUT_WORDS = Path(__file__).parent / "output" / "word_timings.json"


async def _generate(script: str, audio_path: Path, words_path: Path) -> list[dict]:
    communicate = edge_tts.Communicate(script, VOICE, boundary="WordBoundary")
    word_timings = []

    audio_path.parent.mkdir(parents=True, exist_ok=True)
    with open(audio_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word_timings.append({
                    "word": chunk["text"],
                    "start": chunk["offset"] / 10_000_000,   # ticks → seconds
                    "duration": chunk["duration"] / 10_000_000,
                })

    import json
    with open(words_path, "w") as f:
        json.dump(word_timings, f, indent=2)

    return word_timings


def generate_voiceover(
    script: str,
    audio_path: Path = OUTPUT_AUDIO,
    words_path: Path = OUTPUT_WORDS,
) -> tuple[Path, list[dict]]:
    print(f"Generating voiceover ({VOICE})...")
    word_timings = asyncio.run(_generate(script, audio_path, words_path))
    print(f"Voiceover saved: {audio_path}  ({len(word_timings)} words timed)")
    return audio_path, word_timings


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True)
    args = parser.parse_args()
    generate_voiceover(args.script)
