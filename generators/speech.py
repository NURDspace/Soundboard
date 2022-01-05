import os
import re
import io
import json
import pydub
import librosa
import hashlib
import logging
import requests

from pydub.playback import play
from soundboard import audio_format

class speechGenerator():
    log = logging.getLogger("speech")

    def __init__(self, soundboard):
        self.soundboard = soundboard

    def hashtext(self, text:str) -> str:
        """ hash text as sha1"""
        hasher = hashlib.sha1(text.encode("utf-8")) # Use sha1 so we don't get collissions
        return hasher.hexdigest()

    def speech(self, method:str, name:str, text:str, params=None, cache=True, regenCache=False) -> None:
        """
            Play speech/tts depending on the services we want.
            A service should return it's audio as well so that
            we can hash the text and save the audio for it.
            Note that this is only useful for speech that is NOT
            locally generated. As such, caching will automatically
            not be used for those that are local.
        """
        if method == "15ai":
            if cache or regenCache:
                hashed_text = self.hashtext(f"{text}_{name}")
                hashed_file = os.path.join(self.soundboard.config['speech']['cache'],
                                    f"{hashed_text}.wav")

                if os.path.exists(hashed_file):
                    # Play the file if it's found in cache
                    self.log.info(f"Playing cached speech {os.path.basename(hashed_file)} (15ai)")
                    return self.soundboard.samplePlayer.sampleQueue.put(hashed_file)

            audio, format = self.fifteen_ai(name, text)

            if audio:
                hashed_text = self.hashtext(f"{text}_{name}")
                if cache:
                    # Save file if caching enabled
                    self.log.info(f"Saving speech to cache as {os.path.basename(hashed_file)} (15ai)")
                    audio.export(os.path.join(self.soundboard.config['speech']['cache'], f"{hashed_text}.wav"),
                                    format=format)
        else:
            self.log.error(f"Unknown method {method}")

    def fifteen_ai(self, character, text) -> tuple((pydub.AudioSegment, str)):
        """
            Uses the 15ai api to generate voices using machine learning,
            check their website to see possible voices (case sensetive)
        """
        fifteen = FifteenAPI()

        # 15ai does not support numbers (such as 1, 2, 3 etc)
        # There for we convert numbers<int> to actual words first
        self.log.info(f"Generate \"{text}\" with {character} (15ai)")
        tts = fifteen.get_tts_raw(character, re.sub("[0-9]+", lambda nmbr:self.numbers_to_words(int(nmbr.group(0))), text))

        if tts["status"] == "OK" and tts["data"] is not None:
            self.log.info(f"Got {len(tts['data'])} bytes from fifteen.ai")

            # 15ai returns the data as float32 wav, so use some trickery
            # to convert this to "signed 16-bit little endian PCM so
            # that we can play it with pydub
            ioBytes = io.BytesIO(tts['data'])
            ioBytes.seek(0)
            y, sr = librosa.load(ioBytes,sr=None)
            convertedBytes = io.BytesIO(audio_format.float_to_byte(y))
            audio = pydub.AudioSegment.from_file(convertedBytes, format="raw", sample_width=2,
                                              channels=1, frame_rate=44100)
            play(audio)
            return audio, "wav"

        self.log.error(f"Failed to generate \"{text}\" with {character} (15ai)")
        return None, None

    def numbers_to_words(self, num,join=True):
        """
            words = {} convert an integer number into words
            https://stackoverflow.com/questions/8982163/how-do-i-tell-python-to-convert-integers-into-words
        """

        units = ['','one','two','three','four','five','six','seven','eight','nine']

        teens = ['','eleven','twelve','thirteen','fourteen','fifteen','sixteen',
                'seventeen','eighteen','nineteen']

        tens = ['','ten','twenty','thirty','forty','fifty','sixty','seventy',
                'eighty','ninety']

        thousands = ['','thousand','million','billion','trillion','quadrillion',
                    'quintillion','sextillion','septillion','octillion',
                    'nonillion','decillion','undecillion','duodecillion',
                    'tredecillion','quattuordecillion','sexdecillion',
                    'septendecillion','octodecillion','novemdecillion',
                    'vigintillion']
        words = []

        if num==0:
            words.append('zero')
        else:
            numStr = '%d' % num
            numStrLen = len(numStr)
            groups = int((numStrLen+2) /3)
            numStr = numStr.zfill(groups * 3)

            for i in range(0 ,groups* 3,3):
                h,t,u = int(numStr[i]), int(numStr[i+1]), int(numStr[i+2])
                g = int(groups- (i / 3+1))

                if  h >= 1:
                    words.append(units[h])
                    words.append('hundred')
                if t > 1:
                    words.append(tens[t])
                    if u >= 1:
                        words.append(units[u])
                elif t == 1:
                    if u >= 1:
                        words.append(teens[u])
                    else:
                        words.append(tens[t])
                else:
                    if u >= 1: words.append(units[u])

                if (g >=1 ) and ((h + t + u) > 0):
                    words.append(thousands[g] + ',')

        if join: return ' '.join(words)
        return words

class FifteenAPI:
    """ https://github.com/wafflecomposite/15.ai-Python-API/blob/master/fifteen_api.py """
    logger = logging.getLogger('15API')
    logger.addHandler(logging.StreamHandler())
    max_text_len = 500

    tts_headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US,en;q=0.9",
        "access-control-allow-origin": "*",
        "content-type": "application/json;charset=UTF-8",
        "origin": "https://fifteen.ai",
        "referer": "https://fifteen.ai/app",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "python-requests 15.ai-Python-API(https://github.com/wafflecomposite/15.ai-Python-API)"
    }

    tts_url = "https://api.15.ai/app/getAudioFile5"
    audio_url = "https://cdn.15.ai/audio/"

    def __init__(self, show_debug = False):
        if show_debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.WARNING)
        self.logger.info("FifteenAPI initialization")

    def get_tts_raw(self, character, text):

        resp = {"status": "NOT SET", "data": None}

        text_len = len(text)
        if text_len > self.max_text_len:
            self.logger.warning(f'Text too long ({text_len} > {self.max_text_len}), trimming to {self.max_text_len} symbols')
            text = text[:self.max_text_len - 1]

        if not text.endswith(".") and not text.endswith("!") and not text.endswith("?"):
            if len(text) < 140:
                text += '.'
            else:
                text = text[:-1] + '.'

        self.logger.info(f'Target text: [{text}]')
        self.logger.info(f'Character: [{character}]')

        data = json.dumps({"text": text, "character": character, "emotion": "Contextual"})
        self.logger.info('Waiting for 15.ai response...')

        try:
            response = requests.post(self.tts_url, data=data, headers=self.tts_headers)
        except requests.exceptions.ConnectionError as e:
            resp["status"] = f"ConnectionError ({e})"
            self.logger.error(f"ConnectionError ({e})")
            return resp

        if response.status_code == 200:
            resp["response"] = response.json()
            resp["audio_uri"] = resp["response"]["wavNames"][0]

            try:
                responseAudio = requests.get(self.audio_url+resp["audio_uri"], headers=self.tts_headers)
                resp["status"] = "OK"
                resp["data"] = responseAudio.content
                self.logger.info(f"15.ai API response success")
                return resp
            except requests.exceptions.ConnectionError as e:
                resp["status"] = f"ConnectionError ({e})"
                self.logger.error(f"ConnectionError ({e})")
                return resp

        else:
            self.logger.error(f'15.ai API request error, Status code: {response.status_code}')
            resp["status"] = f'15.ai API request error, Status code: {response.status_code}'

        return resp