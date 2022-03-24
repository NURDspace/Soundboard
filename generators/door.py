import os
import re
import json
import logging
import random

class door():
    log = logging.getLogger("door")

    def __init__(self, soundboard) -> None:
        self.soundboard = soundboard
    
    def mqtt_trigger(self, payload):
        try:
            payload_json = json.loads(payload)
        except Exception as e:
            self.log.error(f"Failed to decode payload ({payload} ({e})")
            payload_json = None

        samples = os.listdir(self.soundboard.config['doorbel']['samples'])
        return self.soundboard.samplePlayer.sampleQueue.put(
            os.path.join(self.soundboard.config['doorbel']['samples'], 
            random.choice(samples)))
