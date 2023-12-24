from pydub import AudioSegment
import replicate
import os
import io
import requests

def set_replicate_api_key(key: str):
    os.environ["REPLICATE_API_TOKEN"] = key

def generate_sound(prompt : str):
    output = replicate.run(
        "meta/musicgen:7a76a8258b23fae65c5a22debb8841d1d7e816b75c2f24218cd2bd8573787906",
        input={"prompt": prompt,
                "duration": 2,
                "model_version": "melody",
                "output_format": "mp3"}
    )
    response = requests.get(output)
    audio = AudioSegment.from_file(io.BytesIO(response.content), format="mp3")
    return audio.fade_in(1000).fade_out(2000)

def export_and_return_raw(audio_segment: AudioSegment, path: str) -> bytes:
    # Export concatenated audio to a file
    # audio_segment.export(path, format="mp3")

    # Get raw audio bytes to return
    buffer = io.BytesIO()
    audio_segment.export(buffer, format="mp3")
    return buffer.getvalue()