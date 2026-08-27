from flask import Flask, render_template, request, send_file
from youtube_transcript_api import YouTubeTranscriptApi
from deep_translator import GoogleTranslator
import edge_tts
import asyncio
import subprocess
import os
import re

app = Flask(__name__)

def get_video_id(url):
    patterns = [
        r"(?:v=|youtu\.be/|youtube\.com/shorts/)([A-Za-z0-9_-]{11})"
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def get_transcript(video_id):
    api = YouTubeTranscriptApi()

    try:
        transcript = api.fetch(
            video_id,
            languages=["my", "en"]
        )

        return "\n".join(
            item.text for item in transcript
        )

    except Exception:
        transcript = api.list(video_id)

        for t in transcript:
            if t.language_code.startswith("en"):
                data = t.fetch()
                return "\n".join(item.text for item in data)

        for t in transcript:
            data = t.fetch()
            return "\n".join(item.text for item in data)

    return ""


def translate_to_myanmar(text):
    translator = GoogleTranslator(
        source="auto",
        target="my"
    )

    chunks = []
    current = ""

    for line in text.splitlines():
        if len(current) + len(line) > 3000:
            if current:
                chunks.append(current)
            current = line
        else:
            current += "\n" + line

    if current:
        chunks.append(current)

    result = []

    for chunk in chunks:
        try:
            translated = translator.translate(chunk)
            result.append(translated)
        except Exception:
            result.append(chunk)

    return "\n".join(result)


async def make_voice(text, voice, output):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output)


@app.route("/", methods=["GET", "POST"])
def home():

    transcript = ""
    translated = ""
    error = ""

    if request.method == "POST":

        action = request.form.get("action", "")
        text = request.form.get("text", "").strip()
        youtube_url = request.form.get("youtube_url", "").strip()

        # YouTube Transcript
        if action == "transcript":

            if not youtube_url:
                error = "YouTube Link ထည့်ပေးပါ"
                return render_template(
                    "index.html",
                    transcript=transcript,
                    translated=translated,
                    error=error
                )

            video_id = get_video_id(youtube_url)

            if not video_id:
                error = "YouTube Link မမှန်ပါ"
                return render_template(
                    "index.html",
                    transcript=transcript,
                    translated=translated,
                    error=error
                )

            try:
                transcript = get_transcript(video_id)

                if not transcript:
                    error = "Transcript မတွေ့ပါ"
            except Exception as e:
                error = "Transcript ရယူလို့မရပါ: " + str(e)

            return render_template(
                "index.html",
                transcript=transcript,
                translated=translated,
                error=error
            )

        # Myanmar Translation
        if action == "translate":

            text = request.form.get("text", "").strip()

            if not text:
                error = "Transcript စာသားထည့်ပေးပါ"
            else:
                try:
                    translated = translate_to_myanmar(text)
                except Exception as e:
                    error = "ဘာသာပြန်ရာမှာ Error ဖြစ်ပါတယ်: " + str(e)

            return render_template(
                "index.html",
                transcript=text,
                translated=translated,
                error=error
            )

        # Text to Voice
        if action == "voice":

            text = request.form.get("text", "").strip()
            voice = request.form.get(
                "voice",
                "my-MM-NilarNeural"
            )

            filename = request.form.get(
                "filename",
                "myanmar-voice"
            ).strip()

            if not text:
                return render_template(
                    "index.html",
                    transcript=transcript,
                    translated=translated,
                    error="အသံထုတ်မယ့်စာသားထည့်ပေးပါ"
                )

            raw_output = "raw.mp3"
            output = filename + ".mp3"

            try:
                asyncio.run(
                    make_voice(
                        text,
                        voice,
                        raw_output
                    )
                )

                subprocess.run([
                    "ffmpeg",
                    "-y",
                    "-i",
                    raw_output,
                    "-ar",
                    "24000",
                    "-ac",
                    "1",
                    "-b:a",
                    "128k",
                    output
                ], check=True, stdout=subprocess.DEVNULL)

                return send_file(
                    output,
                    as_attachment=True,
                    download_name=output,
                    mimetype="audio/mpeg"
                )

            except Exception as e:
                error = "အသံထုတ်ရာမှာ Error ဖြစ်ပါတယ်: " + str(e)

    return render_template(
        "index.html",
        transcript=transcript,
        translated=translated,
        error=error
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
