"""
Pacing Fix v3
=============
v1 bug: cat+concat corrupted timestamps → 42min freeze
v2 bug: 154 silences → filter expression too long → cannot allocate memory

v3 fix: Cut each SPEECH segment individually with re-encode (clean timestamps),
        write proper filelist, concat. Re-encoding = no freeze, correct duration.
"""

import sys
import os
import subprocess

def install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

for pkg, imp in [("librosa", "librosa"), ("numpy", "numpy")]:
    try:
        __import__(imp)
    except ImportError:
        print(f"Installing {pkg}...")
        install(pkg)

import numpy as np
import librosa

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
VIDEO_FILE        = "video1.mp4"
SILENCE_THRESHOLD = 0.018   # raise if too much is being cut
MIN_SILENCE_SEC   = 1.0     # only remove silences longer than 1 second
KEEP_PADDING_SEC  = 0.05    # tiny natural pause kept at edges
# ─────────────────────────────────────────

def fmt(s):
    m, sec = divmod(int(s), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"

def fmt_ff(s):
    ms = int((s % 1) * 1000)
    m, sec = divmod(int(s), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}.{ms:03d}"

def get_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except:
        return None

def extract_audio(video_path):
    out = video_path.rsplit(".", 1)[0] + "_tmp_audio.wav"
    r = subprocess.run(
        ["ffmpeg", "-i", video_path, "-vn", "-acodec", "pcm_s16le",
         "-ar", "16000", "-ac", "1", out, "-y", "-loglevel", "error"],
        capture_output=True)
    if r.returncode != 0:
        print("❌ Audio extraction failed:", r.stderr.decode())
        sys.exit(1)
    return out

def detect_keep_regions(y, sr, threshold, min_silence, padding):
    hop = 512
    rms = librosa.feature.rms(y=y, frame_length=1024, hop_length=hop)[0]
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)
    total_dur = float(len(y)) / sr

    is_speech = rms >= threshold
    silences = []
    in_sil = False
    sil_start = 0.0

    for i, speech in enumerate(is_speech):
        if not speech and not in_sil:
            in_sil = True
            sil_start = times[i]
        elif speech and in_sil:
            in_sil = False
            dur = times[i] - sil_start
            if dur >= min_silence:
                silences.append((
                    round(sil_start + padding, 3),
                    round(times[i] - padding, 3)
                ))

    if in_sil:
        dur = total_dur - sil_start
        if dur >= min_silence:
            silences.append((round(sil_start + padding, 3), round(total_dur, 3)))

    keep = []
    cursor = 0.0
    for sil_s, sil_e in silences:
        if sil_s > cursor + 0.05:
            keep.append((round(cursor, 3), round(sil_s, 3)))
        cursor = sil_e
    if cursor < total_dur - 0.05:
        keep.append((round(cursor, 3), round(total_dur, 3)))

    return keep, silences

def cut_segment(video_path, start, end, out_path):
    cmd = [
        "ffmpeg", "-i", video_path,
        "-ss", fmt_ff(start),
        "-to", fmt_ff(end),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-preset", "ultrafast",
        "-avoid_negative_ts", "1",
        out_path, "-y",
        "-loglevel", "error"
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0

def concat_segments(part_files, output_path):
    list_path = output_path.rsplit(".", 1)[0] + "_filelist.txt"
    with open(list_path, "w") as f:
        for p in part_files:
            f.write(f"file '{os.path.abspath(p)}'\n")

    cmd = [
        "ffmpeg", "-f", "concat", "-safe", "0",
        "-i", list_path,
        "-c", "copy",
        "-movflags", "+faststart",
        output_path, "-y",
        "-loglevel", "error"
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    os.remove(list_path)
    if r.returncode != 0:
        print("❌ Concat failed:", r.stderr)
        return False
    return True

def main():
    global VIDEO_FILE

    if len(sys.argv) > 1:
        VIDEO_FILE = sys.argv[1]

    if not os.path.exists(VIDEO_FILE):
        print(f"❌ File not found: {VIDEO_FILE}")
        sys.exit(1)

    base = VIDEO_FILE.rsplit(".", 1)[0]
    output_path = base + "_paced.mp4"
    tmp_dir = base + "_tmp_parts"

    original_dur = get_duration(VIDEO_FILE)
    print(f"\n🎙️  Pacing Fix v3")
    print(f"{'─'*52}")
    print(f"Input  : {VIDEO_FILE} ({fmt(original_dur or 0)})")
    print(f"Output : {output_path}")
    print(f"Min silence to cut: {MIN_SILENCE_SEC}s")
    print(f"{'─'*52}\n")

    print("🎬 Extracting audio...")
    audio_path = extract_audio(VIDEO_FILE)

    print("📊 Analysing silences...")
    y, sr = librosa.load(audio_path, sr=16000, mono=True)
    keep_regions, silences = detect_keep_regions(
        y, sr,
        threshold=SILENCE_THRESHOLD,
        min_silence=MIN_SILENCE_SEC,
        padding=KEEP_PADDING_SEC
    )

    if os.path.exists(audio_path):
        os.remove(audio_path)

    if not silences:
        print("✅ No significant silences found — video already well paced!")
        sys.exit(0)

    total_silence = sum(e - s for s, e in silences)
    print(f"✅ Found {len(silences)} silence(s) totalling {total_silence:.1f}s")
    print(f"   Keeping {len(keep_regions)} speech segment(s)")
    if original_dur:
        print(f"   Expected output: {fmt(original_dur - total_silence)}")

    os.makedirs(tmp_dir, exist_ok=True)

    print(f"\n✂️  Cutting {len(keep_regions)} segments (re-encoding for clean timestamps)...")
    part_files = []
    failed = 0

    for i, (start, end) in enumerate(keep_regions):
        out = os.path.join(tmp_dir, f"part_{i:04d}.mp4")
        ok = cut_segment(VIDEO_FILE, start, end, out)
        if ok and os.path.exists(out):
            part_files.append(out)
            if (i + 1) % 10 == 0 or i == len(keep_regions) - 1:
                print(f"   {i+1}/{len(keep_regions)} done...")
        else:
            failed += 1
            print(f"   ⚠️  Segment {i+1} failed, skipping")

    if not part_files:
        print("❌ All segments failed.")
        sys.exit(1)

    if failed:
        print(f"⚠️  {failed} segment(s) skipped")

    print(f"\n🔗 Concatenating {len(part_files)} segments...")
    ok = concat_segments(part_files, output_path)

    print("🧹 Cleaning up temp files...")
    for p in part_files:
        if os.path.exists(p): os.remove(p)
    try:
        os.rmdir(tmp_dir)
    except:
        pass

    if not ok:
        sys.exit(1)

    new_dur = get_duration(output_path)
    if new_dur:
        print(f"\n✅ Done!")
        print(f"   Output  : {output_path}")
        print(f"   Duration: {fmt(new_dur)} (was {fmt(original_dur or 0)})")
        print(f"   Removed : {(original_dur or 0) - new_dur:.1f}s of silence")
    else:
        print(f"\n✅ Done! → {output_path}")

    print(f"\n📌 Next step:")
    print(f"   python step1_transcribe.py {output_path}")

if __name__ == "__main__":
    main()
