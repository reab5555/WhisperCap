import re
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import os
import math
import srt
import csv
from openai import OpenAI
from moviepy.editor import *

import datetime
from tqdm import tqdm




# Initialize OpenAI API
api_key = "API_KEY_HERE"

client = OpenAI(api_key=api_key)

print('******** OpenAI Whisper Speech2Text - txt + srt - by REA.B ********')

# Set up the file dialog to select the input video or audio file
print('Please select .mp4, .wav, or .mp3 file...')
root = tk.Tk()
root.withdraw()
root.attributes("-top", True)
# Allow selection of .mp4 (video files), and .wav, .mp3 (audio files)
file_path = filedialog.askopenfilename(filetypes=[("Media files", "*.mp4;*.wav;*.mp3")])
root.destroy()

# Determine the file type
file_extension = os.path.splitext(file_path)[1].lower()

# Initialize variables for duration and chunk processing
video_duration = 0
n_chunks = 0

# Handle different file types
if file_extension == '.mp4':
    video = VideoFileClip(file_path)
    video_duration = video.duration
elif file_extension in ['.wav', '.mp3']:
    # For wav and mp3 files, directly use them without extracting audio
    audio = AudioFileClip(file_path)  # Use AudioFileClip for audio files
    video_duration = audio.duration

# Create output folder
output_name = os.path.splitext(os.path.basename(file_path))[0]
output_folder = os.path.dirname(file_path)
output_folder_name = f"{output_name} - transcription data"
transcription_data_folder = os.path.join(output_folder, output_folder_name)
os.makedirs(transcription_data_folder, exist_ok=True)

# Split the media into 30-second chunks for processing
n_chunks = math.ceil(video_duration / 30)

# Transcribe the video or audio chunks
transcription_txt = ""
transcription_srt = ""
last_index = 0
time_offset = 0

for i in tqdm(range(n_chunks), desc='Transcribing Media to Text'):
    start = i * 30
    end = (i + 1) * 30 if i < n_chunks - 1 else video_duration  # Adjust the duration of the last chunk

    if file_extension == '.mp4':
        audio_chunk = video.subclip(start, end).audio
    elif file_extension in ['.wav', '.mp3']:
        audio_chunk = audio.subclip(start, end)

    audio_chunk.write_audiofile("temp_audio.wav", codec='pcm_s16le')

    with open("temp_audio.wav", "rb") as audio_file:
        response = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-1",
            response_format="text",
        )

    # Assuming the response is not always a dictionary and might be a string directly
    if isinstance(response, dict) and 'text' in response:
        transcription_text_part = response['text']
    elif isinstance(response, str):
        transcription_text_part = response
    else:
        # Handle unexpected response types, maybe log an error or throw an exception
        print("Unexpected response format from transcription service.")
        transcription_text_part = ""

    transcription_txt += transcription_text_part

    print(transcription_txt)

    # Save the transcription as a .txt file
    txt_file_path = os.path.join(transcription_data_folder, f"{output_name} - text.txt")
    with open(txt_file_path, "w", encoding='utf-8') as f:
        f.write(transcription_txt)

    # Transcribe to SRT
    # For SRT Transcription
    with open("temp_audio.wav", "rb") as audio_file:
        response_srt = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-1",
            response_format="srt",
        )

    # Directly use response_srt if it's already a string, which is expected for SRT content
    if isinstance(response_srt, str):
        srt_content = response_srt
    else:
        print("Unexpected SRT response format.")
        srt_content = ""

    # Parse and adjust the SRT content as needed
    segments_list = list(srt.parse(srt_content))
    for segment in segments_list:
        segment.index += last_index
        segment.start += datetime.timedelta(seconds=time_offset)
        segment.end += datetime.timedelta(seconds=time_offset)
        segment.start = segment.start - datetime.timedelta(microseconds=segment.start.microseconds)
        segment.end = segment.end - datetime.timedelta(microseconds=segment.end.microseconds)

    modified_srt = srt.compose(segments_list)
    transcription_srt += modified_srt
    last_index = segments_list[-1].index + 1
    time_offset += 30

    # Save the transcription as an .srt file
    srt_file_path = os.path.join(transcription_data_folder, f"{output_name}.srt")
    with open(srt_file_path, "w", encoding='utf-8') as f:
        f.write(transcription_srt)

# Cleanup
os.remove("temp_audio.wav")

print("**** All Done! ****")
