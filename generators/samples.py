import os
import queue
import pydub
import logging

from pydub.playback import play

class samplePlayer():
    sampleQueue = queue.Queue()
    log = logging.getLogger("sample player")

    def __init__(self, soundboard):
        self.soundboard = soundboard

    def preload(self, sample):
        """
            Allow you to preload samples before adding them to the queu,
            should speed up playing multiple samples at once a bit more
            since the next once gets loaded while the previous one still plays
        """
        self.log.info(f"Queuing: {sample}")
        self.sampleQueue.put(pydub.AudioSegment.from_file(sample, os.path.splitext(sample)[-1].split(".")[-1]))

    def sample_thread(self):
        while True:
            sample = self.sampleQueue.get()
            self.soundboard.playlock.acquire()

            try:
                if type(sample) == str:
                    self.log.info(f"Playing: {sample}")
                    sound = pydub.AudioSegment.from_file(sample, os.path.splitext(sample)[-1].split(".")[-1])

                else:
                    sound = sample
                    self.log.info(f"Playing: {type(sample)}")
                status = self.soundboard.mpd.mpd_status()

                if "volume" in status:
                    self.soundboard.mpd.volume_ramp_down(70)
                play(pydub.effects.normalize(sound)) # Play (fixme)
                if self.sampleQueue.empty and "volume" in status:
                    self.soundboard.mpd.volume_ramp_up(int(status['volume']))

            except Exception as e:
                import traceback
                self.log.error(f"Exception happened while playing {sample} ({e})")
                traceback.print_exc()

            finally:
                self.samplePlaying = None
                self.soundboard.playlock.release()

    def play_sample(self, file):
        self.sampleQueue.put_nowait(file)