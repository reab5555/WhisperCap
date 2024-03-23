

# WhisperCap
This tool uses Whisper model to transcribe video and audio files and create subtitles. it supports many languages and can automatically determine the video or audio file spoken language.

<p align="left">
  <img src="/speech2text.png" alt="Alt text for image1" width="155"/>
</p>

## Description
The Whisper model is an automatic speech recognition system developed by OpenAI, designed to transcribe spoken language into text. It is capable of handling a wide range of audio inputs, including noisy environments, multiple speakers, and various accents and languages. Additionally, Whisper can be used to create subtitles for videos, making it accessible for content creators and media professionals to automatically generate accurate text for spoken dialogue. This model leverages deep learning techniques to improve its transcription accuracy and adaptability across different audio conditions and speech variations. this tool saves a text file with the transcription and an srt captions file with timecodes in the same folder of the loaded video or audio file.   

The main advantage of this tool is the ability to bypass the limitation of the transcription time, so video or audio files that are even about an hour long can be transcribed. furthermore, it almost completely eliminates the need for a human to transcribe videos for the example, which saves a lot of time and money when you want to transcribe videos or lectures accurately and efficiently. 

The tool has already been widely used in professional work environments for academic and non-academic needs, for example, re-transcribing lectures in different languages.

### Remarks
* We recommend to go through the transcribed text to check that it is in fact correct.      
* It uses the model and sends a request to the server twice, once for exporting text and once for exporting subtitles, so this should be taken into account.
* Processing time may vary depending on the size and duration of the video or audio file, network stability and availability.
  
## Requirements
* A unique API key must be set in the script in order to transcribe files. please refer to https://platform.openai.com/api-keys.    
set it in the script where: api_key = "API_KEY_HERE"
* Make sure the following packages are installed, and if not:   
pip install openai   
pip install moviepy

