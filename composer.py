from moviepy import VideoFileClip, CompositeVideoClip, ColorClip
from pathlib import Path


TARGET_W = 1080
TARGET_H = 1920
ASPECT = TARGET_W / TARGET_H  # 9:16


def crop_to_vertical(clip: VideoFileClip) -> VideoFileClip:
    """Crop a horizontal (or any) clip to 9:16 by centre-cropping."""
    src_w, src_h = clip.size

    # Determine crop box that fills 9:16 from the centre
    if src_w / src_h > ASPECT:
        # Wider than 9:16 — crop sides
        new_w = int(src_h * ASPECT)
        x1 = (src_w - new_w) // 2
        cropped = clip.cropped(x1=x1, y1=0, x2=x1 + new_w, y2=src_h)
    else:
        # Taller than 9:16 — crop top/bottom
        new_h = int(src_w / ASPECT)
        y1 = (src_h - new_h) // 2
        cropped = clip.cropped(x1=0, y1=y1, x2=src_w, y2=y1 + new_h)

    return cropped.resized((TARGET_W, TARGET_H))


def make_short(
    input_path: str | Path,
    output_path: str | Path,
    start: float = 0,
    end: float | None = None,
    fps: int = 30,
) -> Path:
    """
    Crop a video to 9:16, optionally trim it, and write a Short-ready MP4.

    Args:
        input_path: Source video file.
        output_path: Destination MP4 path.
        start: Start time in seconds (default 0).
        end: End time in seconds (default: full clip).
        fps: Output frame rate (default 30).

    Returns:
        Path to the written file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with VideoFileClip(str(input_path)) as clip:
        if end is not None:
            clip = clip.subclipped(start, end)
        elif start > 0:
            clip = clip.subclipped(start)

        vertical = crop_to_vertical(clip)

        vertical.write_videofile(
            str(output_path),
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            threads=4,
            logger="bar",
        )

    return output_path


def make_short_with_background(
    input_path: str | Path,
    output_path: str | Path,
    start: float = 0,
    end: float | None = None,
    fps: int = 30,
    bg_color: tuple[int, int, int] = (0, 0, 0),
) -> Path:
    """
    Fit (letterbox/pillarbox) a clip into a 9:16 frame with a solid background,
    preserving the original aspect ratio without cropping content.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with VideoFileClip(str(input_path)) as clip:
        if end is not None:
            clip = clip.subclipped(start, end)
        elif start > 0:
            clip = clip.subclipped(start)

        src_w, src_h = clip.size
        scale = min(TARGET_W / src_w, TARGET_H / src_h)
        fitted = clip.resized(width=int(src_w * scale), height=int(src_h * scale))

        bg = ColorClip(size=(TARGET_W, TARGET_H), color=bg_color, duration=fitted.duration)
        x_offset = (TARGET_W - fitted.w) // 2
        y_offset = (TARGET_H - fitted.h) // 2
        fitted = fitted.with_position((x_offset, y_offset))

        final = CompositeVideoClip([bg, fitted])
        final.write_videofile(
            str(output_path),
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            threads=4,
            logger="bar",
        )

    return output_path


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python composer.py <input_video> <output_video> [start] [end]")
        sys.exit(1)

    inp = sys.argv[1]
    out = sys.argv[2]
    t_start = float(sys.argv[3]) if len(sys.argv) > 3 else 0
    t_end = float(sys.argv[4]) if len(sys.argv) > 4 else None

    result = make_short(inp, out, start=t_start, end=t_end)
    print(f"Written: {result}")
