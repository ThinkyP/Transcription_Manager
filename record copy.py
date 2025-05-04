import sys
import subprocess
import signal
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QHBoxLayout
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize, QTimer
import os
import whisper
import threading
import simpleaudio as sa

class AudioRecorder(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("System Audio Recorder")
        self.setGeometry(600, 300, 600, 400)
        self.monitor_source = "alsa_output.pci-0000_00_1f.3.analog-stereo.monitor"  # Replace as needed
        self.process = None
        self.output_file = ""

        self.layout = QVBoxLayout()

        self.record_button = QPushButton()
        self.record_button.setIcon(QIcon.fromTheme("media-playback-start"))
        self.record_button.setIconSize(QSize(48, 48))
        self.record_button.clicked.connect(self.toggle_recording)
        self.layout.addWidget(self.record_button)

        # Table for recordings
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Filename", "Play", "Transcribe"])
        self.layout.addWidget(self.table)

        self.setLayout(self.layout)
        self.is_recording = False

        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.check_process)

        # Ensure recordings directory exists
        self.recordings_dir = os.path.join(os.getcwd(), "recordings")
        os.makedirs(self.recordings_dir, exist_ok=True)

        self.refresh_recordings()

    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.output_file = os.path.join(self.recordings_dir, f"system_audio_{timestamp}.wav")

        command = [
            "bash", "-c",
            f"exec parec --device={self.monitor_source} --rate=44100 --format=s16le --channels=2 | "
            f"sox -t raw -r 44100 -e signed -b 16 -c 2 - '{self.output_file}'"
        ]

        self.process = subprocess.Popen(command, preexec_fn=os.setsid)
        self.record_button.setIcon(QIcon.fromTheme("media-playback-stop"))
        self.is_recording = True
        self.timer.start()

    def stop_recording(self):
        if self.process:
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.process = None
            self.record_button.setIcon(QIcon.fromTheme("media-playback-start"))
            self.is_recording = False
            self.timer.stop()
            self.refresh_recordings()

    def check_process(self):
        if self.process and self.process.poll() is not None:
            self.stop_recording()

    def refresh_recordings(self):
        self.table.setRowCount(0)
        files = sorted([f for f in os.listdir(self.recordings_dir) if f.endswith(".wav")])
        for i, filename in enumerate(files):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(filename))

            play_button = QPushButton("▶")
            play_button.clicked.connect(lambda _, f=filename: self.play_audio(f))
            self.table.setCellWidget(i, 1, play_button)

            transcribe_button = QPushButton("✎")
            transcribe_button.clicked.connect(lambda _, f=filename: self.transcribe_audio(f))
            self.table.setCellWidget(i, 2, transcribe_button)

    def play_audio(self, filename):
        path = os.path.join(self.recordings_dir, filename)
        wave_obj = sa.WaveObject.from_wave_file(path)
        play_obj = wave_obj.play()
        play_obj.wait_done()

    def transcribe_audio(self, filename):
        def run_transcription():
            path = os.path.join(self.recordings_dir, filename)
            model = whisper.load_model("base")
            result = model.transcribe(path)
            txt_file = os.path.join(self.recordings_dir, filename.replace(".wav", ".txt"))
            with open(txt_file, "w", encoding="utf-8") as f:
                f.write(result["text"])
        threading.Thread(target=run_transcription).start()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AudioRecorder()
    window.show()
    sys.exit(app.exec_())
