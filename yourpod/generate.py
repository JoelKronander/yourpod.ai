from openai import OpenAI
import logging
from yourpod.decorators import timing_decorator
from yourpod.models import Podcast, PodcastAudioConfig
from pydantic import BaseModel, Field
from typing import List
from elevenlabs import Voice, voices

logger = logging.getLogger(__name__)

GPT_MODEL = "gpt-4o-2024-08-06"

class PodcastContent(BaseModel):
    """Schema for the podcast content generation"""
    title: str = Field(..., description="A catchy, engaging podcast title")
    description: str = Field(..., description="A compelling episode description")
    transcript: str = Field(..., description="Natural conversation using Host: and Guest: prefixes")

def get_voice_gender(voice_name: str) -> str:
    """Get the gender of a voice from ElevenLabs"""
    try:
        available_voices = voices()
        voice = next((v for v in available_voices if v.name == voice_name), None)
        if voice:
            # ElevenLabs voices have labels that can indicate gender
            labels = voice.labels if hasattr(voice, 'labels') else {}
            gender = labels.get('gender', 'neutral')
            return gender.lower()
    except Exception as e:
        logger.error(f"Error getting voice gender: {e}")
    return 'neutral'

@timing_decorator
async def generate_podcast_async(
    topic: str, 
    podcast_length: int, 
    openai_api_key: str, 
    style: str = "Interview",
    tone: str = "Balanced",
    key_points: str | None = None,
    host_voice: str | None = None,
    guest_voice: str | None = None
) -> Podcast:
    """Generate a complete podcast."""
    try:
        client = OpenAI(api_key=openai_api_key)
        
        # Get voice genders
        host_gender = get_voice_gender(host_voice) if host_voice else 'neutral'
        guest_gender = get_voice_gender(guest_voice) if guest_voice else 'neutral'
        
        # Add gender information to the prompt
        content_prompt = "\n".join([
            "You are a podcast script generator. Generate a podcast script with the following details:",
            "",
            f"Topic: {topic}",
            f"Length: {podcast_length} minutes",
            f"Style: {style}",
            f"Tone: {tone}",
            f"Host Gender: {host_gender}",
            f"Guest Gender: {guest_gender}",
            "",
            "Instructions:",
            "1. Generate a natural conversation between a host and guest",
            "2. Include vocal cues like (laughs), (thoughtful pause) where appropriate",
            "3. Format the transcript with 'Host:' and 'Guest:' prefixes",
            "4. Make the conversation engaging with:",
            "   - A strong opening hook",
            "   - Natural back-and-forth dialogue",
            "   - A memorable conclusion",
            "5. Ensure the dialogue matches the specified genders:",
            f"   - Write the host's lines to match a {host_gender} voice",
            f"   - Write the guest's lines to match a {guest_gender} voice",
            "6. Use gender-appropriate language and references"
        ])

        completion = client.beta.chat.completions.parse(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": "You are a podcast script generator."},
                {"role": "user", "content": content_prompt}
            ],
            response_format=PodcastContent,
            temperature=0.7,
        )

        content = completion.choices[0].message.parsed
        
        audio_config = PodcastAudioConfig(
            volume_level=-20 if style == "Interview" else -25
        )
        
        return Podcast(
            title=content.title,
            description=content.description,
            transcript=content.transcript,
            length_in_minutes=podcast_length,
            style=style,
            audio_config=audio_config
        )

    except Exception as e:
        logger.error(f"Error generating podcast: {str(e)}")
        raise




