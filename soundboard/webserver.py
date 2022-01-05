import os
import bottle

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
        self._app.route('/api/threads', method="GET", callback=self.api_threads)
        self._app.route('/api/samples/list', method="GET", callback=self.api_get_samples)
        self._app.route('/api/samples/play/<name>', method="GET", callback=self.api_play_sample)
        self._app.route('/api/tones/play/square/<freq>', method="GET", callback=self.api_tone_square)

    def webserver_thread(self):
        self._app.run(host=self.host, port=self.port, debug=True)

    def index(self):
        return bottle.jinja2_template('index.tpl', samples=self.get_samples())

    def get_samples(self):
        samples = []
        for sample in os.listdir(self.soundboard.config['sample_path']):
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