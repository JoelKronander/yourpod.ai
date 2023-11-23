from openai import OpenAI, AsyncOpenAI
import instructor
from pydantic import BaseModel, Field
from elevenlabs import generate
import asyncio
from pydub import AudioSegment
import io
from typing import Optional
from tempfile import NamedTemporaryFile
import os

from sound import Sounds, export_and_return_raw

class PodcastSectionOverview(BaseModel):
    length_in_seconds: int = Field(..., description="The length of the section in seconds.")
    description: str = Field(..., description="List of high level episode content.")

class PodcastOverview(BaseModel):
    title: str
    description: str
    section_overviews: list[PodcastSectionOverview]


class PodcastSection(BaseModel):
    length_in_seconds: int
    transcript: str

class Podcast(PodcastOverview):
    """The full podcast, including the transcript."""
    transcript: str
    length_in_minutes: float
    sections: list[PodcastSection]
    sounds: Sounds

    class Config:
        arbitrary_types_allowed = True


def get_podcast_overview(input_text, podcast_length, openai_api_key) -> PodcastOverview:
    client = instructor.patch(OpenAI(api_key=openai_api_key))
    prompt = f"""
You are a podcast producer that has been asked to produce a podcast on {input_text}.
The podcast should be about {podcast_length} minutes long. 
A single host will be reading the podcast transcript. Plase make it to the point, but also engaging.

Write a outline of the podcast, consisting of several sections.
Each section will be read one after the other as a contionus podcast with no breaks in between.
Each section should be between 2 and 4 minutes long.
Don't make the podcast too long, it should be about {podcast_length} minutes long. 
Use as few sections as possible to make the podcast about {podcast_length} minutes long.
Between each section, you can optionally add a sound effect, note that that a sound effect might not be needed between all sections.

Provide the title of the podcast, the description of the podcast, a visual description of the podcast cover image
and describe the high level content, and length in minutes, and optionally sound effect for each section.
"""
    print(f"Prompt: {prompt}")
    overview: PodcastOverview = client.chat.completions.create(
        model="gpt-4-1106-preview",
        response_model=PodcastOverview,
        messages=[
            {"role": "user", "content": prompt},
        ],
        max_retries=2,
    )
    print(f"Overview: {overview}")
    return overview


def get_podcast_section(
        podcast_overview: PodcastOverview, section: PodcastSectionOverview, podcast: Podcast, desired_length: int,
        openai_api_key
) -> PodcastSection:
    client = instructor.patch(OpenAI(api_key=openai_api_key))
    """Generate a podcast section from a podcast overview."""
    prompt = f"""
You are a podcast host that is explaining {podcast_overview.title} to your audience.
The podcast is about {podcast_overview.description}.

The podcast has the following episodes, with estimated length in seconds:
{[[s.description, s.length_in_seconds] for s in podcast_overview.section_overviews]}

Before this section, the transcript is:
{podcast.transcript}

You are now writing the detailed transcript for the section {section.description}.
The transcipt for this section was initally estimated to be about {section.length_in_seconds} seconds to read, but please adjust it as needed to stay make the complete podcast about {desired_length} minutes long.
The estimated length of the podcast so far is {podcast.length_in_minutes}. 
The podcast should be about {desired_length} minutes long, so there is about {desired_length - podcast.length_in_minutes} minutes left for the rest of the podcast sections.
A single host will be reading the podcast transcript. Plase make it to the point, but also engaging.

Write the detailed transcript for this podcast section. 
It will be concatenated with the other sections to form the full podcast transcript.
"""
    print(f"Prompt: {prompt}")
    section: PodcastSection = client.chat.completions.create(
        model="gpt-4-1106-preview",
        response_model=PodcastSection,
        messages=[
            {"role": "user", "content": prompt},
        ],
    )
    print(f"Section: {section}")
    return section


def get_podcast(input_text: str, podcast_length: int, openai_api_key) -> PodcastOverview:
    client = instructor.patch(OpenAI(api_key=openai_api_key))
    podcast_overview: PodcastOverview = get_podcast_overview(input_text, podcast_length)
    podcast: Podcast = Podcast(**podcast_overview.dict(), length_in_minutes=0, transcript="", sections=[])
    for section_overview in podcast_overview.section_overviews:
        section = get_podcast_section(podcast_overview, section_overview, podcast, desired_length=podcast_length)
        podcast.transcript += "\n\n" + section.transcript
        podcast.length_in_minutes += section.length_in_seconds / 60
        podcast.sections.append(section)

    return podcast


def get_podcast_image(cover_image_description: str) -> str:
    """Generate a podcast cover image from a description of the image."""
    return "https://www.google.com/url?sa=i&url=https%3A%2F%2Funsplash.com%2Fs%2Fphotos%2Fnatural&psig=AOvVaw1j_-1b18H9E8vIIJXnVbGE&ust=1700202091318000&source=images&cd=vfe&ved=0CBIQjRxqFwoTCKichsDwx4IDFQAAAAAdAAAAABAE"


def text_2_speech_elevenlabs(podcast, voice):
    audio_path = f"./data/yourpod.mp3"
    print(f"Generating audio for voice {voice}, to file {audio_path}")

    # split prompt into chunks less than 5000 characters
    chunks = [podcast.transcript[i: i + 4950] for i in range(0, len(podcast.transcript), 4950)]

    concatenated_audio = AudioSegment.empty()  # Creating an empty audio segment
    concatenated_audio += podcast.sounds.intro_sound

    for index, chunk in enumerate(chunks):
        chunk_audio = generate(text=chunk, voice=voice, model="eleven_multilingual_v2")
        # Assuming that the generate function represents mp3
        audio_segment = AudioSegment.from_mp3(io.BytesIO(chunk_audio))
        concatenated_audio += audio_segment
        if index < len(chunks) - 1:
            concatenated_audio += podcast.sounds.section_sound

    concatenated_audio += podcast.sounds.outro_sound

    raw_audio_bytes = export_and_return_raw(concatenated_audio, audio_path)
    return raw_audio_bytes


async def generate_audio_chunk(client, voice, chunk, nr):
    response = await client.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=chunk
    )
    with NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
        temp_file_path = temp_file.name  # Get the file path
        response.stream_to_file(temp_file_path)  # Use the file path here
    chunk_audio = AudioSegment.from_mp3(temp_file_path)  # Use the file path to load the audio
    # Optionally delete the temporary file if needed
    os.remove(temp_file_path)
    return chunk_audio


async def text_2_speech_openai(podcast: Podcast, voice, openai_api_key):
    audio_path = f"./data/yourpod.mp3"
    print(f"Generating audio for voice {voice}, to file {audio_path}")

    client = AsyncOpenAI(api_key=openai_api_key)
    chunks = [section.transcript for section in podcast.sections]

    # make sure that each chunk is less than 4000 characters, otherwise split the chunk in two entries
    while any([len(chunk) > 4000 for chunk in chunks]):
        new_chunks = []
        for chunk in chunks:
            if len(chunk) > 4000:
                new_chunks.append(chunk[:4000])
                new_chunks.append(chunk[4000:])
            else:
                new_chunks.append(chunk)
        chunks = new_chunks

    tasks = []
    for nr, chunk in enumerate(chunks):
        tasks.append(generate_audio_chunk(client, voice, chunk, nr))
    chunk_audios = await asyncio.gather(*tasks)

    concatenated_audio = AudioSegment.empty()
    concatenated_audio += podcast.sounds.intro_sound

    for index, chunk_audio in enumerate(chunk_audios):
        concatenated_audio += chunk_audio
        if index < len(chunks) - 1:
            concatenated_audio += podcast.sounds.section_sound

    concatenated_audio += podcast.sounds.outro_sound

    raw_audio_bytes = export_and_return_raw(concatenated_audio, audio_path)
    return raw_audio_bytes




