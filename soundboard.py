import json
import os
import re
import yaml
import pyaudio
import logging
import threading
import tracemalloc
import coloredlogs
import paho.mqtt.client as mqtt

import soundboard.mpd
import soundboard.webserver
import soundboard.themesongs

import generators.samples
import generators.tones
import generators.speech

# TODO:
#    - test Intro tunes
#    - add Doorbell
#    - Turn down MPD volume

class soundBoard():
    log = logging.getLogger("Soundboard")
    threads = {}
    playlock = threading.Lock()
    samplePlaying = None


    def __init__(self):
        self.load_config()
        self.pyaudio = pyaudio.PyAudio()
        self.mqtt = mqtt.Client()

        self.mpd = soundboard.mpd.mpdClient(self)
        self.themeSongs = soundboard.themesongs.themeSongs(self)
        self.webserver = soundboard.webserver.webserver("0.0.0.0", self.config['webserver'], self)

        self.speech = generators.speech.speechGenerator(self)
        self.samplePlayer = generators.samples.samplePlayer(self)
        self.toneGenerator = generators.tones.toneGenerator(self)

        self.mqtt.enable_logger(logging.getLogger("MQTT"))
        self.mqtt.connect(self.config['mqtt']['host'], self.config['mqtt']['port'], 60)

        self.mqtt.on_connect = self.on_mqtt_connect
        self.mqtt.on_message = self.on_mqtt_message



    def load_config(self):
        """ Load the config"""
        # FIXME
        with open("config.yml", "r") as f:
            self.config = yaml.load(f, Loader=yaml.FullLoader)

        self.log.info(f"Samples available: {len(os.listdir(self.config['sample_path']))}")

    def start(self):
        """ Start the threads and then use the main thread for the MQTT loop"""
        self.threads = {
            threading.Thread(name="Webserver", target=self.webserver.webserver_thread),
            threading.Thread(name="Sample Thread", target=self.samplePlayer.sample_thread),
            threading.Thread(name="Tone Thread", target=self.toneGenerator.tone_thread)
            }

        for thread in self.threads:
            self.log.debug(thread)
            thread.daemon = True
            thread.start()

        self.log.debug(self.threads)
        self.mqtt.loop_forever()

    def on_mqtt_connect(self, client, userdata, flags, rc):
        """ When we succesfully connected to MQTT, we can subscribe"""
        self.log.info("MQTT connected.")
        for sub in self.config['mqtt']['subscribe']:
            self.log.info(f"Subscribing MQTT to {sub}")
            self.mqtt.subscribe(sub)

    def on_mqtt_message(self, client, userdata, msg):
        """
            Once a new MQTT message has arrived, serves
            as a wrapper for exceptions so that the entire
            program doesn't crash when we get an error.
        """
        try:
            self.on_mqtt_message_handle(client, userdata, msg)
        except Exception as e:
            import traceback
            self.log.error(f"Error during on_mqtt_message: {e}")
            traceback.print_exc()

    def find_sample(self, sample_name):
        """ Search in the sample folder and return a sample if found"""
        for file in os.listdir(self.config['sample_path']):
            if re.search(sample_name, file, re.IGNORECASE):
                return os.path.join(self.config['sample_path'], file)

    def on_mqtt_message_handle(self, client, userdata, msg):
        """ Hande MQTT message events"""
        self.log.debug(f"MQTT {msg.topic} >> {msg.payload.decode('utf-8')}")

        if msg.topic == "space/door/front": # send to themesongs
            self.themeSongs.mqtt_trigger(msg.payload.decode("utf-8"))

        # Handle all the speech events
        # Takes a json dict with the following parameters
        #  {"method": "15ai", "text": "Hello World", "name": "GlaDOS"}
        if msg.topic.startswith("soundboard/speech"):
            payload = json.loads(msg.payload.decode("utf-8"))
            if "method" in payload and "text" in payload and "name" in payload:
                # Allow these options to not be required
                regenCache = False
                cache = True

                if "cache" in payload:
                    cache = bool(payload['cache'])
                if "regenCache" in payload:
                    regenCache = bool(payload['cache'])

                # Fire it off as a thread, speech samples should be played via
                # the sampleQueue or if needed, by using the playlock
                speechThread = threading.Thread(target=self.speech.speech,
                    args=(payload['method'], payload['name'], payload['text'], None,
                        cache, regenCache))
                speechThread.daemon = True
                speechThread.start()

        # Handle incoming play
        if msg.topic == "soundboard/play":
            payload = msg.payload.decode("utf-8")

            # Split playload by space to allow multiple sounds
            for payload_split in payload.split(" "):

                # Generate tone for example: 100hzsw0.1 will generate
                # a 100 hz saw for 0.1 seconds (100hzsw or 100hz works too)
                if freq_match := re.search("([0-9]+)hz", payload_split, re.IGNORECASE):
                    tone = {"freq": freq_match.group(1), "type": "sine", "duration": 1.0}

                    if wave_match := re.search("[0-9]+.hz(sw|si|tri|sq)", payload_split, re.IGNORECASE):
                        tonemap = {"sw": "saw", "si": "sine", "tri": "triangle", "sq": "square"}
                        tone['type'] = tonemap[wave_match.group(1)]

                    if durr_match := re.search("[0-9]+.hz(sw|si|tri|sq)([0-9]+\.[0-9]+)", payload_split, re.IGNORECASE):
                        duration = float(durr_match.group(2))
                        if duration > 5.0:
                            duration = 5.0
                        tone['duration'] = duration

                    self.toneGenerator.toneQueue.put(tone)

                # Pay sample if we found it
                if sample := self.find_sample(payload_split):
                    self.samplePlayer.sampleQueue.put(sample) #TODO wonder if we can speed this up by pre-loading?


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, filename='soundboard.log')
    coloredlogs.install(level='DEBUG', fmt="%(asctime)s %(name)s %(levelname)s %(message)s")
    sb = soundBoard()
    tracemalloc.start() # debug
    sb.start()