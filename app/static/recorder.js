var liveVideo = document.getElementById('live');

function captureCamera(callback) {
    navigator.mediaDevices.getUserMedia({ audio: true, video: {
        width: 340, height: 220
      } }).then(function(camera) {
        callback(camera);
    }).catch(function(error) {
        alert('Unable to capture your camera. Please check console logs.');
        console.error(error);
    });
}

function stopRecordingCallback() {
    var blob = recorder.getBlob();
    var fileName = getFileName('mp4');
    //turn blob into 'file'
    var fileObject = new File([blob], fileName, {
        type: 'video/mp4'
    });

    var formData = new FormData();

    // recorded data
    formData.append('video-blob', fileObject);

    // file name
    formData.append('video-filename', fileObject.name);

    console.log("formdata = ", formData)

    // upload using jQuery
    $.ajax({
        url: '/live_log/' + event_id + '/requests',
        data: formData,
        cache: false,
        contentType: false,
        processData: false,
        type: 'POST',
        success: function(response) {
            if (response === 'success') {
            } else {
            }
        }
    });
    
    recorder.destroy();
    recorder = null;
}

var recorder; // globally accessible

document.getElementById('log').onclick = function() {
    this.disabled = true;
    captureCamera(function(camera) {
        liveVideo.muted = true;
        liveVideo.volume = 0;
        liveVideo.srcObject = camera;

        recorder = RecordRTC(camera, {
            type: 'video'
        });

        recorder.startRecording();

        // release camera on stopRecording
        recorder.camera = camera;

        recordTimeout = setTimeout(stopRecording, 3000);
    });
};

function stopRecording() {
    document.getElementById('log').disabled = false;
    clearTimeout(recordTimeout);
    recorder.stopRecording(stopRecordingCallback);
}

function getFileName(fileExtension) {
    var d = new Date();
    var year = d.getUTCFullYear();
    var month = d.getUTCMonth();
    var date = d.getUTCDate();
    var t = d.getHours() + ':' + d.getMinutes() + ':' + d.getSeconds()
    return 'RecordRTC-' + t + '-' + date + month + year + '-' + event_id + '.' + fileExtension;
}
