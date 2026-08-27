from flask import Flask, render_template, request, send_file
import edge_tts
import asyncio
import subprocess
import os

app = Flask(__name__)

async def make_voice(text, voice, raw_output):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(raw_output)

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        text = request.form.get("text", "").strip()

        if not text:
            return "စာသားထည့်ပေးပါ"

        voice = "my-MM-NilarNeural"
        raw_output = "raw.mp3"
        output = "output.mp3"

        try:
            asyncio.run(make_voice(text, voice, raw_output))

            subprocess.run([
                "ffmpeg", "-y",
                "-i", raw_output,
                "-ar", "24000",
                "-ac", "1",
                "-b:a", "128k",
                output
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            return send_file(
                output,
                as_attachment=True,
                download_name="myanmar-voice.mp3",
                mimetype="audio/mpeg"
            )

        except Exception as e:
            return f"အသံပြောင်းရာမှာ အမှားဖြစ်ပါတယ်: {e}"

    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
