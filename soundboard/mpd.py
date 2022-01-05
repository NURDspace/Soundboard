import time
import logging

from mpd import MPDClient

class mpdClient():
    log = logging.getLogger("MPD Client")

    def __init__(self, soundboard):
        self.soundboard = soundboard
        self.host = self.soundboard.config['mpd']['host']
        self.port = self.soundboard.config['mpd']['port']

    def mpd_togglepause(self):
        """ Pause MPD """
        with mpdWrapper(self.host, self.port) as client:
            client.pause()

    def mpd_status(self):
        """ Return MPD status"""
        with mpdWrapper(self.host, self.port) as client:
          status = client.status()
          self.log.info("MPD state: %s" % status['state'])
          return status

    def volume(self, volume):
        with mpdWrapper(self.host, self.port) as client:
            client.volume(volume)


    def ramp(self, size, start, end):
        self.log.debug(f"size: {size} | start: {start} | end: {end}")
        result = []
        step = (end - start) / (size - 1)

        for i in range(size):
           result.append(int(start + step * i))

        return result

    def volume_ramp_down(self, endvolume):
        with mpdWrapper(self.host, self.port) as client:
            for step in self.ramp(self.soundboard.config['mpd']['ramp']['down'], int(client.status()['volume']), endvolume):
                self.log.debug(f"Ramping down step: {step} > {endvolume}")
                client.volume(step)
                time.sleep(self.soundboard.config['mpd']['ramp']['delay'])
            return client.status()['volume']

    def mpd_should_pause(self):
        """ Will only pause MPD if it's actually playing"""
        if self.mpd_status()['state'] == "play":
            self.mpd_togglepause()

    def mpd_should_resume(self):
        """ Will only resume MPD if it's actually paused"""
        if self.mpd_status()['state'] == "pause":
            self.mpd_togglepause()

class mpdWrapper(object):
    """ A simple context manager around the MPDclient lib """
    log = logging.getLogger("MPD Wrapper")

    def __init__(self, host="localhost", port=6600):
        self.host = host
        self.port = port
        self.client = MPDClient()

    def __enter__(self) -> MPDClient:
        self.log.debug(f"Connecting to {self.host} @ {self.port}")
        self.client.connect(self.host, self.port)
        return self.client

    def __exit__(self, type, value, traceback):
        self.log.debug(f"Disconnecting from {self.host} @ {self.port}")
        self.client.close()
        self.client.disconnect()