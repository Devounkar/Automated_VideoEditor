import whisper
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip

# ─── CONFIG ───────────────────────────────────────────────
VIDEO_PATH = "video1_paced_reel.mp4"       # 👈 Change this to your video file
OUTPUT_PATH = "video1_reel.mp4"
FONT_SIZE = 36
SUBTITLE_Y_POS = 0.88
WHISPER_MODEL = "medium"
# ──────────────────────────────────────────────────────────


def transcribe_video(video_path):
    print("🔊 Transcribing audio with Whisper...")
    model = whisper.load_model(WHISPER_MODEL)
    result = model.transcribe(video_path)
    print(f"✅ Found {len(result['segments'])} subtitle segments.")
    return result["segments"]


def make_text_image(text, video_width):
    font_size = FONT_SIZE
    padding = 12

    # Try to load a nice macOS font, fall back gracefully
    font = None
    for font_path in [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/SFNSText.ttf",
    ]:
        if os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, font_size)
                break
            except:
                continue
    if font is None:
        font = ImageFont.load_default()

    # Word wrap (~45 chars per line)
    words = text.split()
    lines, line = [], []
    for word in words:
        line.append(word)
        if len(" ".join(line)) > 45:
            lines.append(" ".join(line[:-1]))
            line = [word]
    lines.append(" ".join(line))
    wrapped = "\n".join(lines)

    # Measure text size
    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=6)
    w = bbox[2] - bbox[0] + padding * 2
    h = bbox[3] - bbox[1] + padding * 2

    # Draw on transparent canvas
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    x, y = padding, padding

    # Black stroke/shadow
    for dx in [-2, -1, 0, 1, 2]:
        for dy in [-2, -1, 0, 1, 2]:
            if dx != 0 or dy != 0:
                draw.multiline_text((x+dx, y+dy), wrapped, font=font,
                                    fill=(0, 0, 0, 220), spacing=6, align="center")
    # White text
    draw.multiline_text((x, y), wrapped, font=font,
                        fill=(255, 255, 255, 255), spacing=6, align="center")

    return np.array(img)


def create_subtitle_clips(segments, video_size):
    print("📝 Creating subtitle overlays...")
    subtitle_clips = []
    video_width, video_height = video_size

    for seg in segments:
        start = seg["start"]
        end = seg["end"]
        text = seg["text"].strip()
        if not text:
            continue

        img_array = make_text_image(text, video_width)
        clip = (
            ImageClip(img_array, ismask=False)
            .set_start(start)
            .set_end(end)
            .set_position(("center", SUBTITLE_Y_POS), relative=True)
        )
        subtitle_clips.append(clip)

    return subtitle_clips


def add_subtitles_to_video(video_path, output_path):
    segments = transcribe_video(video_path)

    print("🎬 Loading video...")
    video = VideoFileClip(video_path)

    subtitle_clips = create_subtitle_clips(segments, video.size)

    print("🎞️  Compositing subtitles onto video...")
    final_video = CompositeVideoClip([video] + subtitle_clips)

    print(f"💾 Exporting to {output_path} ...")
    final_video.write_videofile(
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
        add_subtitles_to_video(VIDEO_PATH, OUTPUT_PATH)