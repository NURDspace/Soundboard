import time
import logging

from typing import List, Tuple
from mpd import MPDClient

class mpdClient():
    log = logging.getLogger("MPD Client")

    def __init__(self, soundboard) -> None:
        self.soundboard = soundboard
        self.host = self.soundboard.config['mpd']['host']
        self.port = self.soundboard.config['mpd']['port']

    def mpd_togglepause(self) -> None:
        """ Pause MPD """
        with mpdWrapper(self.host, self.port) as client:
            client.pause()

    def mpd_status(self) -> dict:
        """ Return MPD status"""
        with mpdWrapper(self.host, self.port) as client:
          status = client.status()
          self.log.info("MPD state: %s" % status['state'])
          return status

    def volume(self, volume:int) -> None:
        with mpdWrapper(self.host, self.port) as client:
            client.setvol(volume)

    def ramp(self, size:int, start:int, end:int) -> list:
        self.log.debug(f"size: {size} | start: {start} | end: {end}")
        result = []
        step = (end - start) / (size - 1)

        for i in range(size):
           result.append(int(start + step * i))

        return result

    def volume_ramp_down(self, endvolume:int) -> Tuple[int, int]:
        with mpdWrapper(self.host, self.port) as client:
            startvolume = int(client.status()['volume'])
            if endvolume == startvolume:
                return endvolume, startvolume
            for step in self.ramp(self.soundboard.config['mpd']['ramp']['down'], startvolume, endvolume):
                self.log.debug(f"Ramping down step: {step} > {endvolume}")
                client.setvol(step)
                time.sleep(self.soundboard.config['mpd']['ramp']['delay'])
            return int(client.status()['volume']), startvolume

    def volume_ramp_up(self, endvolume:int) -> Tuple[int, int]:
        with mpdWrapper(self.host, self.port) as client:
            startvolume = int(client.status()['volume'])
            if endvolume == startvolume:
                return endvolume, startvolume
            for step in self.ramp(self.soundboard.config['mpd']['ramp']['up'], endvolume, startvolume):
                self.log.debug(f"Ramping up step: {step} > {endvolume}")
                client.volume(step)
                time.sleep(self.soundboard.config['mpd']['ramp']['delay'])
            return int(client.status()['volume']), startvolume

    def mpd_should_pause(self) -> None:
        """ Will only pause MPD if it's actually playing"""
        if self.mpd_status()['state'] == "play":
            self.mpd_togglepause()

    def mpd_should_resume(self) -> None:
        """ Will only resume MPD if it's actually paused"""
        if self.mpd_status()['state'] == "pause":
            self.mpd_togglepause()

class mpdWrapper(object):
    """ A simple context manager around the MPDclient lib """
    log = logging.getLogger("MPD Wrapper")

    def __init__(self, host="localhost", port=6600):
        self.host = host
        self.port = port
        self.client = MPDClient() # Make less verbose

    def __enter__(self) -> MPDClient:
        self.log.debug(f"Connecting to {self.host} @ {self.port}")
        self.client.connect(self.host, self.port)
        return self.client

    def __exit__(self, type, value, traceback):
        self.log.debug(f"Disconnecting from {self.host} @ {self.port}")
        self.client.close()
        self.client.disconnect()