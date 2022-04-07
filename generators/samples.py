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
            Allow you to preload samples before adding them to the queue,
            should speed up playing multiple samples at once a bit more
            since the next once gets loaded while the previous one still plays
        """
        self.log.info(f"Queuing: {sample}")
        self.sampleQueue.put(pydub.AudioSegment.from_file(sample, os.path.splitext(sample)[-1].split(".")[-1]))

    def sample_thread(self):
        while True:
            sample = self.sampleQueue.get()
            self.soundboard.playlock.acquire()
            sample_dict = {"pause": False}
            is_raw = False

            try:
                if type(sample) == str:
                    self.log.info(f"Playing: {sample}")
                    sound = pydub.AudioSegment.from_file(sample, os.path.splitext(sample)[-1].split(".")[-1])

                elif type(sample) == dict:
                    sample_dict = sample
                    sample = sample["sample"]
                    sound = pydub.AudioSegment.from_file(sample, os.path.splitext(sample)[-1].split(".")[-1])

                else: # Raw pcm
                    is_raw = True
                    sound = sample
                    self.log.info(f"Playing: {type(sample)}")

                status = self.soundboard.mpd.mpd_status()

                if sample_dict['pause'] == True:
                   self.soundboard.mpd.mpd_should_pause()

                elif "volume" in status:
                   self.soundboard.mpd.volume_ramp_down(self.soundboard.config['mpd']['ramp']['amount'])

                if not is_raw:
                   
                    if sound.channels == 1:
                        sound = sound.set_channels(2)

                    if sound.frame_rate != 44100:
                        sound = sound.set_frame_rate(44100)

                    sound = pydub.effects.normalize(sound)
                    self.soundboard.pulse.write(sound.raw_data)
                else:
                    self.soundboard.pulse.write(sample)

                if self.sampleQueue.empty and "volume" in status and not sample_dict['pause'] == True:
                   self.soundboard.mpd.volume_ramp_up(int(status['volume']))

                elif sample_dict['pause'] == True:
                   self.soundboard.mpd.mpd_should_resume()

            except Exception as e:
                import traceback
                self.log.error(f"Exception happened while playing {sample} ({e})")
                traceback.print_exc()

            finally:
                self.samplePlaying = None
                self.soundboard.playlock.release()

    def play_sample(self, file):
        self.sampleQueue.put_nowait(file)