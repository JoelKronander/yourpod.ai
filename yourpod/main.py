import streamlit as st
import datetime
import asyncio
from elevenlabs import clone, voices, set_api_key
from tempfile import NamedTemporaryFile

import generate
import content

st.set_page_config(
    page_title="YourPod.ai",
    page_icon="🎙",
    layout="centered",
    initial_sidebar_state="auto",
)


def initialize_session():
    keys = ['session_id', 'openai_api_key', 'elevenlabs_api_key',
            'openai_voice', 'elevenlabs_voice', 'voice_cloning_temp_file', 'podcast_length']
    for key in keys:
        if key not in st.session_state:
            st.session_state[key] = None


initialize_session()

st.title("YourPod.ai")

# Sidebar controls
openai_api_key = st.sidebar.text_input("OpenAI API Key")
if openai_api_key.startswith("sk-"):
    st.session_state.openai_api_key = openai_api_key
    st.session_state.podcast_length = st.sidebar.slider(
        "How long would you like the podcast to be? (mins)", 2, 25, 5
    )
    st.session_state.openai_voice = st.sidebar.selectbox(
        "Pick your OpenAI podcast host voice.", ["alloy", "echo", "fable", "onyx", "nova", "shimmer"], index=5
    )
else:
    st.sidebar.warning("Please enter your Open AI key", icon="⚠️")

elevenlabs_api_key = st.sidebar.text_input("Elevenlabs API Key")
if elevenlabs_api_key:
    st.session_state.elevenlabs_api_key = elevenlabs_api_key
    set_api_key(elevenlabs_api_key)
    voice_cloning = st.sidebar.checkbox("Voice cloning")
    if voice_cloning:
        voice_cloning_file = st.sidebar.file_uploader(
            "Upload an audio file to clone the voice from.", type=["wav"]
        )
        if voice_cloning_file:
            with NamedTemporaryFile(suffix=".mp3", delete=True) as temp_file:
                temp_file_name = temp_file.name  # Get the file path
                with open(temp_file_name, "wb") as f:
                    f.write(voice_cloning_file.read())
                st.session_state.elevenlabs_voice = clone(
                    name="my_generated_voice_" + str(datetime.datetime.now()),
                    description="Custom voice",
                    files=[temp_file_name],
                )
    else:
        st.session_state.elevenlabs_voice = st.sidebar.selectbox(
            "Pick your podcast host voice.", [v.name for v in voices()]
        )
else:
    st.sidebar.warning("Please enter your Elevenlabs API key for more custom voices and voice cloning.", icon="⚠️")

# Main window
with st.form("my_form"):
    text = st.text_area("Create a podcast about...", content.get_random_wikipedia_article_title())
    submitted = st.form_submit_button("Generate")
    # Example texts (optional)

    if submitted:
        if not st.session_state.openai_api_key:
            st.warning("Please enter your OpenAI API key!", icon="⚠️")
        else:
            st.success("Generating podcast... This can take a few minutes.", icon="🎙")
            with st.spinner('Wait for it...'):
                input_text = text
                podcast_overview = generate.get_podcast_overview(input_text, st.session_state.podcast_length,
                                                                 openai_api_key=st.session_state.openai_api_key)
                st.success(
                    f"Outline Done! -- Title: {podcast_overview.title} -- Sections To Generate: {len(podcast_overview.section_overviews)}",
                    icon="✅")
                podcast = generate.Podcast(**podcast_overview.dict(), length_in_minutes=0, transcript="", sections=[])
                bar = st.progress(0, text="Generating sections...")
                for nr, section_overview in enumerate(podcast_overview.section_overviews):
                    bar.progress((nr + 1) / len(podcast_overview.section_overviews),
                                 text=f"Generating section {nr + 1}/{len(podcast_overview.section_overviews)}...")
                    section = generate.get_podcast_section(podcast_overview, section_overview, podcast,
                                                           desired_length=st.session_state.podcast_length,
                                                           openai_api_key=st.session_state.openai_api_key)
                    if nr > 0 and section.sound_effect_intro:
                        podcast.transcript += "\n\n" + f"[{section.sound_effect_intro}]"
                    podcast.transcript += "\n\n" + section.transcript
                    podcast.length_in_minutes += section.length_in_seconds / 60
                    podcast.sections.append(section)
            st.success("Transcript Done!", icon="✅")
            st.info(podcast.transcript)

            with st.spinner('Generating Audio...'):
                if st.session_state.elevenlabs_voice:
                    audio = generate.text_2_speech(podcast.transcript, st.session_state.elevenlabs_voice)
                else:
                    # Use openai voice
                    audio = asyncio.run(generate.text_2_speech_openai(podcast, st.session_state.openai_voice,
                                                                      openai_api_key=st.session_state.openai_api_key))
            st.audio(audio)