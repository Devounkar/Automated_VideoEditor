import sys
import os
import subprocess

def install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

try:
    import whisper
except ImportError:
    print("Installing openai-whisper...")
    install("openai-whisper")
    import whisper

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
VIDEO_FILE = "video1.mp4"
MODEL_SIZE = "medium"   # tiny / base / small / medium
# ─────────────────────────────────────────

def format_time(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

def format_srt(seconds):
    ms = int((seconds % 1) * 1000)
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def transcribe(path, model_size):
    if not os.path.exists(path):
        print(f"❌ File not found: {path}")
        sys.exit(1)

    print(f"📁 Video : {path}")
    print(f"🤖 Model : {model_size}")
    print(f"🎙️  Transcribing...")
    model = whisper.load_model(model_size)
    result = model.transcribe(path, verbose=False)
    base = path.rsplit(".", 1)[0]

    # Plain text
    with open(base + "_transcript.txt", "w", encoding="utf-8") as f:
        f.write(result["text"].strip())
    print(f"✅ Plain text       → {base}_transcript.txt")

    # Timestamped
    with open(base + "_transcript_timestamps.txt", "w", encoding="utf-8") as f:
        for seg in result["segments"]:
            f.write(f"[{format_time(seg['start'])} --> {format_time(seg['end'])}]  {seg['text'].strip()}\n")
    print(f"✅ With timestamps  → {base}_transcript_timestamps.txt")

    # SRT
    with open(base + ".srt", "w", encoding="utf-8") as f:
        for i, seg in enumerate(result["segments"], 1):
            f.write(f"{i}\n{format_srt(seg['start'])} --> {format_srt(seg['end'])}\n{seg['text'].strip()}\n\n")
    print(f"✅ SRT subtitles    → {base}.srt")

    print(f"\n── Preview ──────────────────────────────────")
    print(result["text"][:400])
    print(f"─────────────────────────────────────────────")
    print(f"\n🎉 Paste '{base}_transcript_timestamps.txt' into step3_pipeline.html")

if __name__ == "__main__":
    if len(sys.argv) > 1: VIDEO_FILE = sys.argv[1]
    if len(sys.argv) > 2: MODEL_SIZE = sys.argv[2]
    transcribe(VIDEO_FILE, MODEL_SIZE)
