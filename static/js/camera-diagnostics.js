// Camera diagnostics and permission handling
class CameraDiagnostics {
  static async checkCameraAccess() {
    const results = {
      hasMediaDevices: !!navigator.mediaDevices,
      hasGetUserMedia: !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia),
      isSecureContext: window.isSecureContext,
      protocol: window.location.protocol,
      hostname: window.location.hostname,
      cameras: [],
      permissions: null,
      errors: []
    };

    try {
      // Check permissions API
      if (navigator.permissions) {
        const permission = await navigator.permissions.query({ name: 'camera' });
        results.permissions = permission.state;
      }

      // Try to enumerate devices
      if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
        const devices = await navigator.mediaDevices.enumerateDevices();
        results.cameras = devices.filter(device => device.kind === 'videoinput');
      }

      // Test camera access
      if (results.hasGetUserMedia) {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ 
            video: { facingMode: 'environment' } 
          });
          stream.getTracks().forEach(track => track.stop());
          results.cameraAccessible = true;
        } catch (error) {
          results.cameraAccessible = false;
          results.cameraError = error.name + ': ' + error.message;
        }
      }

    } catch (error) {
      results.errors.push(error.message);
    }

    return results;
  }

  static async requestCameraPermission() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          facingMode: { ideal: 'environment' },
          width: { ideal: 1280 },
          height: { ideal: 720 }
        } 
      });
      
      // Stop the stream immediately - we just wanted permission
      stream.getTracks().forEach(track => track.stop());
      return { success: true };
    } catch (error) {
      return { 
        success: false, 
        error: error.name,
        message: error.message,
        code: error.code
      };
    }
  }

  static getErrorMessage(diagnostics) {
    if (!diagnostics.hasMediaDevices) {
      return 'Camera API not supported in this browser. Please use a modern browser.';
    }

    if (!diagnostics.isSecureContext && diagnostics.hostname !== 'localhost' && diagnostics.hostname !== '127.0.0.1') {
      return 'Camera requires HTTPS connection. Please use HTTPS or localhost.';
    }

    if (diagnostics.permissions === 'denied') {
      return 'Camera permission denied. Please allow camera access in browser settings.';
    }

    if (diagnostics.cameras.length === 0) {
      return 'No cameras detected. Please connect a camera and refresh the page.';
    }

    if (diagnostics.cameraError) {
      if (diagnostics.cameraError.includes('NotAllowedError')) {
        return 'Camera access blocked. Please allow camera permission and try again.';
      }
      if (diagnostics.cameraError.includes('NotFoundError')) {
        return 'No camera found. Please connect a camera device.';
      }
      if (diagnostics.cameraError.includes('NotReadableError')) {
        return 'Camera is being used by another application. Please close other apps using the camera.';
      }
      return `Camera error: ${diagnostics.cameraError}`;
    }

    return 'Unknown camera issue. Please try manual input.';
  }
}

window.CameraDiagnostics = CameraDiagnostics;