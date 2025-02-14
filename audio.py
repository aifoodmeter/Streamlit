import streamlit as st
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import openai
from tempfile import NamedTemporaryFile

def record_audio(duration=5, sample_rate=44100):
    """Record audio from microphone"""
    recording = sd.rec(int(duration * sample_rate),
                      samplerate=sample_rate,
                      channels=1,
                      dtype=np.int16)
    st.info("Recording...")
    sd.wait()
    st.success("Recording complete!")
    return recording, sample_rate

def save_audio(recording, sample_rate):
    """Save the recording to a temporary WAV file"""
    with NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
        wav.write(temp_audio.name, sample_rate, recording)
        return temp_audio.name

def transcribe_audio(audio_file_path, api_key):
    """Transcribe audio using OpenAI's API with forced English language"""
    client = openai.OpenAI(api_key=api_key)
    
    with open(audio_file_path, 'rb') as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="en",
            prompt="Please transcribe this audio in English only."
        )
    return transcript.text

