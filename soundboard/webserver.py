import os
import time
import shutil
import bottle

# TODO handle logging

class webserver(bottle.Bottle):

    def __init__(self, host, port, soundboard):
        self.soundboard = soundboard
        self.host = host
        self.port = port
        self._app = bottle.Bottle()
        bottle.TEMPLATE_PATH.append('./html/templates')
        self.setup_routes()

    def setup_routes(self):
        # static files
        self._app.route("/assets/js/<filepath:re:.*\.js>",
                        callback=lambda filepath:bottle.static_file(filepath, root="html/js"))
        self._app.route("/assets/css/<filepath:re:.*\.(css|map)>",
                        callback=lambda filepath:bottle.static_file(filepath, root="html/css"))
        self._app.route("/assets/img/<filepath:re:.*\.(jpg|png|gif|ico|svg)>",
                         callback=lambda filepath:bottle.static_file(filepath, root="html/img"))
        self._app.route("/assets/font/<filepath:re:.*\.(eot|otf|svg|ttf|woff|woff2?)>",
                        callback=lambda filepath:bottle.static_file(filepath, root="html/font"))

        self._app.route('/', callback=self.index)
        self._app.route('/upload', method="GET", callback=self.upload)
        self._app.route('/upload', method="POST", callback=self.upload)
        self._app.route('/api/threads', method="GET", callback=self.api_threads)
        self._app.route('/api/samples/list', method="GET", callback=self.api_get_samples)
        self._app.route('/api/samples/play/<name>', method="GET", callback=self.api_play_sample)
        self._app.route('/api/tones/play/square/<freq>', method="GET", callback=self.api_tone_square)

    def webserver_thread(self):
        self._app.run(host=self.host, port=self.port, debug=True)

    def index(self):
        return bottle.jinja2_template('index.tpl', samples=self.get_samples())

    def upload(self):
        if bottle.request.method == "GET":
            return bottle.jinja2_template("upload.tpl")
        if bottle.request.method == "POST":
            uploaded_file = bottle.request.files.get('sampleUpload')
            if not uploaded_file:
                return bottle.jinja2_template("upload.tpl")

            if os.path.splitext(uploaded_file.filename)[1].lower() not in ('.flac', '.wav', '.mp3', '.ogg'): # TODO config
                return bottle.jinja2_template("upload.tpl", alert={"type": "alert-danger",
                    "msg": f"Filetype {os.path.splitext(uploaded_file.filename)[1].lower()} is not supported.\
                    Supported file types are wav, mp3, ogg and flac"})

            if os.path.exists(os.path.join(self.soundboard.config['sample_path'], uploaded_file.filename)):
                 return bottle.jinja2_template("upload.tpl", alert={"type": "alert-danger",
                    "msg": f"There is already a sample called {uploaded_file.filename}, please choose a different name."})

            temp_file = str(time.time()).split(".")[0] + os.path.splitext(uploaded_file.filename)[1]
            temp_path = os.path.join("cache/", temp_file) #todo config
            uploaded_file.save(temp_path)

            if os.path.getsize(temp_path) >= 3145728: # TODO config
                return bottle.jinja2_template("upload.tpl", alert={"type": "alert-danger",
                    "msg": f"{os.path.basename(uploaded_file.filename)} is too big! Max allowed size is 3MiB"})

            shutil.move(temp_path, os.path.join(self.soundboard.config['sample_path'], uploaded_file.filename.replace(" ", "_")))
            return bottle.jinja2_template("upload.tpl", alert={"type": "alert-success",
                    "msg": f"Upload successful!"})

    def get_samples(self):
        samples = []
        for sample in sorted(os.listdir(self.soundboard.config['sample_path'])):
            if not os.path.isdir(os.path.join(self.soundboard.config['sample_path'], sample)):
                samples.append({"name": os.path.splitext(sample)[0],
                                "ext": os.path.splitext(sample)[-1],
                                "path": os.path.join(self.soundboard.config['sample_path'], sample),
                                "size": os.path.getsize(os.path.join(self.soundboard.config['sample_path'], sample))})
        return samples

    # API
    def api_threads(self):
        return {"response": "OK", "threads":[str(t) for t in self.soundboard.threads]}

    def api_get_samples(self):
        return {"response": "OK", "samples": self.get_samples()}

    def api_play_sample(self, name):
        samples = self.get_samples()

        for sample in samples:
            if name in sample['name']:
                self.soundboard.samplePlayer.play_sample(sample['path'])
                return {"response": "OK"}

        return {"response": "FAIL", "MSG": f"Couldn't find {name}"}

    def api_tone_square(self, freq):
        self.soundboard.toneGenerator.toneQueue.put({"type": "square", "freq": freq, "duration": 1.0})
        return {"response": "OK"}