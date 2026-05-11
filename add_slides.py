import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip
import os

# ─── CONFIG ───────────────────────────────────────────────
VIDEO_PATH = "video1_paced_youtube_final.mp4"       # 👈 Change this to your video file
OUTPUT_PATH = "video1_paced_youtube_slides.mp4"
SLIDE_DURATION = 2.5                  # seconds each slide is shown
FADE_DURATION = 0.4                   # seconds for fade in/out
# ──────────────────────────────────────────────────────────

# ─── SLIDE DEFINITIONS (time in seconds) ──────────────────
SLIDES = [
    {
        "time": 25,
        "title": "THAT WAS ME",
        "subtitle": "Building. Scaling. Hustling. Surviving.",
        "accent": (220, 80, 60),       # red-orange
    },
    {
        "time": 80,
        "title": "SUCCESS REWARDS DELAY",
        "subtitle": "Postpone sleep. Postpone meals.\nPostpone recovery. Nothing breaks immediately.",
        "accent": (200, 140, 30),      # amber
    },
    {
        "time": 140,
        "title": "HIGH PERFORMERS\nMASK SIGNALS",
        "subtitle": "Feeling wired isn't feeling well.",
        "accent": (60, 140, 200),      # blue
    },
    {
        "time": 176,
        "title": "THE CEO ANALOGY",
        "subtitle": "Brilliant leader. Exhausted system underneath.\nThe company performs — until it doesn't.",
        "accent": (120, 80, 200),      # purple
    },
    {
        "time": 220,
        "title": "DIRECTION > DRAMA",
        "subtitle": "Your labs don't need to scream.\nThey just need to point.",
        "accent": (40, 170, 120),      # teal
    },
    {
        "time": 265,
        "title": "THE SHIFT",
        "subtitle": "Stop asking: \"Am I sick?\"\nStart asking: \"Is this system moving right?\"",
        "accent": (220, 80, 60),       # red-orange
    },
    {
        "time": 317,
        "title": "COMING UP NEXT",
        "subtitle": "What happens when you ignore\nearly health warnings — and why the\nbody always collects later.",
        "accent": (60, 140, 200),      # blue
    },
]
# ──────────────────────────────────────────────────────────


def get_font(size):
    for path in [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/SFNSDisplay.ttf",
        "/System/Library/Fonts/SFNSText.ttf",
    ]:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
    return ImageFont.load_default()


def make_slide_image(title, subtitle, accent, video_w, video_h):
    """Render a full-screen slide with dark background, accent bar, title and subtitle."""
    img = Image.new("RGBA", (video_w, video_h), (15, 15, 20, 230))  # dark semi-transparent
    draw = ImageDraw.Draw(img)

    # Accent bar on left
    bar_width = max(8, video_w // 80)
    draw.rectangle([(40, video_h // 5), (40 + bar_width, video_h * 4 // 5)], fill=accent + (255,))

    # Title
    title_font = get_font(max(48, video_h // 12))
    title_x = 40 + bar_width + 30
    title_y = video_h // 3

    # Title shadow
    for dx, dy in [(-2, -2), (2, 2), (-2, 2), (2, -2)]:
        draw.multiline_text(
            (title_x + dx, title_y + dy), title,
            font=title_font, fill=(0, 0, 0, 180), spacing=10
        )
    # Title text
    draw.multiline_text(
        (title_x, title_y), title,
        font=title_font, fill=(255, 255, 255, 255), spacing=10
    )

    # Accent underline below title
    title_bbox = draw.multiline_textbbox((title_x, title_y), title, font=title_font, spacing=10)
    title_bottom = title_bbox[3] + 16
    draw.rectangle(
        [(title_x, title_bottom), (title_x + min(400, video_w // 3), title_bottom + 4)],
        fill=accent + (200,)
    )

    # Subtitle
    sub_font = get_font(max(28, video_h // 22))
    sub_y = title_bottom + 30
    draw.multiline_text(
        (title_x, sub_y), subtitle,
        font=sub_font, fill=(200, 200, 200, 230), spacing=10
    )

    return np.array(img)


def make_slide_clip(slide, video_w, video_h):
    """Create a slide ImageClip with fade in/out."""
    img_array = make_slide_image(
        slide["title"], slide["subtitle"], slide["accent"], video_w, video_h
    )
    start = slide["time"]
    end = start + SLIDE_DURATION

    clip = (
        ImageClip(img_array)
        .set_start(start)
        .set_end(end)
        .set_position((0, 0))
        .crossfadein(FADE_DURATION)
        .crossfadeout(FADE_DURATION)
    )
    return clip


def add_slides_to_video(video_path, output_path):
    print("🎬 Loading video...")
    video = VideoFileClip(video_path)
    video_w, video_h = video.size

    print(f"📊 Creating {len(SLIDES)} slides...")
    slide_clips = []
    for i, slide in enumerate(SLIDES):
        # Skip slides beyond video duration
        if slide["time"] >= video.duration:
            print(f"  ⚠️  Slide {i+1} at {slide['time']}s skipped (beyond video length)")
            continue
        clip = make_slide_clip(slide, video_w, video_h)
        slide_clips.append(clip)
        print(f"  ✅ Slide {i+1}: '{slide['title']}' at {slide['time']}s")

    print("🎞️  Compositing slides onto video...")
    final = CompositeVideoClip([video] + slide_clips)

    print(f"💾 Exporting to {output_path}...")
    final.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        fps=video.fps,
    )
    print(f"✅ Done! Saved: {output_path}")


if __name__ == "__main__":
    if not os.path.exists(VIDEO_PATH):
        print(f"❌ Video not found: {VIDEO_PATH}")
    else:
        add_slides_to_video(VIDEO_PATH, OUTPUT_PATH)