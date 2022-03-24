import os
import re
import json
import logging

class themeSongs():
    log = logging.getLogger("Theme Songs")

    def __init__(self, soundboard) -> None:
        self.soundboard = soundboard

    def mqtt_trigger(self, payload):
        try:
            payload_json = json.loads(payload)
        except Exception as e:
            self.log.error(f"Failed to decode payload ({payload} ({e})")
            payload_json = None

        if payload_json and "name" in payload_json:
            if not os.path.exists(self.soundboard.config['themesongs']):
                self.log.error(f"Invalid path {self.soundboard.config['themesongs']}")
                return

            for file in os.listdir(self.soundboard.config['themesongs']):
                if re.search(payload_json['name'], file, re.IGNORECASE):
                    self.log.info(f"Theme song for {payload_json['name']} is {file}")

                    return self.soundboard.samplePlayer.sampleQueue.put(
                        os.path.join(self.soundboard.config['themesongs'], file))