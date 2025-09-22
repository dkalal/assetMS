// Quagga fallback implementation
class QuaggaFallback {
  constructor() {
    this.isScanning = false;
    this.stream = null;
    this.detectionCallback = null;
  }

  init(config, callback) {
    // Simulate successful initialization
    setTimeout(() => callback(null), 100);
  }

  start() {
    this.isScanning = true;
    console.log('Quagga fallback: Scanner started - manual input recommended');
  }

  stop() {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    this.isScanning = false;
  }

  onDetected(callback) {
    this.detectionCallback = callback;
  }
}

// Create Quagga fallback with static methods
if (typeof Quagga === 'undefined') {
  const fallback = new QuaggaFallback();
  
  window.Quagga = {
    init: (config, callback) => fallback.init(config, callback),
    start: () => fallback.start(),
    stop: () => fallback.stop(),
    onDetected: (callback) => fallback.onDetected(callback)
  };
  
  console.log('Quagga fallback loaded - manual input available');
}