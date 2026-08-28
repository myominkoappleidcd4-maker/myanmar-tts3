from flask import Flask, render_template, request, send_from_directory
import edge_tts
import asyncio
import os
import re
import uuid
import subprocess
from werkzeug.utils import secure_filename

app = Flask(__name__)

OUTPUT_DIR = "static/audio"
os.makedirs(OUTPUT_DIR, exist_ok=True)

VOICES = {
    "nilar": "my-MM-NilarNeural",
    "thiha": "my-MM-ThihaNeural"
}

SPEEDS = {
    "slow": "-20%",
    "normal": "+0%",
    "fast": "+20%"
}

PITCHES = {
    "low": "-10Hz",
    "normal": "+0Hz",
    "high": "+10Hz"
}


def split_text(text, max_length=2500):
    text = text.strip()

    if len(text) <= max_length:
        return [text]

    sentences = re.split(r"(?<=[။.!?])\s*", text)

    parts = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()

        if not sentence:
            continue

        if len(current) + len(sentence) + 1 <= max_length:
            current += sentence + " "
        else:
            if current:
                parts.append(current.strip())

            current = sentence + " "

    if current:
        parts.append(current.strip())

    return parts


async def make_voice(text, voice, output, rate, pitch):
    communicate = edge_tts.Communicate(
        text,
        voice,
        rate=rate,
        pitch=pitch
    )

    await communicate.save(output)


def create_audio(text, voice, rate, pitch, output_path):
    parts = split_text(text)

    temp_files = []

    try:
        if len(parts) == 1:
            asyncio.run(
                make_voice(
                    parts[0],
                    voice,
                    output_path,
                    rate,
                    pitch
                )
            )
            return

        for index, part in enumerate(parts):
            temp_name = f"temp_{uuid.uuid4().hex}_{index}.mp3"
            temp_path = os.path.join(OUTPUT_DIR, temp_name)

            asyncio.run(
                make_voice(
                    part,
                    voice,
                    temp_path,
                    rate,
                    pitch
                )
            )

            temp_files.append(temp_path)

        list_file = os.path.join(
            OUTPUT_DIR,
            f"concat_{uuid.uuid4().hex}.txt"
        )

        with open(list_file, "w", encoding="utf-8") as f:
            for file in temp_files:
                f.write(
                    "file '{}'\n".format(
                        os.path.abspath(file).replace("'", "'\\''")
                    )
                )

        command = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            list_file,
            "-c",
            "copy",
            output_path
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(result.stderr)

    finally:
        for file in temp_files:
            if os.path.exists(file):
                os.remove(file)

        if "list_file" in locals() and os.path.exists(list_file):
            os.remove(list_file)


@app.route("/", methods=["GET", "POST"])
def home():

    text = ""
    voice_key = "nilar"
    speed = "normal"
    pitch = "normal"
    filename = "myanmar-voice"
    audio_file = None
    error = ""

    if request.method == "POST":

        text = request.form.get("text", "").strip()
        voice_key = request.form.get("voice", "nilar")
        speed = request.form.get("speed", "normal")
        pitch = request.form.get("pitch", "normal")
        filename = request.form.get(
            "filename",
            "myanmar-voice"
        ).strip()

        if not text:
            error = "စာသားထည့်ပေးပါ။"

        elif voice_key not in VOICES:
            error = "အသံရွေးချယ်မှု မမှန်ပါ။"

        elif speed not in SPEEDS:
            error = "Speed ရွေးချယ်မှု မမှန်ပါ။"

        elif pitch not in PITCHES:
            error = "Pitch ရွေးချယ်မှု မမှန်ပါ။"

        else:

            filename = secure_filename(filename)

            if not filename:
                filename = "myanmar-voice"

            output_name = filename + ".mp3"
            output_path = os.path.join(
                OUTPUT_DIR,
                output_name
            )

            try:
                create_audio(
                    text,
                    VOICES[voice_key],
                    SPEEDS[speed],
                    PITCHES[pitch],
                    output_path
                )

                if os.path.exists(output_path):
                    audio_file = output_name
                else:
                    error = "အသံဖိုင် မထုတ်နိုင်ပါ။"

            except Exception as e:
                error = "အသံထုတ်ရာတွင် Error ဖြစ်နေပါတယ်။"
                print("ERROR:", e)

    return render_template(
        "index.html",
        text=text,
        voice=voice_key,
        speed=speed,
        pitch=pitch,
        filename=filename,
        audio_file=audio_file,
        error=error
    )


@app.route("/audio/<filename>")
def audio(filename):
    return send_from_directory(
        OUTPUT_DIR,
        filename,
        as_attachment=False
    )


@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(
        OUTPUT_DIR,
        filename,
        as_attachment=True
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
