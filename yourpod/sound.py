from pydub import AudioSegment
import replicate
import os
import io
import requests
import logging
from contextlib import contextmanager
from tempfile import NamedTemporaryFile
from typing import List, Tuple, Optional
import asyncio
from yourpod.decorators import timing_decorator
from yourpod.exceptions import AudioError, RateLimitError
from yourpod.models import Podcast
from elevenlabs import generate as elevenlabs_generate
from tenacity import retry, stop_after_attempt, wait_exponential
from yourpod.transcript import parse_transcript_segments

# Set up logging
logger = logging.getLogger(__name__)

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
    buffer = io.BytesIO()
    audio_segment.export(buffer, format="mp3")
    return buffer.getvalue()

@contextmanager
def temp_audio_file(suffix=".mp3"):
    """Context manager for temporary audio files"""
    temp_path = None
    try:
        with NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            temp_path = temp_file.name
            yield temp_path
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

def save_audio_file(audio_data: bytes, prefix: str = "podcast") -> str:
    """Save audio data to a temporary file and return the path"""
    with NamedTemporaryFile(prefix=prefix, suffix=".mp3", delete=False) as temp_file:
        temp_file.write(audio_data)
        return temp_file.name

@timing_decorator
async def generate_audio_segments_async(text_segments: List[Tuple[str, str]], voice_map: dict) -> List[bytes]:
    """Generate audio segments in parallel"""
    async def generate_segment(text: str, voice: str) -> bytes:
        try:
            return await text_2_speech_elevenlabs_async(text, voice)
        except Exception as e:
            logger.error(f"Error generating segment: {str(e)}")
            raise

    # Process segments in parallel batches
    BATCH_SIZE = 5  # Adjust based on API limits
    results = []
    
    for i in range(0, len(text_segments), BATCH_SIZE):
        batch = text_segments[i:i + BATCH_SIZE]
        batch_tasks = [
            generate_segment(text, voice_map[speaker])
            for text, speaker in batch
        ]
        
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        # Handle any errors in the batch
        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"Batch processing error: {result}")
                continue
            results.append(result)
            
        # Add small delay between batches to avoid rate limits
        if i + BATCH_SIZE < len(text_segments):
            await asyncio.sleep(1)
    
    return results

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
@timing_decorator
async def text_2_speech_elevenlabs_async(text: str, voice: str) -> bytes:
    """Async wrapper for elevenlabs generation with retries."""
    try:
        audio = elevenlabs_generate(text=text, voice=voice, model="eleven_multilingual_v2")
        return audio
    except Exception as e:
        if "rate limit" in str(e).lower():
            raise RateLimitError("ElevenLabs API rate limit exceeded")
        logger.error(f"Error generating audio: {str(e)}")
        raise

@timing_decorator
async def generate_background_music(prompt: str) -> Optional[AudioSegment]:
    """
    Generate background music using Replicate's Stable Audio model
    
    Args:
        prompt: Text description of the desired music
        
    Returns:
        AudioSegment if successful, None if failed
    """
    try:
        # Run the Stable Audio model
        output = replicate.run(
            "stackadoc/stable-audio-open-1.0:9aff84a639f96d0f7e6081cdea002d15133d0043727f849c40abdd166b7c75a8",
            input={"prompt": prompt}
        )
        
        # Download and convert to AudioSegment
        response = requests.get(output)
        audio = AudioSegment.from_file(io.BytesIO(response.content), format="wav")
        return audio.fade_in(1000).fade_out(1000)
        
    except Exception as e:
        logger.error(f"Error generating background music: {e}")
        return None

@timing_decorator
async def generate_transition_effect(style: str) -> Optional[AudioSegment]:
    """Generate transition sound effect based on podcast style"""
    style_effect_map = {
        "Interview": "short subtle transition whoosh",
        "News Report": "professional news transition sound",
        "Story Narrative": "storytelling transition sound effect",
        "Comedy Podcast": "playful transition sound effect",
    }
    
    prompt = style_effect_map.get(style, "short subtle podcast transition sound")
    try:
        output = replicate.run(
            "stackadoc/stable-audio-open-1.0:9aff84a639f96d0f7e6081cdea002d15133d0043727f849c40abdd166b7c75a8",
            input={
                "prompt": prompt,
                "duration": 2,
            }
        )
        
        response = requests.get(output)
        audio = AudioSegment.from_file(io.BytesIO(response.content), format="wav")
        return audio.fade_in(200).fade_out(200)
    except Exception as e:
        logger.error(f"Error generating transition effect: {e}")
        return None

@timing_decorator
async def text_2_speech_elevenlabs_improved(
    podcast: Podcast,
    host_voice: str,
    guest_voice: str,
    add_effects: bool = False
) -> bytes:
    """Generate audio for the podcast"""
    try:
        # Parse transcript into segments
        segments = parse_transcript_segments(podcast.transcript)
        voice_map = {'host': host_voice, 'guest': guest_voice}
        
        # Generate audio for each segment
        audio_segments = []
        for text, speaker in segments:
            audio = elevenlabs_generate(
                text=text,
                voice=voice_map[speaker],
                model="eleven_multilingual_v2"
            )
            audio_segments.append(audio)
            
        # Combine segments into one audio stream
        combined_audio = b''.join(audio_segments)
        
        # Convert to AudioSegment for basic processing
        audio_segment = AudioSegment.from_mp3(io.BytesIO(combined_audio))
        
        # Add simple fade effects
        audio_segment = audio_segment.fade_in(1000).fade_out(1000)
        
        # Convert back to bytes
        buffer = io.BytesIO()
        audio_segment.export(buffer, format="mp3")
        return buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Error generating audio: {str(e)}")
        raise AudioError(f"Failed to generate audio: {str(e)}")

async def generate_sound_effects(podcast: Podcast) -> List[AudioSegment]:
    """Generate sound effects in parallel"""
    effect_prompts = [
        section.sound_effect for section in podcast.section_overviews 
        if hasattr(section, 'sound_effect') and section.sound_effect
    ]
    
    if not effect_prompts:
        return []
        
    effects = await asyncio.gather(*[
        asyncio.to_thread(generate_sound, prompt)
        for prompt in effect_prompts
    ])
    
    return effects

def combine_audio_with_effects(
    main_audio: AudioSegment,
    effects: List[AudioSegment],
    fade_duration: int = 1000
) -> AudioSegment:
    """Combine main audio with sound effects"""
    result = main_audio
    
    if not effects:
        return result.fade_in(fade_duration).fade_out(fade_duration)
        
    segment_length = len(result) / (len(effects) + 1)
    
    for i, effect in enumerate(effects):
        position = int(segment_length * (i + 1))
        result = result.overlay(effect, position=position)
    
    return result.fade_in(fade_duration).fade_out(fade_duration)