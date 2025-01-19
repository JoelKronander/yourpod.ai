from openai import OpenAI
import logging
from yourpod.decorators import timing_decorator
from yourpod.models import Podcast
from pydantic import BaseModel, Field
from typing import List

logger = logging.getLogger(__name__)

GPT_MODEL = "gpt-4o-2024-08-06"

class PodcastContent(BaseModel):
    """Schema for the podcast content generation"""
    title: str = Field(..., description="A catchy, engaging podcast title")
    description: str = Field(..., description="A compelling episode description")
    transcript: str = Field(..., description="Natural conversation using Host: and Guest: prefixes")

@timing_decorator
async def generate_podcast_async(
    topic: str, 
    podcast_length: int, 
    openai_api_key: str, 
    style: str = "Interview",
    tone: str = "Balanced",
    key_points: str | None = None
) -> Podcast:
    """Generate a complete podcast."""
    try:
        client = OpenAI(api_key=openai_api_key)
        
        content_prompt = "\n".join([
            "You are a podcast script generator. Generate a podcast script with the following details:",
            "",
            f"Topic: {topic}",
            f"Length: {podcast_length} minutes",
            f"Style: {style}",
            f"Tone: {tone}",
            f"Key points: {key_points if key_points else 'Choose engaging angles'}",
            "",
            "Instructions:",
            "1. Generate a natural conversation between a host and guest",
            "2. Include vocal cues like (laughs), (thoughtful pause) where appropriate",
            "3. Format the transcript with 'Host:' and 'Guest:' prefixes",
            "4. Make the conversation engaging with:",
            "   - A strong opening hook",
            "   - Specific examples and data points",
            "   - Natural back-and-forth dialogue",
            "   - Clear key insights",
            "   - A memorable conclusion"
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

        # Access the parsed content directly
        content = completion.choices[0].message.parsed
        
        return Podcast(
            title=content.title,
            description=content.description,
            transcript=content.transcript,
            length_in_minutes=podcast_length
        )

    except Exception as e:
        logger.error(f"Error generating podcast: {str(e)}")
        raise




