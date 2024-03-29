import sys
import os
import math
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QFileDialog, QProgressBar, QCheckBox
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from moviepy.editor import VideoFileClip, AudioFileClip
import srt
import datetime
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline


# Set the ffmpeg_path relative to the current script directory
script_dir = os.path.dirname(os.path.realpath(__file__))
ffmpeg_path = os.path.join(script_dir, 'ffmpeg.exe')
# Add the directory containing ffmpeg to the system PATH
os.environ["PATH"] += os.pathsep + os.path.dirname(ffmpeg_path)

class TranscriptionThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str, str)
    errorOccurred = pyqtSignal(str)

    def __init__(self, file_path, transcribe_to_text, transcribe_to_srt):
        super().__init__()
        self.file_path = file_path
        self.transcribe_to_text = transcribe_to_text
        self.transcribe_to_srt = transcribe_to_srt
        self.stopped = False

    def run(self):
        try:

            file_extension = os.path.splitext(self.file_path)[1].lower()
            output_folder = os.path.join(os.path.dirname(self.file_path), os.path.splitext(os.path.basename(self.file_path))[0] + " Transcription Results")
            os.makedirs(output_folder, exist_ok=True)
            video_duration = 0

            temp_files = []  # Keep track of temporary files

            if file_extension == '.mp4':
                video = VideoFileClip(self.file_path)
                video_duration = video.duration
            elif file_extension in ['.wav', '.mp3']:
                audio = AudioFileClip(self.file_path)
                video_duration = audio.duration
            else:
                self.errorOccurred.emit("Unsupported file type")
                return

            n_chunks = math.ceil(video_duration / 30)
            transcription_txt = ""
            transcription_srt = ""
            results = []
            last_index = 0
            time_offset = 0

            for i in range(n_chunks):
                if self.stopped:
                    break

                start = i * 30
                end = min((i + 1) * 30, video_duration)
                chunk_duration = end - start

                temp_file_path = os.path.join(output_folder, f"temp_audio_{i}.wav")
                temp_files.append(temp_file_path)  # Add temp file path to the list

                audio_chunk = video.subclip(start, end).audio if file_extension == '.mp4' else audio.subclip(start, end)
                audio_chunk.write_audiofile(temp_file_path, codec='pcm_s16le')

                with open(temp_file_path, "rb") as audio_file:
                    device = "cuda:0" if torch.cuda.is_available() else "cpu"
                    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

                    model_id = "openai/whisper-large-v3"

                    model = AutoModelForSpeechSeq2Seq.from_pretrained(
                        model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True
                    )
                    model.to(device)

                    processor = AutoProcessor.from_pretrained(model_id)

                    pipe = pipeline(
                        "automatic-speech-recognition",
                        model=model,
                        tokenizer=processor.tokenizer,
                        feature_extractor=processor.feature_extractor,
                        max_new_tokens=128,
                        chunk_length_s=30,
                        batch_size=16,
                        return_timestamps=True,
                        torch_dtype=torch_dtype,
                        device=device,
                    )
                    result = pipe(temp_file_path)
                    print(result["text"])
                    transcription_text_part = (result["text"])
                    transcription_txt += transcription_text_part

                results.append(result)  # Append the result of each chunk to the results list

                current_progress = int(((i + 1) / n_chunks) * 100)
                print(f"Transcription Progress: {current_progress}")  # Debug print
                self.progress.emit(current_progress)

            if not self.stopped:
                if self.transcribe_to_text:
                    txt_file_path = os.path.join(output_folder,
                                                 os.path.splitext(os.path.basename(self.file_path))[0] + "_transcription.txt")
                    with open(txt_file_path, 'w', encoding='utf-8') as f:
                        f.write(transcription_txt)

                if self.transcribe_to_srt:
                    # Convert timestamp to srt.Time format
                    def seconds_to_srt_time(seconds):
                        """Convert seconds to SRT time format HH:MM:SS,MS."""
                        ms = int((seconds - int(seconds)) * 1000)
                        s = int(seconds) % 60
                        m = int(seconds / 60) % 60
                        h = int(seconds / 3600)
                        return f'{h:02}:{m:02}:{s:02},{ms:03}'

                    srt_file_path = os.path.join(output_folder,
                                                 os.path.splitext(os.path.basename(self.file_path))[0] + "_transcription.srt")
                    # Initialize the offset before processing the chunks
                    cumulative_offset = 0

                    # Function to split text into chunks with a maximum of 5 words per line
                    def split_text(text, max_words=5):
                        words = text.replace('.', '').split()  # Remove periods here
                        for i in range(0, len(words), max_words):
                            yield ' '.join(words[i:i + max_words])

                    with open(srt_file_path, 'w', encoding='utf-8') as f_srt:
                        counter = 1
                        for result in results:
                            for chunk in result['chunks']:
                                # Adjust the start and end times by adding the cumulative offset
                                start, end = chunk['timestamp']
                                adjusted_start = start + cumulative_offset
                                adjusted_end = end + cumulative_offset

                                # Convert adjusted timestamps to SRT time format
                                start_time = seconds_to_srt_time(adjusted_start)
                                end_time = seconds_to_srt_time(adjusted_end)

                                # Split the text for SRT formatting (up to 2 lines with a max of 5 words each)
                                split_lines = list(split_text(chunk['text'], max_words=5))
                                # Ensure we don't exceed 2 lines
                                split_lines = split_lines[:2]

                                # Write the subtitle entry to the SRT file
                                f_srt.write(f'{counter}\n')
                                f_srt.write(f'{start_time} --> {end_time}\n')
                                f_srt.write('\n'.join(split_lines) + '\n\n')
                                counter += 1
                            cumulative_offset += 30  # Or use the actual duration of the chunk


            # After transcription is done or stopped, clean up temporary files
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

                self.finished.emit("Transcription Complete. Saved to:", output_folder)

        except Exception as e:
            self.errorOccurred.emit(str(e))
            return

    def stop(self):
        self.stopped = True

class App(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('WhisperCap')
        self.setGeometry(100, 100, 600, 250)

        self.layout = QVBoxLayout()
        self.label = QLabel('No file selected', self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txtCheckbox = QCheckBox('Transcribe to Text File (.txt)', self)
        self.txtCheckbox.setChecked(True)
        self.srtCheckbox = QCheckBox('Transcribe to SRT File (.srt)', self)
        self.srtCheckbox.setChecked(True)
        self.progressBar = QProgressBar(self)
        self.progressBar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progressBar.setVisible(False)
        self.loadButton = QPushButton('Load File', self)
        self.loadButton.clicked.connect(self.loadFile)
        self.transcribeButton = QPushButton('Start Transcription', self)
        self.transcribeButton.clicked.connect(self.startTranscription)
        self.transcribeButton.setEnabled(False)
        self.stopButton = QPushButton('Stop', self)
        self.stopButton.clicked.connect(self.stopTranscription)
        self.stopButton.setEnabled(False)

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.txtCheckbox)
        self.layout.addWidget(self.srtCheckbox)
        self.layout.addWidget(self.progressBar)
        self.layout.addWidget(self.loadButton)
        self.layout.addWidget(self.transcribeButton)
        self.layout.addWidget(self.stopButton)

        self.setLayout(self.layout)

        self.file_path = ''
        self.transcriptionThread = None
        self.txtCheckbox.stateChanged.connect(self.enableTranscriptionButton)
        self.srtCheckbox.stateChanged.connect(self.enableTranscriptionButton)

    def loadFile(self):
        filePath, _ = QFileDialog.getOpenFileName(self, "Select Media File", "", "Media Files (*.mp4 *.wav *.mp3);;All Files (*)")
        if filePath:
            self.file_path = filePath
            fileType = 'video' if os.path.splitext(filePath)[1].lower() == '.mp4' else 'audio'
            self.label.setText(f"Loaded: {filePath}\nType: {fileType}")
            self.transcribeButton.setEnabled(True)
            self.progressBar.setValue(0)
            self.progressBar.setVisible(False)
            self.stopButton.setEnabled(False)

    def enableTranscriptionButton(self):
        self.transcribeButton.setEnabled(self.txtCheckbox.isChecked() or self.srtCheckbox.isChecked())

    def startTranscription(self):
        if self.file_path:
            self.progressBar.setVisible(True)
            self.transcribeButton.setEnabled(False)
            self.stopButton.setEnabled(True)
            self.transcriptionThread = TranscriptionThread(self.file_path, self.txtCheckbox.isChecked(), self.srtCheckbox.isChecked())
            self.transcriptionThread.progress.connect(self.updateProgress)
            self.transcriptionThread.finished.connect(self.transcriptionFinished)
            self.transcriptionThread.errorOccurred.connect(self.showError)
            self.transcriptionThread.start()

    def stopTranscription(self):
        if self.transcriptionThread and self.transcriptionThread.isRunning():
            self.transcriptionThread.stop()
            self.stopButton.setEnabled(False)
            self.progressBar.setVisible(False)
            self.progressBar.setValue(0)
            self.label.setText("Transcription stopped by user.")

    def enableTranscriptionButton(self):
        self.transcribeButton.setEnabled(self.txtCheckbox.isChecked() or self.srtCheckbox.isChecked())

    def updateProgress(self, value):
        self.progressBar.setValue(value)
        QApplication.processEvents()  # Force GUI update (use cautiously)

    def transcriptionFinished(self, message, folder_path):
        self.label.setText(f"{message}\n{folder_path}")
        self.progressBar.setValue(100)
        self.loadButton.setEnabled(True)
        self.transcribeButton.setEnabled(False)
        self.stopButton.setEnabled(False)  # Disable stop button after finishing

    def showError(self, message):
        self.label.setText(f"Error: {message}")
        self.progressBar.setValue(0)
        self.loadButton.setEnabled(True)
        self.transcribeButton.setEnabled(True)
        self.stopButton.setEnabled(False)  # Disable stop button on error


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec())
