import sys
import subprocess
import signal
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QHBoxLayout, QLabel, QHeaderView
)
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette
from PyQt5.QtCore import QSize, QTimer, Qt
import os
import whisper
import threading
import simpleaudio as sa

class AudioRecorder(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎙️ Recorder Studio")
        self.setGeometry(600, 300, 700, 500)
        self.monitor_source = "alsa_output.pci-0000_00_1f.3.analog-stereo.monitor"  # Replace as needed
        self.process = None
        self.output_file = ""

        # Dark Mode Styling
        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: #E0E0E0;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                font-size: 14px;
            }
            QPushButton {
                background-color: #1E1E1E;
                color: #E0E0E0;
                border: 1px solid #333;
                border-radius: 6px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #2A2A2A;
            }
            QTableWidget {
                background-color: #1E1E1E;
                border: none;
                gridline-color: #333;
            }
            QHeaderView::section {
                background-color: #2A2A2A;
                padding: 4px;
                border: none;
                font-weight: bold;
            }
        """)

        self.layout = QVBoxLayout()

        # Record button
        self.record_button = QPushButton("▶ Start Recording")
        self.record_button.setIcon(QIcon.fromTheme("media-record"))
        self.record_button.setIconSize(QSize(24, 24))
        self.record_button.clicked.connect(self.toggle_recording)
        self.layout.addWidget(self.record_button, alignment=Qt.AlignCenter)

        # Table for recordings
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Filename", "", ""])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setColumnWidth(1, 50)
        self.table.setColumnWidth(2, 50)
        self.table.horizontalHeader().setVisible(False)
        self.layout.addWidget(self.table)

        self.setLayout(self.layout)
        self.is_recording = False

        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.check_process)

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
        self.record_button.setText("■ Stop Recording")
        self.record_button.setIcon(QIcon.fromTheme("media-playback-stop"))
        self.is_recording = True
        self.timer.start()

    def stop_recording(self):
        if self.process:
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.process = None
            self.record_button.setText("▶ Start Recording")
            self.record_button.setIcon(QIcon.fromTheme("media-record"))
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
            play_button.setMaximumWidth(40)
            play_button.clicked.connect(lambda _, f=filename: self.play_audio(f))
            self.table.setCellWidget(i, 1, play_button)

            transcribe_button = QPushButton("✎")
            transcribe_button.setMaximumWidth(40)
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
