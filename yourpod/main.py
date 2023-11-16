import streamlit as st
import datetime
import requests
import generate
from elevenlabs import clone, voices, set_api_key
import asyncio

st.title("YourPod.ai")

## Sidebar controls
# Add a selectbox to the sidebar:
elevenlabs_api_key = st.sidebar.text_input("Elevenlabs API Key")
openai_api_key = st.sidebar.text_input("OpenAI API Key")
if not elevenlabs_api_key:
    st.sidebar.warning("Please enter your Elevenlabs API key!", icon="⚠")
else:
    set_api_key(elevenlabs_api_key)
    # voice cloning
    voice_cloning = st.sidebar.checkbox("Voice cloning")
    if voice_cloning:
        voice_cloning_file = st.sidebar.file_uploader(
            "Upload an audio file to clone the voice from.", type=["wav"]
        )
        if voice_cloning_file:
            # create a temp file from the uploaded file
            with open("temp.wav", "wb") as f:
                f.write(voice_cloning_file.read())
            voice = clone(
                name="my_generated_voice"+str(datetime.datetime.now()),
                description="Custom voice", # Optional
                files=['temp.wav'],
            )
    else:
        voice = st.sidebar.selectbox(
            "Pick your podcast host voice.", [v.name for v in voices()]
        )
    podcast_length = st.sidebar.slider(
        "How long would you like the podcast to be? (mins)", 1, 5, 1
    )

## Main window
with st.form("my_form"):
    text = st.text_area("What would you like to learn about?")
    submitted = st.form_submit_button("Submit")
    examples = st.text("Examples:")
    example1 = st.text("Bitcoin")
    example2 = st.text(
        "Travel adventures, focusing on hidden gems and unique travel experiences across the globe?"
    )
    example3 = st.text(
        "The future of work, focusing on the impact of automation and AI on the workforce?"
    )
    if not openai_api_key.startswith("sk-"):
        st.warning("Please enter your OpenAI API key!", icon="⚠")
    if submitted and openai_api_key.startswith("sk-"):
        st.success("Generating podcast... This can take a few minutes.", icon="🎙")
        podcast = generate.get_podcast(text, podcast_length)
        st.info(podcast.transcript)

        cover_image_url = generate.get_podcast_image(
            podcast.description_of_episode_cover_image
        )
        st.image(cover_image_url, caption="Cover image", use_column_width=True)

        _, audio = generate.text_2_speech(podcast.transcript, voice)
        st.audio(audio)


upload = st.button("Upload to Buzzsprout")
if upload:
    # upload audio to buzzsprout
    # docs
    #     POST /episodes.json will create a new episode with the included parameters.
    # {
    #   "title":"Too many or too few?",
    #   "description":"",
    #   "summary":"",
    #   "artist":"Muffin Man",
    #   "tags":"",
    #   "published_at":"2019-09-12T03:00:00.000-04:00",
    #   "duration":23462,
    #   "guid":"Buzzsprout788880",
    #   "inactive_at":null,
    #   "episode_number":4,
    #   "season_number":5,
    #   "explicit":true,
    #   "private":true,
    #   "email_user_after_audio_processed": true,
    #   "audio_url": "https://www.google.com/my_audio_file.mp4",
    #   "artwork_url": "https://www.google.com/my_artwork_file.jpeg"
    # }
    BUZZSPROUT_API_TOKEN = "828bd25a81bce931c25885586cfa6ce8"

    url = "https://www.buzzsprout.com/api/episodes"
    payload = {
        "title": "Test 1",
        "description": text,
        "summary": text,
        "artist": "GPT4",
        "published_at": datetime.datetime.now(),
        "guid": "Buzzsprout788880",
        "inactive_at": None,
        "episode_number": 1,
        "season_number": 1,
        "explicit": True,
        "private": True,
        "audio_file": audio,
        "artwork_url": "https://www.google.com/my_artwork_file.jpeg",
    }
    # Define the headers
    headers = {
        "Authorization": f"Token token={BUZZSPROUT_API_TOKEN}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, headers=headers, data=payload)

    # Check the response
    if response.status_code == 201:
        print("Episode uploaded successfully!")
    else:
        print(f"Failed to upload episode. Status code: {response.status_code}")
        print(f"Response: {response.text}")
