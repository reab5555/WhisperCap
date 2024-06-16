

# WhisperCap
This is a GUI based tool that uses Whisper model to transcribe video and audio files and create subtitles. it can transcribe even a hour-long files, and it supports many languages and can automatically determine the video or audio file spoken language.

<p align="left">
  <img src="/speech2text.png" alt="Alt text for image1" width="155"/>
</p>

## Description
### Whisper
The Whisper model is an automatic speech recognition system developed by OpenAI, designed to transcribe spoken language into text. It is capable of handling a wide range of audio inputs, including noisy environments, multiple speakers, and various accents and languages. Additionally, Whisper can be used to create subtitles for videos, making it accessible for content creators and media professionals to automatically generate accurate text for spoken dialogue. This model leverages deep learning techniques to improve its transcription accuracy and adaptability across different audio conditions and speech variations. this tool saves a text file with the transcription and an srt captions file with timecodes in the same folder of the loaded video or audio file.   

### Advantages of WhisperCap
* The main advantage of this tool is the ability to bypass the limitation of the transcription time by working in chunks, so video or audio files that are even about an hour long can be transcribed in almost any language.
* Based on a GUI, so it is easy and simple to transcribe files even for those who do not understand how a script works.
* It almost completely eliminates the need for a human to transcribe videos manually, which saves a lot of time and money when one wants to transcribe videos or lectures accurately and efficiently. 

Primarily developed for academic needs and universities with non-profit intentions, the tool has already been widely used in professional work environments for academic and non-academic needs, for example, re-transcribing lectures in different languages.   

### Remarks
* We recommend to go through the transcribed text to check that it is in fact correct.      
* It uses the model and sends a request to the server twice, once for exporting text and once for exporting subtitles, so this should be taken into account.
* Processing time may vary depending on the size and duration of the video or audio file, network or local computation stability and availability.
   
## Requirements
* Download ffmpeg package with the ffmpeg.exe from either https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-essentials.7z or https://github.com/GyanD/codexffmpeg/releases/tag/6.1.1
after downloading the ffmpeg package, ffmpeg.exe is found in "ffmpeg\bin\ffmpeg.exe" - place it in the script directory.
   
* Make sure the following packages are installed with:   
pip install openai   
pip install moviepy   
pip install PyQt6   
pip install srt
pip install transformers
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
