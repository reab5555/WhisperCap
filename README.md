<p align="left">
  <img src="/speech2text.png" alt="Alt text for image1" width="155"/>
</p>

# WhisperCap
This tool uses OpenAI's Whisper model to transcribe video and audio files and create subtitles. it support many languages and can automatically determine the video or audio file spoken language.

## Description
The Whisper model is an automatic speech recognition system developed by OpenAI, designed to transcribe spoken language into text. It is capable of handling a wide range of audio inputs, including noisy environments, multiple speakers, and various accents and languages. Additionally, Whisper can be used to create subtitles for videos, making it accessible for content creators and media professionals to automatically generate accurate text for spoken dialogue. This model leverages deep learning techniques to improve its transcription accuracy and adaptability across different audio conditions and speech variations. this tool saves a text file with the transcription and an srt captions file with timecodes in the same folder of the loaded video or audio file.

## Requirments
A unique API key must be set in the script in order to transcribe files. please refer to https://platform.openai.com/api-keys.    
set it in the script where: api_key = "API_KEY_HERE"
