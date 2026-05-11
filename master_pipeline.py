# master_pipeline.py — single command, full automation

import subprocess, os, json, openai

VIDEO = "raw_input.mp4"

# Stage 1: Pacing
subprocess.run(["python", "step2_pacing_fix.py", VIDEO])
paced = VIDEO.replace(".mp4", "_paced.mp4")

# Stage 2: Transcribe
subprocess.run(["python", "step1_transcribe.py", paced])
with open(paced.replace(".mp4", "_transcript_timestamps.txt")) as f:
    transcript = f.read()

client = openai.OpenAI()

# Stage 3: LLM segment selection
seg_response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{
        "role": "user",
        "content": f"Given this transcript, return JSON list of segments to KEEP with start/end seconds.\n\n{transcript}"
    }]
)
segments = json.loads(seg_response.choices[0].message.content)
# ... apply cuts via FFmpeg

# Stage 4: LLM slide generation
slide_response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{
        "role": "user",
        "content": f"Identify topic breaks and return JSON slide definitions with time, title, subtitle, accent color.\n\n{transcript}"
    }]
)
slides = json.loads(slide_response.choices[0].message.content)
# inject into add_slides.py SLIDES list dynamically

# Stage 5: Subtitles + Slides composite
subprocess.run(["python", "add_subtitles_and_slides.py", paced])