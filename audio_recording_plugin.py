import os
import wave
import pyaudio
from time import time
from plugin import Plugin

class AudioRecordingPlugin(Plugin):
    def __init__(self, g_pool):
        super().__init__(g_pool)
        self.audio = None
        self.stream = None
        self.recording = False
        self.frames = []
        self.start_time = None

    def init_ui(self):
        self.add_menu()
        self.menu.label = 'Audio Recording'
        self.menu.append(self.gui.button('Start Recording', self.start_recording))
        self.menu.append(self.gui.button('Stop Recording', self.stop_recording))

    def deinit_ui(self):
        self.remove_menu()

    def start_recording(self):
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(format=pyaudio.paInt16,
                                       channels=1,
                                       rate=44100,
                                       input=True,
                                       frames_per_buffer=1024)
        self.recording = True
        self.start_time = time()

    def stop_recording(self):
        if self.recording:
            self.stream.stop_stream()
            self.stream.close()
            self.audio.terminate()

            output_path = os.path.join(self.g_pool.user_dir, 'recordings')
            os.makedirs(output_path, exist_ok=True)
            file_name = f'audio_{self.start_time:.0f}.wav'
            file_path = os.path.join(output_path, file_name)

            with wave.open(file_path, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
                wf.setframerate(44100)
                wf.writeframes(b''.join(self.frames))

            self.frames = []
            self.recording = False

    def recent_events(self, events):
        if self.recording:
            data = self.stream.read(1024)
            self.frames.append(data)

