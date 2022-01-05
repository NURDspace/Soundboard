function playSample(sampleName) {
    var oReq = new XMLHttpRequest();
    oReq.open("GET", "/api/samples/play/" + sampleName);
    oReq.send();
}
