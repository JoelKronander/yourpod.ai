import streamlit as st
import asyncio
from pydub import AudioSegment

import generate
from sound import generate_sound
from utils import initialize_session


st.set_page_config(
    page_title="YourPod.ai",
    page_icon="🎙",
    layout="centered",
    initial_sidebar_state="auto",
)
st.title("YourPod.ai")

initialize_session()

# Main window
with st.form("yourpod_form"):
    topic = st.text_area("Create a podcast about...", placeholder=st.session_state['random_default_topic'])
    if topic is None or topic == "":
        topic = st.session_state['random_default_topic']

    submitted = st.form_submit_button("Generate")

    if submitted:
        if not st.session_state.openai_api_key:
            st.warning("Please enter your OpenAI API key!", icon="⚠️")
        else:
            st.success("Generating podcast... This can take a few minutes.", icon="🎙")
            with st.spinner('Wait for it...'):
                podcast_overview = generate.get_podcast_overview(topic,
                                                                 st.session_state.podcast_length,
                                                                 openai_api_key=st.session_state.openai_api_key)
                st.success(f"Outline Done! -- Title: {podcast_overview.title} -- Sections To Generate: {len(podcast_overview.section_overviews)}", icon="✅")


                st.success("Generating main podcast content...", icon="📖")
                podcast = generate.Podcast(**podcast_overview.model_dump(),
                                           length_in_minutes=0,
                                           transcript="",
                                           sections=[],
                                           sounds=[])

                bar = st.progress(0, text="Generating sections...")
                for nr, section_overview in enumerate(podcast_overview.section_overviews):
                    bar.progress((nr+1)/len(podcast_overview.section_overviews), text=f"Generating section {nr+1}/{len(podcast_overview.section_overviews)}...")
                    section = generate.get_podcast_section(podcast_overview, section_overview, podcast, desired_length=st.session_state.podcast_length, openai_api_key=st.session_state.openai_api_key)

                    podcast.transcript += "\n\n" + section.transcript
                    podcast.length_in_minutes += section.length_in_seconds / 60
                    podcast.sections.append(section)

                st.success("Transcript Done!", icon="✅")
                st.info(podcast.transcript)

                with st.spinner('Generating Sounds...'):
                    for section_overview in podcast_overview.section_overviews:
                        if st.session_state.replicate_api_key and section_overview.sound_effect_prompt != None:
                            print("\nSound prompt: ", section_overview.sound_effect_prompt)
                            section_sound = generate_sound(section_overview.sound_effect_prompt)
                            podcast.sounds.append(section_sound)
                st.success("Sounds Done!", icon="🎷")

                with st.spinner('Generating Audio...'):
                    if st.session_state.elevenlabs_voice:
                        audio = generate.text_2_speech_elevenlabs(podcast, st.session_state.elevenlabs_voice)
                    else:
                        # Use openai voice
                        audio = asyncio.run(generate.text_2_speech_openai(podcast,
                                                                        st.session_state.openai_voice,
                                                                        openai_api_key=st.session_state.openai_api_key))
                st.success("Audio Done!", icon="🔊")
            
            st.success("Podcast Done!", icon="🎧")
            st.audio(audio)

