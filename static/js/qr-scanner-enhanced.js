// Enhanced QR Scanner with optimized detection settings
class EnhancedQRScanner {
  constructor(elementId) {
    this.elementId = elementId;
    this.scanner = null;
    this.isScanning = false;
    this.detectionCount = 0;
    this.lastDetection = null;
  }

  async start(onSuccess, onError) {
    try {
      if (!window.Html5Qrcode) {
        throw new Error('Html5Qrcode library not available');
      }

      this.scanner = new Html5Qrcode(this.elementId);
      const cameras = await Html5Qrcode.getCameras();
      
      if (!cameras || cameras.length === 0) {
        throw new Error('No cameras available');
      }

      // Select best camera (prefer back/environment camera)
      const backCamera = cameras.find(camera => 
        camera.label.toLowerCase().includes('back') || 
        camera.label.toLowerCase().includes('rear') ||
        camera.label.toLowerCase().includes('environment')
      );
      
      const selectedCamera = backCamera || cameras[0];
      
      // Enhanced configuration for better QR detection
      const config = {
        fps: 15, // Higher FPS for better detection
        qrbox: function(viewfinderWidth, viewfinderHeight) {
          // Dynamic QR box sizing
          const minEdgePercentage = 0.7;
          const minEdgeSize = Math.min(viewfinderWidth, viewfinderHeight);
          const qrboxSize = Math.floor(minEdgeSize * minEdgePercentage);
          return {
            width: qrboxSize,
            height: qrboxSize
          };
        },
        aspectRatio: 1.0,
        disableFlip: false,
        videoConstraints: {
          facingMode: { ideal: "environment" },
          focusMode: { ideal: "continuous" },
          advanced: [
            { focusMode: "continuous" },
            { exposureMode: "continuous" },
            { whiteBalanceMode: "continuous" }
          ]
        },
        // Enhanced detection settings
        experimentalFeatures: {
          useBarCodeDetectorIfSupported: true
        }
      };

      await this.scanner.start(
        selectedCamera.id,
        config,
        (decodedText, decodedResult) => {
          this.handleDetection(decodedText, decodedResult, onSuccess);
        },
        (errorMessage) => {
          // Ignore continuous scanning errors but log them
          if (this.detectionCount === 0) {
            console.log('Scanner active, waiting for QR code...');
            this.detectionCount = 1;
          }
        }
      );

      this.isScanning = true;
      console.log(`Enhanced QR Scanner started with camera: ${selectedCamera.label}`);
      
    } catch (error) {
      if (onError) onError(error);
      throw error;
    }
  }

  handleDetection(decodedText, decodedResult, onSuccess) {
    // Prevent duplicate detections
    const now = Date.now();
    if (this.lastDetection && 
        this.lastDetection.text === decodedText && 
        (now - this.lastDetection.time) < 2000) {
      return;
    }

    this.lastDetection = { text: decodedText, time: now };
    
    // Validate QR code format
    if (this.isValidQRCode(decodedText)) {
      console.log('Valid QR code detected:', decodedText);
      if (onSuccess) onSuccess(decodedText, decodedResult);
    } else {
      console.log('Invalid QR code format:', decodedText);
    }
  }

  isValidQRCode(text) {
    if (!text || text.length < 1) return false;
    
    // Accept various formats:
    // 1. UUID format (asset UUIDs)
    // 2. Numeric IDs
    // 3. Alphanumeric codes
    // 4. URLs containing asset info
    
    const patterns = [
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i, // UUID
      /^\d+$/, // Numeric ID
      /^[A-Z0-9]{3,}$/i, // Alphanumeric code
      /asset[_-]?(\d+|[0-9a-f-]+)/i, // Asset reference
      /\/assets?\//i // URL with assets path
    ];

    return patterns.some(pattern => pattern.test(text)) || text.length >= 3;
  }

  async stop() {
    if (this.scanner && this.isScanning) {
      try {
        await this.scanner.stop();
        this.scanner.clear();
        this.isScanning = false;
        console.log('Enhanced QR Scanner stopped');
      } catch (error) {
        console.error('Error stopping scanner:', error);
      }
    }
  }

  getState() {
    return {
      isScanning: this.isScanning,
      detectionCount: this.detectionCount,
      lastDetection: this.lastDetection
    };
  }
}

window.EnhancedQRScanner = EnhancedQRScanner;