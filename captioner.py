"""
Shorts-style subtitle renderer.

Layout: 3 words shown at a time on one line.
        The currently spoken word is bright yellow.
        Flanking words are white.
        All words have a thick black stroke for readability on any background.
        A semi-transparent pill sits behind the group for extra contrast.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip
from moviepy import vfx

# ── Typography ─────────────────────────────────────────────────────────────
FONT_SIZE    = 92
WORD_GAP     = 20          # px between words on the same line
STROKE_W     = 7           # px — thick stroke removes need for heavy background
ACTIVE_COL   = (255, 224, 0,   255)   # bright yellow  — spoken word
PASSIVE_COL  = (255, 255, 255, 255)   # white          — flanking words
STROKE_COL   = (0,   0,   0,   255)
SHADOW_COL   = (0,   0,   0,   140)
SHADOW_OFF   = (3, 4)

# ── Pill behind the 3-word group ───────────────────────────────────────────
FADE_DURATION = 0.06   # seconds — crossfade between word groups

# ── Position — lower-third sweet spot ─────────────────────────────────────
SUBTITLE_Y   = 0.70        # fraction of frame height

# Impact → Arial Bold → system default
FONT_PATHS = [
    "C:/Windows/Fonts/impact.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/Arial Bold.ttf",
]


def _font(size: int = FONT_SIZE) -> ImageFont.FreeTypeFont:
    for p in FONT_PATHS:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _measure(draw: ImageDraw.Draw, text: str, font) -> tuple[int, int]:
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]


def _draw_stroked(draw: ImageDraw.Draw, x: int, y: int,
                  text: str, font, fill: tuple) -> None:
    """Draw text with drop-shadow and thick stroke, then fill."""
    # shadow
    draw.text((x + SHADOW_OFF[0], y + SHADOW_OFF[1]),
              text, font=font, fill=SHADOW_COL)
    # stroke (all surrounding pixels)
    for dx in range(-STROKE_W, STROKE_W + 1):
        for dy in range(-STROKE_W, STROKE_W + 1):
            if dx or dy:
                draw.text((x + dx, y + dy), text, font=font, fill=STROKE_COL)
    # fill
    draw.text((x, y), text, font=font, fill=fill)


def _make_group_frame(
    group: list[str],        # 1-3 words
    active: int,             # index of the spoken word (0/1/2)
    frame_w: int,
    frame_h: int,
) -> np.ndarray:
    """
    Render one subtitle frame: up to 3 words on a single centred line.
    `active` word → yellow.  Others → white.
    """
    img  = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _font(FONT_SIZE)

    upper = [w.upper() for w in group]
    sizes = [_measure(draw, w, font) for w in upper]

    total_w = sum(s[0] for s in sizes) + WORD_GAP * (len(sizes) - 1)
    max_h   = max(s[1] for s in sizes)

    cx = frame_w // 2
    cy = int(frame_h * SUBTITLE_Y)

    # Draw words left-to-right
    x = cx - total_w // 2
    for i, (word, (w, h)) in enumerate(zip(upper, sizes)):
        ty = cy - h // 2
        color = ACTIVE_COL if i == active else PASSIVE_COL
        _draw_stroked(draw, x, ty, word, font, color)
        x += w + WORD_GAP

    return np.array(img)


def _build_clips(word_timings: list[dict], frame_w: int, frame_h: int) -> list:
    """
    Group word_timings into chunks of 3.
    Within each chunk, produce one ImageClip per word — all showing the full
    3-word group but with the currently spoken word highlighted yellow.
    """
    clips  = []
    n      = len(word_timings)
    GROUP  = 3

    for start_i in range(0, n, GROUP):
        chunk = word_timings[start_i : start_i + GROUP]   # 1, 2, or 3 items
        words = [item["word"].strip() for item in chunk]

        for local_idx, item in enumerate(chunk):
            t_start = item["start"]
            t_dur   = max(item["duration"], 0.07)
            fade    = min(FADE_DURATION, t_dur * 0.3)

            frame = _make_group_frame(words, local_idx, frame_w, frame_h)
            clips.append(
                ImageClip(frame)
                .with_start(t_start)
                .with_duration(t_dur)
                .with_effects([vfx.FadeIn(fade), vfx.FadeOut(fade)])
            )

    return clips


def _build_fallback_clips(script: str, duration: float,
                          frame_w: int, frame_h: int) -> list:
    """Even-spaced groups of 3 when no word timings are available."""
    words   = script.split()
    n       = len(words)
    GROUP   = 3
    per_w   = duration / max(n, 1)
    clips   = []

    for start_i in range(0, n, GROUP):
        chunk = words[start_i : start_i + GROUP]
        for local_idx in range(len(chunk)):
            t_start = (start_i + local_idx) * per_w
            fade    = min(FADE_DURATION, per_w * 0.3)
            frame   = _make_group_frame(chunk, local_idx, frame_w, frame_h)
            clips.append(
                ImageClip(frame)
                .with_start(t_start)
                .with_duration(per_w)
                .with_effects([vfx.FadeIn(fade), vfx.FadeOut(fade)])
            )

    return clips


def add_subtitles_and_audio(
    video_path:   Path,
    audio_path:   Path,
    script:       str,
    output_path:  Path,
    fps:          int = 30,
    word_timings: list[dict] | None = None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("Loading video and audio...")
    video = VideoFileClip(str(video_path))
    audio = AudioFileClip(str(audio_path))
    duration = audio.duration

    # Loop or trim video to match audio length exactly
    if video.duration < duration:
        from moviepy import concatenate_videoclips
        loops = int(duration / video.duration) + 1
        video = concatenate_videoclips([video] * loops).subclipped(0, duration)
    else:
        video = video.subclipped(0, duration)

    video = video.with_audio(audio)
    w, h  = video.size

    if word_timings:
        n_groups = (len(word_timings) + 2) // 3
        print(f"Rendering subtitles — {len(word_timings)} words in {n_groups} groups of 3...")
        sub_clips = _build_clips(word_timings, w, h)
    else:
        print("No word timings available — using evenly spaced groups...")
        sub_clips = _build_fallback_clips(script, duration, w, h)

    final = CompositeVideoClip([video] + sub_clips)

    print(f"Writing final video -> {output_path}")
    final.write_videofile(
        str(output_path),
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        logger="bar",
    )

    video.close()
    audio.close()
    final.close()
    return output_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--video",  required=True)
    parser.add_argument("--audio",  required=True)
    parser.add_argument("--script", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    add_subtitles_and_audio(
        Path(args.video), Path(args.audio), args.script, Path(args.output)
    )
