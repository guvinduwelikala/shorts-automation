from pathlib import Path
from moviepy import VideoFileClip, concatenate_videoclips
from composer import make_short

RAW_CLIPS_DIR = Path(__file__).parent / "raw_clips"
OUTPUT_DIR = Path(__file__).parent / "output"


def batch_compose(fps: int = 30) -> None:
    clips = sorted(RAW_CLIPS_DIR.glob("*.mp4"))
    if not clips:
        print(f"No .mp4 files found in '{RAW_CLIPS_DIR}'.")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Found {len(clips)} clip(s). Processing...\n")

    processed = []
    for i, clip_path in enumerate(clips, start=1):
        out_path = OUTPUT_DIR / clip_path.name
        print(f"[{i}/{len(clips)}] {clip_path.name} -> output/{clip_path.name}")
        try:
            make_short(clip_path, out_path, fps=fps)
            print(f"  Done: {out_path}\n")
            processed.append(out_path)
        except Exception as e:
            print(f"  ERROR processing {clip_path.name}: {e}\n")

    if len(processed) < 2:
        print("Not enough clips to assemble. Skipping merge.")
        return

    final_path = OUTPUT_DIR / "Output.mp4"
    print(f"Assembling {len(processed)} clip(s) into Output.mp4...")

    video_clips = [VideoFileClip(str(p)) for p in processed]
    final = concatenate_videoclips(video_clips, method="compose")
    final.write_videofile(
        str(final_path),
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        logger="bar",
    )
    for vc in video_clips:
        vc.close()
    final.close()

    print(f"\nDone. Final video saved to '{final_path}'.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args()
    batch_compose(fps=args.fps)
