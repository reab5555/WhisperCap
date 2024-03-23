import sys
import os
import math
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QFileDialog, QProgressBar, QCheckBox
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from moviepy.editor import VideoFileClip, AudioFileClip
import tempfile
from openai import OpenAI
import srt
import datetime


# Initialize OpenAI API
api_key = "API_KEY_HERE"

client = OpenAI(api_key=api_key)

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
        last_index = 0
        time_offset = 0

        for i in range(n_chunks):
            if self.stopped: break

            start = i * 30
            end = min((i + 1) * 30, video_duration)
            chunk_duration = end - start

            temp_file_path = os.path.join(output_folder, f"temp_audio_{i}.wav")
            temp_files.append(temp_file_path)  # Add temp file path to the list

            audio_chunk = video.subclip(start, end).audio if file_extension == '.mp4' else audio.subclip(start, end)
            audio_chunk.write_audiofile(temp_file_path, codec='pcm_s16le')

            with open(temp_file_path, "rb") as audio_file:
                    if self.transcribe_to_text:
                        response_txt = client.audio.transcriptions.create(
                            file=audio_file,
                            model="whisper-1",
                            response_format="text",
                        )
                        # Assuming the response is not always a dictionary and might be a string directly
                        if isinstance(response_txt, dict) and 'text' in response_txt:
                            transcription_text_part = response_txt['text']
                        elif isinstance(response_txt, str):
                            transcription_text_part = response_txt
                        else:
                            # Handle unexpected response types, maybe log an error or throw an exception
                            print("Unexpected response format from transcription service.")
                            transcription_text_part = ""

                        transcription_txt += transcription_text_part

                    if self.transcribe_to_srt:
                        with open(temp_file_path, "rb") as audio_file:
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


            self.progress.emit(int((i + 1) / n_chunks * 100))

        # After transcription is done or stopped, clean up temporary files
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)

        if not self.stopped:
            if self.transcribe_to_text:
                txt_file_path = os.path.join(output_folder, os.path.splitext(os.path.basename(self.file_path))[0] + "_transcription.txt")
                with open(txt_file_path, 'w', encoding='utf-8') as f:
                    f.write(transcription_txt)

            if self.transcribe_to_srt:
                srt_file_path = os.path.join(output_folder, os.path.splitext(os.path.basename(self.file_path))[0] + "_transcription.srt")
                with open(srt_file_path, 'w', encoding='utf-8') as f:
                    f.write(transcription_srt)


            self.finished.emit("Transcription Complete. Saved to:", output_folder)


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
