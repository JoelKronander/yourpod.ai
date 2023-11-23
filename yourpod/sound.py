from pydub import AudioSegment
import replicate
import os
import io
import requests


class Sounds:
    def __init__(self, intro_sound: AudioSegment, section_sound: AudioSegment, outro_sound: AudioSegment):
        self.intro_sound = intro_sound
        self.section_sound = section_sound
        self.outro_sound = outro_sound

def set_replicate_api_key(key: str):
    os.environ["REPLICATE_API_TOKEN"] = key

def generate_sound(section: str, topic: str):
    prompt = "A clear {} to a podcast on the topic {}".format(section, topic)
    output = replicate.run(
        "meta/musicgen:7a76a8258b23fae65c5a22debb8841d1d7e816b75c2f24218cd2bd8573787906",
        input={"prompt": prompt,
                "duration": 3,
                "model_version": "melody",
                "output_format": "mp3"}
    )
    response = requests.get(output)
    audio = AudioSegment.from_file(io.BytesIO(response.content), format="mp3")
    print(prompt)
    return audio.fade_in(1000).fade_out(2000)

def export_and_return_raw(audio_segment: AudioSegment, path: str) -> bytes:
    # Export concatenated audio to a file
    # audio_segment.export(path, format="mp3")

    # Get raw audio bytes to return
    buffer = io.BytesIO()
    audio_segment.export(buffer, format="mp3")
    return buffer.getvalue()