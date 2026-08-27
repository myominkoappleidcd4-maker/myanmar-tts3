from flask import Flask, render_template, request, send_file
import edge_tts
import asyncio
import os

app = Flask(__name__)

VOICES = {
    "my-MM-NilarNeural": "Myanmar Female - Nilar",
    "my-MM-ThihaNeural": "Myanmar Male - Thiha"
}

async def make_voice(text, voice, output):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output)

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        text = request.form.get("text", "").strip()
        voice = request.form.get("voice", "my-MM-NilarNeural")

        if not text:
            return render_template("index.html", error="စာသားထည့်ပေးပါ။")

        if voice not in VOICES:
            voice = "my-MM-NilarNeural"

        output = "output.mp3"

        try:
            asyncio.run(make_voice(text, voice, output))
            return send_file(
                output,
                mimetype="audio/mpeg",
                as_attachment=False,
                download_name="myanmar-voice.mp3"
            )
        except Exception as e:
            return f"အသံပြောင်းရာမှာ Error ဖြစ်နေပါတယ်: {e}", 500

    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
