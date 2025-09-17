// Simple QR/Barcode scanner fallback using HTML5 video
class SimpleBarcodeScanner {
  constructor() {
    this.isScanning = false;
    this.stream = null;
  }

  async init(config, callback) {
    try {
      const constraints = {
        video: {
          facingMode: 'environment',
          width: { ideal: 1280 },
          height: { ideal: 720 }
        }
      };

      this.stream = await navigator.mediaDevices.getUserMedia(constraints);
      const video = config.inputStream.target;
      video.srcObject = this.stream;
      
      await new Promise((resolve) => {
        video.onloadedmetadata = resolve;
      });

      callback(null);
    } catch (error) {
      callback(error);
    }
  }

  start() {
    this.isScanning = true;
    // Simple implementation - in real scenario you'd use a proper QR library
    console.log('Scanner started - manual input recommended');
  }

  stop() {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    this.isScanning = false;
  }

  onDetected(callback) {
    // Placeholder - would need actual QR detection library
    this.detectionCallback = callback;
  }
}

// Fallback Quagga object
if (typeof Quagga === 'undefined') {
  window.Quagga = new SimpleBarcodeScanner();
}