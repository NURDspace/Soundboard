import time
import mpd 
import logging
import threading

from mpd import MPDClient

class mpdclient():
    log = logging.getLogger("MPD Client")
    mpd_lock = threading.Lock()

    def __init__(self, soundboard) -> None:
        self.soundboard = soundboard
        self.host = self.soundboard.config['mpd']['host']
        self.port = self.soundboard.config['mpd']['port']
        
        self.client = MPDClient()
        self.client.connect(self.host, self.port)
        
        threading.Thread(target=self.mpd_keepalive).start()

    def mpd_keepalive(self):
        """ Keep MPD connection alive or reconnect when an error happens."""
        self.log.info("MPD client keep alive started")
        while True:
            try:
                self.mpd_lock.acquire()
                self.client.status()
                self.mpd_lock.release()
            except mpd.base.ConnectionError:
                self.client.connect(self.host, self.port)
            finally:
                time.sleep(1)

    def mpd_togglepause(self) -> None:
        """ Pause MPD """
        self.mpd_lock.acquire()
        self.client.pause()
        self.mpd_lock.release()

    def mpd_status(self) -> dict:
        """ Return MPD status"""

        if self.client._sock == None:
            self.client.connect(self.host, self.port)
        status = self.client.status()
        return status

    def volume(self, volume:int) -> None:
        self.mpd_lock.acquire()
        self.client.setvol(volume)
        self.mpd_lock.release()

    def ramp(self, size:int, start:int, end:int) -> list:
        self.log.debug(f"size: {size} | start: {start} | end: {end}")
        result = []
        step = (end - start) / (size - 1)

        for i in range(size):
           result.append(int(start + step * i))

        return result

    def volume_ramp_up(self, endvolume):
        self.volume_ramp(endvolume, False)

    def volume_ramp_down(self, endvolume):
        self.volume_ramp(endvolume, True)

    def volume_ramp(self, endvolume, down=False):
        status = self.mpd_status()
        if "volume" in status:
            startvolume = int(status['volume'])
            
            if down is False and startvolume == endvolume:
                print("endvolume matches startvolume")
                return endvolume, startvolume
            
            elif endvolume == startvolume:
                return endvolume, startvolume
            
            # TODO add back config
            step_list = [s for s in reversed(self.ramp(5, endvolume, startvolume))]
            
            for step in step_list:
                self.volume(step)
                #time.sleep(self.soundboard.config['mpd']['ramp']['delay'])
                # TODO add back config
                time.sleep(0.025)
            return int(self.mpd_status()['volume']), startvolume


    def mpd_should_pause(self) -> None:
        """ Will only pause MPD if it's actually playing"""
        if self.mpd_status()['state'] == "play":
            self.mpd_togglepause()

    def mpd_should_resume(self) -> None:
        """ Will only resume MPD if it's actually paused"""
        if self.mpd_status()['state'] == "pause":
            self.mpd_togglepause()