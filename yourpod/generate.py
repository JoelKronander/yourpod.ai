from openai import OpenAI
import instructor
from pydantic import BaseModel, Field
from elevenlabs import voices, generate, set_api_key
from aiohttp import ClientSession
import asyncio
from pydub import AudioSegment
import io
from typing import Optional


client = instructor.patch(OpenAI())


class PodcastSectionOverview(BaseModel):
    section_length_in_mins: int 
    section_description: str = Field(..., description="List of high level episode content.")
    section_sound_effect_into: Optional[str] = Field(..., description="An optional sound effect to play between the last section and this section")


class PodcastSection(BaseModel):
    episode_length_in_mins: int
    episode_transcript: str    


class PodcastOverview(BaseModel):
    title: str
    description: str
    podcast_length_in_mins: int
    description_of_episode_cover_image: str
    sections: list[PodcastSectionOverview]


def get_podcast_overview(input_text, podcast_length) -> PodcastOverview:
    prompt = f"""
You are a podcast host that has been asked to produce a podcast on {input_text} to your audience.
The podcast should be about {podcast_length} minutes long.

Write a outline of the podcast, consisting of several sections.
Each section will be read one after the other as a continues transcript.

Provide the title of the podcast, the description of the podcast, a high-level summary of the podcast,
a visual description of the podcast cover image and describe the high level content for each section.
"""
    print(f"Prompt: {prompt}")
    overview: PodcastOverview = client.chat.completions.create(
        model="gpt-4-1106-preview",
        response_model=PodcastOverview,
        messages=[
            {"role": "user", "content": prompt},
        ],
    )
    print(f"Overview: {overview}")
    return overview


def get_podcast_section(
    podcast_overview: PodcastOverview, section: PodcastSectionOverview
) -> PodcastSection:
    """Generate a podcast section from a podcast overview."""
    prompt = f"""
You are a podcast host that is explaining {podcast_overview.title} to your audience.
The podcast is about {podcast_overview.description}.

The podcast has the following episodes: 
{[s.description for s in podcast_overview.sections]}

You are now writing the detailed transcript for the section {section.description} of the podcast.

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


class Podcast(PodcastOverview):
    transcript: str


def get_podcast(input_text: str, podcast_length: int) -> PodcastOverview:
    podcast_overview: PodcastOverview = get_podcast_overview(input_text, podcast_length)
    podcast: Podcast = Podcast(**podcast_overview.dict(), transcript="")
    # sections = await asyncio.gather(
    #     *[
    #         get_podcast_section(podcast_overview, episode)
    #         for episode in podcast_overview.episodes
    #     ]
    # )
    for section in podcast_overview.sections:
        section = get_podcast_section(podcast_overview, section)
        podcast.transcript += "\n\n" + section.episode_transcript

    return podcast


def get_podcast_image(cover_image_description: str) -> str:
    """Generate a podcast cover image from a description of the image."""
    return "https://www.google.com/url?sa=i&url=https%3A%2F%2Funsplash.com%2Fs%2Fphotos%2Fnatural&psig=AOvVaw1j_-1b18H9E8vIIJXnVbGE&ust=1700202091318000&source=images&cd=vfe&ved=0CBIQjRxqFwoTCKichsDwx4IDFQAAAAAdAAAAABAE"


def text_2_speech(prompt, voice):
    audio_path = f"temp.mp3"
    print(f"Generating audio for voice {voice}, to file {audio_path}")

    # split prompt into chunks less than 5000 characters
    chunks = [prompt[i : i + 4950] for i in range(0, len(prompt), 4950)]

    concatenated_audio = AudioSegment.empty()  # Creating an empty audio segment
    for chunk in chunks:
        chunk_audio = generate(text=chunk, voice=voice, model="eleven_multilingual_v2")
        # Assuming that the generate function represents mp3
        audio_segment = AudioSegment.from_mp3(io.BytesIO(chunk_audio))
        concatenated_audio += audio_segment

    # Export concatenated audio to a file
    concatenated_audio.export(audio_path, format="mp3")

    # Get raw audio bytes to return
    buffer = io.BytesIO()
    concatenated_audio.export(buffer, format="mp3")
    raw_audio_bytes = buffer.getvalue()

    return audio_path, raw_audio_bytes
