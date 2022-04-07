import os
import re
import json
import logging
import random

class door():
    log = logging.getLogger("door")
    doorState = False
 
    def __init__(self, soundboard) -> None:
        self.soundboard = soundboard
    
    def doorbell_mqtt_trigger(self, payload):
        samples = os.listdir(os.path.join(self.soundboard.config['door']['samples'], "doorbell"))

        #self.soundboard.samplePlayer.sampleQueue.put(
        self.soundboard.samplePlayer.sampleQueue.put({"sample": 
            os.path.join(self.soundboard.config['door']['samples'], "doorbell", random.choice(samples)),
            "pause": True})

    def door_mqtt_trigger(self, payload):
        
        if self.soundboard.config['door']['open_close_sound'] == True:
            if payload == "False" : # door is open
                if not self.doorState == False and self.soundboard.running == True:
                    self.soundboard.samplePlayer.sampleQueue.put(
                        os.path.join(self.soundboard.config['door']['samples'], "door_open.wav"))
                self.doorState = False
        
            elif payload == "True": # door is closed
                if not self.doorState == True and self.soundboard.running == True:
                    self.soundboard.samplePlayer.sampleQueue.put(
                        os.path.join(self.soundboard.config['door']['samples'], "door_closed.wav"))
                self.doorState = True
