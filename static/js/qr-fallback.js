// Html5Qrcode fallback implementation for QR code scanning
class Html5QrcodeFallback {
  constructor(elementId) {
    this.elementId = elementId;
    this.isScanning = false;
    this.stream = null;
  }

  async start(cameraId, config, qrCodeSuccessCallback, qrCodeErrorCallback) {
    try {
      const constraints = {
        video: {
          facingMode: 'environment',
          width: { ideal: 1280 },
          height: { ideal: 720 }
        }
      };

      this.stream = await navigator.mediaDevices.getUserMedia(constraints);
      const element = document.getElementById(this.elementId);
      
      if (element) {
        const video = document.createElement('video');
        video.srcObject = this.stream;
        video.style.width = '100%';
        video.style.height = 'auto';
        video.autoplay = true;
        element.appendChild(video);
        
        this.isScanning = true;
        console.log('QR Scanner fallback: Camera started - manual input recommended');
      }
      
      return Promise.resolve();
    } catch (error) {
      return Promise.reject(error);
    }
  }

  async stop() {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    this.isScanning = false;
    return Promise.resolve();
  }

  clear() {
    const element = document.getElementById(this.elementId);
    if (element) {
      element.innerHTML = '';
    }
  }

  static async getCameras() {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const cameras = devices.filter(device => device.kind === 'videoinput');
      return cameras.map(camera => ({ id: camera.deviceId, label: camera.label }));
    } catch (error) {
      return [];
    }
  }
}

// Create Html5Qrcode fallback if library fails to load
if (typeof Html5Qrcode === 'undefined') {
  window.Html5Qrcode = Html5QrcodeFallback;
  console.log('Html5Qrcode fallback loaded - manual input recommended');
}