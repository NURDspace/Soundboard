import math
import rtttl
import numpy
import queue
import pyaudio
import logging

from tones.mixer import Mixer
from tones import SINE_WAVE, SAWTOOTH_WAVE, TRIANGLE_WAVE, SQUARE_WAVE

class toneGenerator():
    toneQueue = queue.Queue()
    log = logging.getLogger("Tone Generator")

    def __init__(self, soundboard):
        self.soundboard = soundboard
        #self.stream = self.soundboard.pyaudio.open(format=pyaudio.paInt16, channels=1, rate=44100, output=True)

    def tone_thread(self):
        while True:
            tone = self.toneQueue.get()
            self.soundboard.playlock.acquire()

            if tone["type"] == "sine":
                self.play_tone(SINE_WAVE, tone['freq'], tone["duration"])

            elif tone["type"] == "saw":
                self.play_tone(SAWTOOTH_WAVE, tone['freq'], tone["duration"])

            elif tone["type"] == "triangle":
                self.play_tone(TRIANGLE_WAVE, tone['freq'], tone["duration"])

            elif tone["type"] == "square":
                self.play_tone(SQUARE_WAVE, tone['freq'], tone["duration"])

            elif tone['type'] == "morse":
                    self.morse_code(tone['morse'])

            elif tone['type'] == "dtmf":
                    self.play_dtmf_tone(tone['dtmf'])

            elif tone['type'] == "rttl":
                try:
                    self.play_rtttl(tone['rttl'])
                except Exception as e:
                    self.log.error(f"Failed to play RTTL ({e}) ({tone})")

            self.soundboard.playlock.release()

    def morse_code(self, morse):
        mixer = Mixer(44100, 1.0)
        mixer.create_track(0, SINE_WAVE)

        for char in morse: #TODO add to config
            if char == ".":
                duration = 0.100
            else:
                duration = 0.300
            mixer.add_tone(0, frequency=440, duration=duration, decay=0.0)
            mixer.add_silence(0, 0.100)

        self.soundboard.pulse.write(mixer.sample_data())

    def play_rtttl(self, ringtone):
        mixer = Mixer(44100, 1.0)
        mixer.create_track(0, SQUARE_WAVE)
        mixer.create_track(1, SQUARE_WAVE)
        mixer.create_track(2, SQUARE_WAVE)

        for note in rtttl.parse_rtttl(ringtone)['notes']:
           mixer.add_tone(1, frequency=note['frequency'] - 6,
                            duration=note['duration'] / 1000, decay=0.2, amplitude=0.3)
           mixer.add_tone(0, frequency=note['frequency'],
                            duration=note['duration'] / 1000, decay=0.1, amplitude=0.5)
           mixer.add_tone(2, frequency=note['frequency'] + 6,
                            duration=note['duration'] / 1000, decay=0.2, amplitude=0.3)

        self.soundboard.pulse.write(mixer.sample_data())
        self.soundboard.playlock.release()

    def play_tone(self, tone, freq, duration=1.0):
        self.log.info(f"Playing a {tone} with a freq of {freq} for {duration}")
        mixer = Mixer(44100, 1.0)
        mixer.create_track(0, tone)
        mixer.add_tone(0, frequency=freq, duration=duration, decay=0.1)
        self.soundboard.pulse.write(mixer.sample_data())

    def sine_wave(self, frequency, length, rate):
        length = int(length * rate)
        factor = float(frequency) * (math.pi * 2) / rate
        return numpy.sin(numpy.arange(length) * factor)

    def dtmf_sine_wave(self, f1, f2, length, rate):
        s1=self.sine_wave(f1,length,rate)
        s2=self.sine_wave(f2,length,rate)
        ss=s1+s2
        sa=numpy.divide(ss, 2.0)
        return sa

    def play_dtmf_tone(self, digits, length=0.2, rate=44100):
        dtmf_freqs = {'1': (1209,697), '2': (1336, 697), '3': (1477, 697), 'A': (1633, 697),
                    '4': (1209,770), '5': (1336, 770), '6': (1477, 770), 'B': (1633, 770),
                    '7': (1209,852), '8': (1336, 852), '9': (1477, 852), 'C': (1633, 852),
                    '*': (1209,941), '0': (1336, 941), '#': (1477, 941), 'D': (1633, 941)}

        dtmf_digits = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '0', '#', 'A', 'B', 'C', 'D']

        if type(digits) is not type(''):
            digits=str(digits)[0]

        digits = ''.join ([dd for dd in digits if dd in dtmf_digits])
        joined_chunks = []

        for digit in digits:
            digit=digit.upper()
            frames = []
            frames.append(self.dtmf_sine_wave(dtmf_freqs[digit][0], dtmf_freqs[digit][1], length, rate))
            chunk = numpy.concatenate(frames) * 0.25
            joined_chunks.append(chunk)

            # fader section
            fade = 200 # 200ms
            fade_in = numpy.arange(0., 1., 1/fade)
            fade_out = numpy.arange(1., 0., -1/fade)

            chunk[:fade] = numpy.multiply(chunk[:fade], fade_in) # fade sample wave in
            chunk[-fade:] = numpy.multiply(chunk[-fade:], fade_out) # fade sample wave out

        X = numpy.array(joined_chunks, dtype='float32') # creates an one long array of tone samples to record
        stream = self.soundboard.pyaudio.open(format=pyaudio.paFloat32, channels=1, rate=44100, output=True, frames_per_buffer=1024)
        stream.write(X.astype(numpy.float32).tostring()) # to hear tones
        stream.stop_stream()
        stream.close()