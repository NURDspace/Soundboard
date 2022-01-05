{% include 'header.tpl' %}

<div class="col-lg-8 mx-auto p-3 py-md-5">
  <header class="d-flex align-items-center pb-3 mb-5 border-bottom">
    <a href="/" class="d-flex align-items-center text-dark text-decoration-none">
    <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor" class="bi bi-speaker" viewBox="0 0 16 16">
    <path d="M12 1a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1h8zM4 0a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2H4z"/>
    <path d="M8 4.75a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5zM8 6a2 2 0 1 0 0-4 2 2 0 0 0 0 4zm0 3a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm-3.5 1.5a3.5 3.5 0 1 1 7 0 3.5 3.5 0 0 1-7 0z"/>
    </svg>
      <span class="fs-4">Soundboard 2.0</span>
    </a>
  </header>
    <h3>Upload samples</h3><br>
    <p class="fs-5">
        {% if alert is defined %}
            <div class="alert {{alert['type']}} role="alert">{{alert['msg']}}</div>
        {% endif %}
        <form action="" enctype="multipart/form-data" method="POST">
            <p>Note that files should have no space in them, the name of the file corresponds to how it's being played and triggered.<br>
            Spaces will be automatically replaced with a underscore.    </p>
            <div class="input-group">
                <input type="file" class="form-control"  name="sampleUpload" id="sampleUpload" aria-describedby="sampleUpload" aria-label="Upload">
                <button class="btn btn-outline-secondary" type="submit" id="sampleSubmit">Upload</button>
              </div>
            <p>
                <font color="red">*</font> Accepted formats are: wav, mp3, ogg, flac and the file limit is 5 MB.
            </p>
        </form>
    </p>
</div>

{% include 'footer.tpl' %}