from pydub import AudioSegment
import io

class Sounds:
    def __init__(self, intro_sound: AudioSegment, section_sound: AudioSegment, outro_sound: AudioSegment):
        self.intro_sound = intro_sound
        self.section_sound = section_sound
        self.outro_sound = outro_sound

def export_and_return_raw(audio_segment: AudioSegment, path: str) -> bytes:
    # Export concatenated audio to a file
    audio_segment.export(path, format="mp3")

    # Get raw audio bytes to return
    buffer = io.BytesIO()
    audio_segment.export(buffer, format="mp3")
    return buffer.getvalue()