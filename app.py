import os
import math
import re
import gradio as gr
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
from moviepy.editor import VideoFileClip

def timestamp_to_seconds(timestamp):
    """Convert SRT timestamp to seconds"""
    # Split hours, minutes, and seconds (with milliseconds)
    hours, minutes, rest = timestamp.split(':')
    # Handle seconds and milliseconds (separated by comma)
    seconds, milliseconds = rest.split(',')
    
    total_seconds = (
        int(hours) * 3600 +
        int(minutes) * 60 +
        int(seconds) +
        int(milliseconds) / 1000
    )
    return total_seconds

def format_time(seconds):
    """Convert seconds to SRT timestamp format"""
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace('.', ',')

def clean_srt_duplicates(srt_content, time_threshold=30, similarity_threshold=0.9):
    """
    Remove duplicate captions within a specified time range in SRT format,
    keeping only the last occurrence.
    """
    # Pattern to match each SRT block, including newlines in text
    srt_pattern = re.compile(r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\n|\Z)", re.DOTALL)
    
    # Store blocks with their timing information
    blocks = []
    seen_texts = {}  # Track last occurrence of each text
    
    for match in srt_pattern.finditer(srt_content):
        index, start_time, end_time, text = match.groups()
        text = text.strip()
        
        # Convert start time to seconds for comparison
        start_seconds = timestamp_to_seconds(start_time)
        
        # Check for similar existing captions within the time threshold
        is_duplicate = False
        for existing_text, (existing_time, existing_idx) in list(seen_texts.items()):
            time_diff = abs(start_seconds - existing_time)
            
            # Check if texts are identical or very similar
            if (text == existing_text or 
                (len(text) > 0 and len(existing_text) > 0 and 
                 (text in existing_text or existing_text in text))):
                if time_diff < time_threshold:
                    # Remove the previous occurrence if this is a duplicate
                    blocks = [b for b in blocks if b[0] != str(existing_idx)]
                    is_duplicate = True
                    break
        
        if not is_duplicate or start_seconds - seen_texts.get(text, (0, 0))[0] >= time_threshold:
            blocks.append((index, start_time, end_time, text))
            seen_texts[text] = (start_seconds, len(blocks))
    
    # Rebuild the SRT content with proper formatting and sequential numbering
    cleaned_srt = []
    for i, (_, start_time, end_time, text) in enumerate(blocks, 1):
        cleaned_srt.append(f"{i}\n{start_time} --> {end_time}\n{text}\n\n")
    
    return ''.join(cleaned_srt)

def transcribe(video_file, transcribe_to_text, transcribe_to_srt, language):
    """
    Main transcription function that processes video files and generates
    text and/or SRT transcriptions.
    """
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    model_id = "openai/whisper-large-v3"
    
    try:
        # Initialize model and processor
        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id, 
            torch_dtype=torch_dtype, 
            low_cpu_mem_usage=True, 
            use_safetensors=True
        )
        model.to(device)
        
        processor = AutoProcessor.from_pretrained(model_id)
        
        pipe = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            max_new_tokens=128,
            chunk_length_s=60,
            batch_size=4,
            return_timestamps=True,
            torch_dtype=torch_dtype,
            device=device,
        )

        if video_file is None:
            yield "Error: No video file provided.", None
            return

        # Handle video file path
        video_path = video_file.name if hasattr(video_file, 'name') else video_file
        
        try:
            video = VideoFileClip(video_path)
        except Exception as e:
            yield f"Error processing video file: {str(e)}", None
            return

        # Process video in chunks
        audio = video.audio
        duration = video.duration
        n_chunks = math.ceil(duration / 10)
        transcription_txt = ""
        transcription_srt = []
        
        for i in range(n_chunks):
            start = i * 10
            end = min((i + 1) * 10, duration)
            audio_chunk = audio.subclip(start, end)
            
            temp_file_path = f"temp_audio_{i}.wav"
            
            try:
                # Save audio chunk to temporary file
                audio_chunk.write_audiofile(
                    temp_file_path,
                    codec='pcm_s16le',
                    verbose=False,
                    logger=None
                )
                
                # Process audio chunk
                with open(temp_file_path, "rb") as temp_file:
                    result = pipe(
                        temp_file_path,
                        generate_kwargs={"language": language}
                    )
                    
                    transcription_txt += result["text"]
                    
                    if transcribe_to_srt:
                        for chunk in result["chunks"]:
                            start_time, end_time = chunk["timestamp"]
                            if start_time is not None and end_time is not None:
                                transcription_srt.append({
                                    "start": start_time + i * 10,
                                    "end": end_time + i * 10,
                                    "text": chunk["text"].strip()
                                })
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
            
            # Report progress
            yield f"Progress: {int(((i + 1) / n_chunks) * 100)}%", None

        # Prepare output
        output = ""
        srt_file_path = None
        
        if transcribe_to_text:
            output += "Text Transcription:\n" + transcription_txt.strip() + "\n\n"
        
        if transcribe_to_srt:
            output += "SRT Transcription:\n"
            srt_content = ""
            
            # Generate initial SRT content
            for i, sub in enumerate(transcription_srt, 1):
                srt_entry = f"{i}\n{format_time(sub['start'])} --> {format_time(sub['end'])}\n{sub['text']}\n\n"
                srt_content += srt_entry
            
            # Clean up duplicates
            cleaned_srt_content = clean_srt_duplicates(srt_content)
            
            # Save SRT content to file
            srt_file_path = "transcription.srt"
            with open(srt_file_path, "w", encoding="utf-8") as srt_file:
                srt_file.write(cleaned_srt_content)
            
            output += f"\nSRT file saved as: {srt_file_path}"
        
        # Clean up video object
        video.close()
        
        yield output, srt_file_path
        
    except Exception as e:
        yield f"Error during transcription: {str(e)}", None

# Create Gradio interface
iface = gr.Interface(
    fn=transcribe,
    inputs=[
        gr.Video(label="Upload Video"),
        gr.Checkbox(label="Transcribe to Text", value=True),
        gr.Checkbox(label="Transcribe to SRT", value=True),
        gr.Dropdown(
            choices=['en', 'he', 'it', 'es', 'fr', 'de', 'zh', 'ar'],
            value='en',
            label="Language"
        )
    ],
    outputs=[
        gr.Textbox(label="Transcription Output"),
        gr.File(label="Download SRT")
    ],
    title="WhisperCap Video Transcription",
    description="""
    Upload a video file to transcribe its audio using Whisper Large V3.
    You can generate both text and SRT format transcriptions.
    Supported languages: English (en), Hebrew (he), Italian (it), Spanish (es),
    French (fr), German (de), Chinese (zh), Arabic (ar)
    """,
    allow_flagging="never"
)

# Launch the interface
if __name__ == "__main__":
    iface.launch(share=True)