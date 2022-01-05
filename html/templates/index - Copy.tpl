<html lang="en">
    <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <title>Sound board 2.0</title>
    </head>

    <body>
    <h3>Samples</h3>
    <div class="button-container">
        {% for sample in samples %}
            <button class="button" onclick=playSample('{{sample['name']}}')>{{sample['name']}}</button>
        {% endfor %}
        </div>

        <div> 
        <br>
        <h3>Tones</h3>
        <input type="number" id="freq" name="freq" min="0" max="22000"> <button class="button" onclick=playTone() )>Play Tone</button>

        </div>
    </body>

    <style>
    .container {
        display: grid;
        grid-template-columns: 33.33% 33.33% 33.33%;
        grid-template-rows: 33.33% 33.33% 33.33%;
        width: 500px;
        height: 200px;
        background: #87CEEB;
    }

    .button {
        margin: 10px;
    }
    </style>

    <script>
        function playSample(sampleName) {
            var oReq = new XMLHttpRequest();
            oReq.open("GET", "/api/samples/play/" + sampleName);
            oReq.send();
        }

        function playTone() {
            var oReq = new XMLHttpRequest();
            oReq.open("GET", "/api/tones/play/square/" + document.getElementById("freq").value);
            oReq.send();
        }

    </script>

</html>

