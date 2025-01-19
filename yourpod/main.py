import streamlit as st
from typing import Optional
from pydantic import BaseModel
import base64
from elevenlabs import voices, generate as elevenlabs_generate
import asyncio
import logging

import yourpod.generate as generate
from yourpod.utils import initialize_session
from yourpod.sound import text_2_speech_elevenlabs_improved
from yourpod.models import Podcast

# Set up logging
logger = logging.getLogger(__name__)

class PodcastGenerationState(BaseModel):
    """Tracks the state of podcast generation."""
    is_generating: bool = False
    current_section: int = 0
    total_sections: int = 0
    stage: str = ""

def get_binary_file_downloader_html(bin_data, file_label='File'):
    """Generate HTML code for file download link"""
    b64 = base64.b64encode(bin_data).decode()
    return f'<a href="data:application/octet-stream;base64,{b64}" download="{file_label}.mp3">Download {file_label}</a>'

def validate_input(topic: str) -> tuple[bool, str]:
    """Validate user input"""
    if not topic.strip():
        return False, "Topic cannot be empty"
    if len(topic) > 500:
        return False, "Topic is too long (max 500 characters)"
    return True, ""

async def generate_podcast_with_audio(
    topic: str,
    podcast_length: int,
    openai_api_key: str,
    podcast_style: str,
    tone: str,
    key_points: Optional[str],
    host_voice: str,
    guest_voice: str,
    add_effects: bool
) -> tuple[Podcast, bytes]:
    """Async function to generate podcast content and audio"""
    # Generate podcast content
    podcast = await generate.generate_podcast_async(
        topic,
        podcast_length,
        openai_api_key,
        style=podcast_style,
        tone=tone,
        key_points=key_points
    )
    
    # Generate audio
    audio = await text_2_speech_elevenlabs_improved(
        podcast,
        host_voice=host_voice,
        guest_voice=guest_voice,
        add_effects=add_effects
    )
    
    return podcast, audio

def main():
    st.set_page_config(
        page_title="YourPod.ai",
        page_icon="🎙",
        layout="centered",
        initial_sidebar_state="expanded",
    )
    
    # Clean header
    st.title("🎙️ YourPod.ai")
    st.markdown("##### Create AI-powered podcasts on any topic")
    
    initialize_session()

    # Organize sidebar into clear sections
    with st.sidebar:
        st.subheader("⚙️ Podcast Settings")
        
        # Core settings in an expander
        with st.expander("Content Settings", expanded=True):
            st.session_state.podcast_style = st.selectbox(
                "Format",
                [
                    "Casual Deep Dive",
                    "Interview",
                    "Solo Host",
                    "News Report",
                    "Educational",
                    "Story Narrative",
                    "Comedy Podcast",
                    "Debate Style"
                ],
                help="Select the style/format of your podcast"
            )
            
            st.session_state.conversation_depth = st.select_slider(
                "Conversation Depth",
                options=["Light", "Moderate", "Deep Dive"],
                value="Moderate",
                help="Choose how deep the conversation should go into topics"
            )
            
            st.session_state.controversy_level = st.select_slider(
                "Controversy Level",
                options=["Safe", "Balanced", "Spicy"],
                value="Balanced",
                help="Choose how controversial the takes should be"
            )
            
            st.session_state.tone = st.select_slider(
                "Tone",
                options=["Formal", "Balanced", "Casual"],
                value="Balanced",
                help="Choose how formal or casual the conversation should be"
            )

            st.session_state.podcast_length = st.slider(
                "Length (minutes)",
                min_value=1,
                max_value=10,
                value=3,
                help="Choose the approximate length of your podcast"
            )
        
        # Voice settings in a separate expander
        if st.session_state.elevenlabs_api_key:
            with st.expander("Voice Settings", expanded=True):
                available_voices = [v.name for v in voices()]
                
                st.session_state.host_voice = st.selectbox(
                    "Host Voice",
                    available_voices,
                    index=0,
                    key="host_voice_select"
                )
                
                st.session_state.guest_voice = st.selectbox(
                    "Guest Voice",
                    available_voices,
                    index=min(1, len(available_voices)-1),
                    key="guest_voice_select"
                )
        else:
            st.warning("Enter your Elevenlabs API key to select voices", icon="⚠️")

    # Main content area
    with st.form("yourpod_form"):
        topic = st.text_area(
            "What would you like to create a podcast about?",
            placeholder=st.session_state['random_default_topic'],
            help="Enter your topic or click Generate to use the example topic"
        ) or st.session_state['random_default_topic']
        
        # Advanced options in an expander
        with st.expander("Advanced Options"):
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.include_intro = st.checkbox(
                    "Include Intro/Outro",
                    value=True,
                    help="Add professional podcast introduction and conclusion"
                )
            with col2:
                st.session_state.add_sound_effects = st.checkbox(
                    "Add Sound Effects",
                    value=True,
                    help="Include subtle background music and transitions"
                )
            
            st.session_state.key_points = st.text_area(
                "Key Points (Optional)",
                placeholder="Enter specific points to cover (one per line)",
                help="Leave blank for AI to determine the content structure"
            )

        # Center the generate button and make it prominent
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            generate_button = st.form_submit_button(
                "🎙️ Generate Podcast",
                use_container_width=True,
                type="primary"
            )
        
        if generate_button:
            is_valid, error_msg = validate_input(topic)
            if not is_valid:
                st.error(error_msg)
                return
            
            if not st.session_state.openai_api_key:
                st.warning("Please enter your OpenAI API key!", icon="⚠️")
                return
            if not st.session_state.elevenlabs_api_key:
                st.warning("Please enter your ElevenLabs API key!", icon="⚠️")
                return

            state = PodcastGenerationState()
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Generate podcast content
            state.stage = "Creating podcast content"
            status_text.text(state.stage)
            progress_bar.progress(20)
            
            try:
                async def run_generation():
                    podcast = await generate.generate_podcast_async(
                        topic,
                        st.session_state.podcast_length,
                        st.session_state.openai_api_key,
                        style=st.session_state.podcast_style,
                        tone=st.session_state.tone,
                        key_points=st.session_state.key_points
                    )
                    
                    progress_bar.progress(60)
                    st.success(f"Content generated: {podcast.title}", icon="✅")
                    
                    # Generate audio
                    state.stage = "Creating audio"
                    status_text.text(state.stage)
                    progress_bar.progress(80)
                    
                    audio = await text_2_speech_elevenlabs_improved(
                        podcast,
                        host_voice=st.session_state.host_voice,
                        guest_voice=st.session_state.guest_voice,
                        add_effects=st.session_state.add_sound_effects
                    )
                    
                    return podcast, audio

                # Run the async operations
                podcast, audio = asyncio.run(run_generation())
                
                progress_bar.progress(100)
                status_text.text("Podcast complete!")
                
                if audio:
                    st.audio(audio)
                    st.markdown(
                        get_binary_file_downloader_html(
                            audio, 
                            podcast.title.replace(" ", "_").lower()
                        ),
                        unsafe_allow_html=True
                    )
            except Exception as e:
                st.error(f"Error generating podcast: {str(e)}")
                logger.error(f"Error in podcast generation: {str(e)}")

if __name__ == "__main__":
    main()

