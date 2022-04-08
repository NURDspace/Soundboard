

import subprocess
import os
import re
import json
import pydub
import shutil
import urllib
import string
import random
import hashlib
import logging
import requests

from urllib import parse

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

        if cache or regenCache:
            hashed_text = self.hashtext(f"{text}_{name}_{method}")
            hashed_file = os.path.join(self.soundboard.config['speech']['cache'],
                                    f"{hashed_text}.wav")

            if os.path.exists(hashed_file):
                # Play the file if it's found in cache
                self.log.info(f"Playing cached speech {os.path.basename(hashed_file)} ({method})")
                return self.soundboard.samplePlayer.sampleQueue.put(hashed_file)

        # AcapelaGroup
        if method == "apg":
            audioFile = self.acapellaGroup(name, text)

        elif method == "15ai":
            audioFile = self.fifteen_ai(name, text)

        else:
            return self.log.error(f"Unknown method {method}")

        if audioFile:
            self.soundboard.samplePlayer.sampleQueue.put(audioFile)
            hashed_text = self.hashtext(f"{text}_{name}_{method}")
            if cache:
                # Save file if caching enabled
                self.log.info(f"Saving speech to cache as {os.path.basename(hashed_file)} ({method})")
                shutil.copy(audioFile, hashed_file)

    def convert_bitdepth_sox(self, input, output):
        """
            Use sox to convert any input to 16 bit wav
        """
        if not os.path.exists(input):
            raise FileNotFoundError(f"Failed to find {input}")
        
        subprocess.call([
            self.soundboard.config['binaries']['sox'],
            input, "-b", "16", output
            ]
        )

        if not os.path.exists(output):
            raise FileNotFoundError(f"Failed to find {output}")

    def acapellaGroup(self, voice, text):
        apg = AcapelaGroup()
        self.log.info(f"Generate \"{text}\" with {voice} (AcapellaGroup)")

        data = apg.generate(voice, text)
        cacheFile = os.path.join(self.soundboard.config['speech']['cache'], "acapellagroup.mp3")
        cacheFileOutput = os.path.join(self.soundboard.config['speech']['cache'], "acapellagroup16.wav")
        
        with open(cacheFile, "wb") as fout:
            fout.write(data)
        
        self.convert_bitdepth_sox(cacheFile, cacheFileOutput)
        return cacheFileOutput

    def fifteen_ai(self, character, text):
        """
            Uses the 15ai api to generate voices using machine learning,
            check their website to see possible voices (case sensetive)
        """
        fifteen = FifteenAPI()


        # 15ai does not support numbers (such as 1, 2, 3 etc)
        # Therefor we convert numbers<int> to actual words first
        self.log.info(f"Generate \"{text}\" with {character} (15ai)")
        tts = fifteen.get_tts_raw(character, re.sub("[0-9]+", lambda num:self.numbers_to_words(int(num.group(0))), text))

        if tts["status"] == "OK" and tts["data"] is not None:
            self.log.info(f"Got {len(tts['data'])} bytes from fifteen.ai")

            # 15ai returns the data as float32 wav, so we use sox
            # to convert this to "signed 16-bit little endian PCM so
            # that we can play it with pydub
            
            cacheFile = os.path.join(self.soundboard.config['speech']['cache'], "tmp15ai32.wav")
            cacheFileOutput = os.path.join(self.soundboard.config['speech']['cache'], "tmp15ai16.wav")

            with open(cacheFile, "wb") as fout:
                fout.write(tts["data"])

            self.convert_bitdepth_sox(cacheFile, cacheFileOutput)
            #self.soundboard.samplePlayer.sampleQueue.put(cacheFileOutput)
            return cacheFileOutput

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

        if join: 
            return ' '.join(words)
        return words

class AcapelaGroup():
    """
        Based on https://github.com/weespin/WillFromAfarDownloader
    """
    voices = {'Mehdi': 'ar_sa_hd_mehdi_22k_lf.bvcu', 'Nizar': 'ar_sa_hd_nizar_22k_lf.bvcu', 'Salma': 'ar_sa_hd_salma_22k_lf.bvcu', 'Leila': 'ar_sa_hd_leila_22k_lf.bvcu', 'Laia': 'ca_es_hd_laia_22k_lf.bvcu', 'Eliska': 'czc_hd_eliska_22k_lf.bvcu', 'Mette': 'dad_hd_mette_22k_lf.bvcu', 'Rasmus': 'dad_hd_rasmus_22k_lf.bvcu', 'Lea': 'ged_lea_22k_ns.bvcu', 'ClaudiaSmile': 'ged_hd_claudiasmile_22k_lf.bvcu', 'Jonas': 'ged_jonas_22k_ns.bvcu', 'Andreas': 'ged_hd_andreas_22k_lf.bvcu', 'Claudia': 'ged_hd_claudia_22k_lf.bvcu', 'Sarah': 'ged_hd_sarah_22k_lf.bvcu', 'Julia': 'ged_hd_julia_22k_lf.bvcu', 'Klaus': 'ged_hd_klaus_22k_lf.bvcu', 'Dimitris': 'grg_hd_dimitris_22k_lf.bvcu', 'DimitrisSad': 'grg_dimitrissad_22k_ns.bvcu', 'DimitrisHappy': 'grg_dimitrishappy_22k_ns.bvcu', 'Lisa': 'en_au_hd_lisa_22k_lf.bvcu', 'Liam': 'en_au_liam_22k_ns.bvcu', 'Olivia': 'en_au_olivia_22k_ns.bvcu', 'Tyler': 'en_au_hd_tyler_22k_lf.bvcu', 'Rachel': 'eng_hd_rachel_22k_lf.bvcu', 'Graham': 'eng_hd_graham_22k_lf.bvcu', 'Rosie': 'eng_rosie_22k_ns.bvcu', 'Peter': 'eng_hd_peter_22k_lf.bvcu', 'Harry': 'eng_harry_22k_ns.bvcu', 'QueenElizabeth': 'eng_queenelizabeth_22k_ns.bvcu', 'Lucy': 'eng_hd_lucy_22k_lf.bvcu', 'PeterSad': 'eng_petersad_22k_ns.bvcu', 'PeterHappy': 'eng_peterhappy_22k_ns.bvcu', 'Deepa': 'en_in_hd_deepa_22k_lf.bvcu', 'Rhona': 'en_sct_hd_rhona_22k_lf.bvcu', 'Rod': 'enu_hd_rod_22k_lf.bvcu', 'WillOldMan': 'enu_willoldman_22k_ns.bvcu', 'Tracy': 'enu_hd_tracy_22k_lf.bvcu', 'Kenny': 'enu_hd_kenny_22k_lf.bvcu', 'WillBadGuy': 'enu_willbadguy_22k_ns.bvcu', 'Micah': 'enu_micah_22k_ns.bvcu', 'Ella': 'enu_ella_22k_ns.bvcu', 'Saul': 'enu_saul_22k_ns.bvcu', 'Valeria US': 'enu_valeriaenglish_22k_ns.bvcu', 'Laura': 'enu_hd_laura_22k_lf.bvcu', 'WillLittleCreature': 'enu_willlittlecreature_22k_ns.bvcu', 'Nelly': 'enu_hd_nelly_22k_lf.bvcu', 'Emilio US': 'enu_emilioenglish_22k_ns.bvcu', 'Will': 'enu_hd_will_22k_lf.bvcu', 'WillUpClose': 'enu_willupclose_22k_ns.bvcu', 'WillHappy': 'enu_willhappy_22k_ns.bvcu', 'Sharon': 'enu_hd_sharon_22k_lf.bvcu', 'Karen': 'enu_karen_22k_ns.bvcu', 'WillSad': 'enu_willsad_22k_ns.bvcu', 'Josh': 'enu_josh_22k_ns.bvcu', 'WillFromAfar': 'enu_willfromafar_22k_ns.bvcu', 'Ryan': 'enu_hd_ryan_22k_lf.bvcu', 'Scott': 'enu_scott_22k_ns.bvcu', 'Antonio': 'sps_hd_antonio_22k_lf.bvcu', 'Maria': 'sps_hd_maria_22k_lf.bvcu', 'Ines': 'sps_hd_ines_22k_lf.bvcu', 'Valeria Spanish': 'spu_valeria_22k_ns.bvcu', 'Emilio Spanish': 'spu_emilio_22k_ns.bvcu', 'Rosa': 'spu_hd_rosa_22k_lf.bvcu', 'Rodrigo': 'spu_hd_rodrigo_22k_lf.bvcu', 'Sanna': 'fif_hd_sanna_22k_lf.bvcu', 'Hanus': 'fo_fo_hanus_22k_ns.bvcu', 'Hanna': 'fo_fo_hanna_22k_ns.bvcu', 'Louise': 'frc_hd_louise_22k_lf.bvcu', 'Manon': 'frf_hd_manon_22k_lf.bvcu', 'Alice': 'frf_hd_alice_22k_lf.bvcu', 'AntoineHappy': 'frf_antoinehappy_22k_ns.bvcu', 'MargauxHappy': 'frf_margauxhappy_22k_ns.bvcu', 'Julie': 'frf_hd_julie_22k_lf.bvcu', 'Robot': 'frf_robot_22k_ns.bvcu', 'AntoineFromAfar': 'frf_antoinefromafar_22k_ns.bvcu', 'Bruno': 'frf_hd_bruno_22k_lf.bvcu', 'Margaux': 'frf_hd_margaux_22k_lf.bvcu', 'Anais': 'frf_hd_anais_22k_lf.bvcu', 'Valentin': 'frf_valentin_22k_ns.bvcu', 'AntoineUpClose': 'frf_antoineupclose_22k_ns.bvcu', 'Claire': 'frf_hd_claire_22k_lf.bvcu', 'Antoine': 'frf_hd_antoine_22k_lf.bvcu', 'Elise': 'frf_elise_22k_ns.bvcu', 'AntoineSad': 'frf_antoinesad_22k_ns.bvcu', 'MargauxSad': 'frf_margauxsad_22k_ns.bvcu', 'Kal': 'gb_se_hd_kal_22k_lf.bvcu', 'Aurora': 'iti_aurora_22k_ns.bvcu', 'Fabiana': 'iti_hd_fabiana_22k_lf.bvcu', 'Alessio': 'iti_alessio_22k_ns.bvcu', 'Vittorio': 'iti_hd_vittorio_22k_lf.bvcu', 'Chiara': 'iti_hd_chiara_22k_lf.bvcu', 'Sakura': 'ja_jp_hd_sakura_22k_lf.bvcu', 'Minji': 'ko_kr_hd_minji_22k_lf.bvcu', 'Zoe': 'dub_hd_zoe_22k_lf.bvcu', 'JeroenSad': 'dub_jeroensad_22k_ns.bvcu', 'Sofie': 'dub_hd_sofie_22k_lf.bvcu', 'JeroenHappy': 'dub_jeroenhappy_22k_ns.bvcu', 'Jeroen': 'dub_hd_jeroen_22k_lf.bvcu', 'Jasmijn': 'dun_hd_jasmijn_22k_lf.bvcu', 'Max': 'dun_hd_max_22k_lf.bvcu', 'Daan': 'dun_hd_daan_22k_lf.bvcu', 'Femke': 'dun_hd_femke_22k_lf.bvcu', 'Elias': 'non_elias_22k_ns.bvcu', 'Kari': 'non_hd_kari_22k_lf.bvcu', 'Emilie': 'non_emilie_22k_ns.bvcu', 'Bente': 'non_hd_bente_22k_lf.bvcu', 'Olav': 'non_hd_olav_22k_lf.bvcu', 'Ania': 'pop_hd_ania_22k_lf.bvcu', 'Marcia': 'pob_hd_marcia_22k_lf.bvcu', 'Celia': 'poe_hd_celia_22k_lf.bvcu', 'Alyona': 'rur_hd_alyona_22k_lf.bvcu', 'Mia': 'sc_se_hd_mia_22k_lf.bvcu', 'Samuel': 'sv_fi_hd_samuel_22k_lf.bvcu', 'Elin': 'sws_hd_elin_22k_lf.bvcu', 'Freja': 'sws_freja_22k_ns.bvcu', 'Erik': 'sws_hd_erik_22k_lf.bvcu', 'Filip': 'sws_filip_22k_ns.bvcu', 'Emma': 'sws_hd_emma_22k_lf.bvcu', 'Emil': 'sws_hd_emil_22k_lf.bvcu', 'Ipek': 'tut_hd_ipek_22k_lf.bvcu', 'Lulu': 'zh_cn_hd_lulu_22k_lf.bvcu', 'mehdi': 'ar_sa_hd_mehdi_22k_lf.bvcu', 'nizar': 'ar_sa_hd_nizar_22k_lf.bvcu', 'salma': 'ar_sa_hd_salma_22k_lf.bvcu', 'leila': 'ar_sa_hd_leila_22k_lf.bvcu', 'laia': 'ca_es_hd_laia_22k_lf.bvcu', 'eliska': 'czc_hd_eliska_22k_lf.bvcu', 'mette': 'dad_hd_mette_22k_lf.bvcu', 'rasmus': 'dad_hd_rasmus_22k_lf.bvcu', 'lea': 'ged_lea_22k_ns.bvcu', 'claudiasmile': 'ged_hd_claudiasmile_22k_lf.bvcu', 'jonas': 'ged_jonas_22k_ns.bvcu', 'andreas': 'ged_hd_andreas_22k_lf.bvcu', 'claudia': 'ged_hd_claudia_22k_lf.bvcu', 'sarah': 'ged_hd_sarah_22k_lf.bvcu', 'julia': 'ged_hd_julia_22k_lf.bvcu', 'klaus': 'ged_hd_klaus_22k_lf.bvcu', 'dimitris': 'grg_hd_dimitris_22k_lf.bvcu', 'dimitrissad': 'grg_dimitrissad_22k_ns.bvcu', 'dimitrishappy': 'grg_dimitrishappy_22k_ns.bvcu', 'lisa': 'en_au_hd_lisa_22k_lf.bvcu', 'liam': 'en_au_liam_22k_ns.bvcu', 'olivia': 'en_au_olivia_22k_ns.bvcu', 'tyler': 'en_au_hd_tyler_22k_lf.bvcu', 'rachel': 'eng_hd_rachel_22k_lf.bvcu', 'graham': 'eng_hd_graham_22k_lf.bvcu', 'rosie': 'eng_rosie_22k_ns.bvcu', 'peter': 'eng_hd_peter_22k_lf.bvcu', 'harry': 'eng_harry_22k_ns.bvcu', 'queenelizabeth': 'eng_queenelizabeth_22k_ns.bvcu', 'lucy': 'eng_hd_lucy_22k_lf.bvcu', 'petersad': 'eng_petersad_22k_ns.bvcu', 'peterhappy': 'eng_peterhappy_22k_ns.bvcu', 'deepa': 'en_in_hd_deepa_22k_lf.bvcu', 'rhona': 'en_sct_hd_rhona_22k_lf.bvcu', 'rod': 'enu_hd_rod_22k_lf.bvcu', 'willoldman': 'enu_willoldman_22k_ns.bvcu', 'tracy': 'enu_hd_tracy_22k_lf.bvcu', 'kenny': 'enu_hd_kenny_22k_lf.bvcu', 'willbadguy': 'enu_willbadguy_22k_ns.bvcu', 'micah': 'enu_micah_22k_ns.bvcu', 'ella': 'enu_ella_22k_ns.bvcu', 'saul': 'enu_saul_22k_ns.bvcu', 'valeria us': 'enu_valeriaenglish_22k_ns.bvcu', 'laura': 'enu_hd_laura_22k_lf.bvcu', 'willlittlecreature': 'enu_willlittlecreature_22k_ns.bvcu', 'nelly': 'enu_hd_nelly_22k_lf.bvcu', 'emilio us': 'enu_emilioenglish_22k_ns.bvcu', 'will': 'enu_hd_will_22k_lf.bvcu', 'willupclose': 'enu_willupclose_22k_ns.bvcu', 'willhappy': 'enu_willhappy_22k_ns.bvcu', 'sharon': 'enu_hd_sharon_22k_lf.bvcu', 'karen': 'enu_karen_22k_ns.bvcu', 'willsad': 'enu_willsad_22k_ns.bvcu', 'josh': 'enu_josh_22k_ns.bvcu', 'willfromafar': 'enu_willfromafar_22k_ns.bvcu', 'ryan': 'enu_hd_ryan_22k_lf.bvcu', 'scott': 'enu_scott_22k_ns.bvcu', 'antonio': 'sps_hd_antonio_22k_lf.bvcu', 'maria': 'sps_hd_maria_22k_lf.bvcu', 'ines': 'sps_hd_ines_22k_lf.bvcu', 'valeria spanish': 'spu_valeria_22k_ns.bvcu', 'emilio spanish': 'spu_emilio_22k_ns.bvcu', 'rosa': 'spu_hd_rosa_22k_lf.bvcu', 'rodrigo': 'spu_hd_rodrigo_22k_lf.bvcu', 'sanna': 'fif_hd_sanna_22k_lf.bvcu', 'hanus': 'fo_fo_hanus_22k_ns.bvcu', 'hanna': 'fo_fo_hanna_22k_ns.bvcu', 'louise': 'frc_hd_louise_22k_lf.bvcu', 'manon': 'frf_hd_manon_22k_lf.bvcu', 'alice': 'frf_hd_alice_22k_lf.bvcu', 'antoinehappy': 'frf_antoinehappy_22k_ns.bvcu', 'margauxhappy': 'frf_margauxhappy_22k_ns.bvcu', 'julie': 'frf_hd_julie_22k_lf.bvcu', 'robot': 'frf_robot_22k_ns.bvcu', 'antoinefromafar': 'frf_antoinefromafar_22k_ns.bvcu', 'bruno': 'frf_hd_bruno_22k_lf.bvcu', 'margaux': 'frf_hd_margaux_22k_lf.bvcu', 'anais': 'frf_hd_anais_22k_lf.bvcu', 'valentin': 'frf_valentin_22k_ns.bvcu', 'antoineupclose': 'frf_antoineupclose_22k_ns.bvcu', 'claire': 'frf_hd_claire_22k_lf.bvcu', 'antoine': 'frf_hd_antoine_22k_lf.bvcu', 'elise': 'frf_elise_22k_ns.bvcu', 'antoinesad': 'frf_antoinesad_22k_ns.bvcu', 'margauxsad': 'frf_margauxsad_22k_ns.bvcu', 'kal': 'gb_se_hd_kal_22k_lf.bvcu', 'aurora': 'iti_aurora_22k_ns.bvcu', 'fabiana': 'iti_hd_fabiana_22k_lf.bvcu', 'alessio': 'iti_alessio_22k_ns.bvcu', 'vittorio': 'iti_hd_vittorio_22k_lf.bvcu', 'chiara': 'iti_hd_chiara_22k_lf.bvcu', 'sakura': 'ja_jp_hd_sakura_22k_lf.bvcu', 'minji': 'ko_kr_hd_minji_22k_lf.bvcu', 'zoe': 'dub_hd_zoe_22k_lf.bvcu', 'jeroensad': 'dub_jeroensad_22k_ns.bvcu', 'sofie': 'dub_hd_sofie_22k_lf.bvcu', 'jeroenhappy': 'dub_jeroenhappy_22k_ns.bvcu', 'jeroen': 'dub_hd_jeroen_22k_lf.bvcu', 'jasmijn': 'dun_hd_jasmijn_22k_lf.bvcu', 'max': 'dun_hd_max_22k_lf.bvcu', 'daan': 'dun_hd_daan_22k_lf.bvcu', 'femke': 'dun_hd_femke_22k_lf.bvcu', 'elias': 'non_elias_22k_ns.bvcu', 'kari': 'non_hd_kari_22k_lf.bvcu', 'emilie': 'non_emilie_22k_ns.bvcu', 'bente': 'non_hd_bente_22k_lf.bvcu', 'olav': 'non_hd_olav_22k_lf.bvcu', 'ania': 'pop_hd_ania_22k_lf.bvcu', 'marcia': 'pob_hd_marcia_22k_lf.bvcu', 'celia': 'poe_hd_celia_22k_lf.bvcu', 'alyona': 'rur_hd_alyona_22k_lf.bvcu', 'mia': 'sc_se_hd_mia_22k_lf.bvcu', 'samuel': 'sv_fi_hd_samuel_22k_lf.bvcu', 'elin': 'sws_hd_elin_22k_lf.bvcu', 'freja': 'sws_freja_22k_ns.bvcu', 'erik': 'sws_hd_erik_22k_lf.bvcu', 'filip': 'sws_filip_22k_ns.bvcu', 'emma': 'sws_hd_emma_22k_lf.bvcu', 'emil': 'sws_hd_emil_22k_lf.bvcu', 'ipek': 'tut_hd_ipek_22k_lf.bvcu', 'lulu': 'zh_cn_hd_lulu_22k_lf.bvcu'}

    def generate(self, voice, text) -> None:
        token, email = self.update_nonce_token()
        return self.get_file(self.get_sound_link(self.map_voice(voice), text, token, email))

    def map_voice(self, voice):
        if voice in self.voices:
            print("lezz go")
            return self.voices[voice.lower()]
        print("ehhh")
        return voice

    def get_file(self, url):
        r = requests.get(url)
        if r.status_code == 200:
            return r.content
        return None

    def return_fake_gmail(self):
        generatorString = string.ascii_letters + string.digits
        return "".join(random.choice(generatorString) for i in range(random.randint(10, 25))) + "@gmail.com"

    def update_nonce_token(self):
        email = self.return_fake_gmail()
        data = {"googleid": email}
        r = requests.post("https://acapelavoices.acapela-group.com/index/getnonce/", data=data)
        try:
            return r.json()['nonce'], email
        except:
            return None, None

    def get_sound_link(self, voiceid, text, token, email):
        data = {"req_voice": voiceid, "cl_pwd": "", "cl_vers": "1-30",
                "req_echo": "ON", "cl_login": "AcapelaGroup",
                "req_comment": f"%7B%22nonce%22%3A%22{token}%22%2C%22user%22%3A%22{email}%22%7D",
                "req_text": urllib.parse.quote(text, safe=''),
                "cl_env": "ACAPELA_VOICES", "prot_vers": "2",
                "cl_app": "AcapelaGroup_WebDemo_Android"}
        print(f"voiceid: {voiceid}")
        r = requests.post("http://www.acapela-group.com:8080/webservices/1-34-01-Mobility/Synthesizer", data=data)
        if r.status_code == 200:
            response = r.content.decode("utf-8")
            return dict(parse.parse_qs(response))['snd_url'][0]


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
        "referrer": "https://fifteen.ai/app",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0"
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