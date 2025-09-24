// QR Scanner UI enhancements for better user experience
class QRScannerUI {
  constructor(containerId) {
    this.containerId = containerId;
    this.container = document.getElementById(containerId);
    this.isActive = false;
  }

  addScanningOverlay() {
    if (!this.container) return;

    const overlay = document.createElement('div');
    overlay.id = 'qr-scanning-overlay';
    overlay.style.cssText = `
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
      z-index: 10;
    `;

    // Scanning frame
    const frame = document.createElement('div');
    frame.style.cssText = `
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      width: 250px;
      height: 250px;
      border: 3px solid #00ff00;
      border-radius: 12px;
      box-shadow: 0 0 20px rgba(0, 255, 0, 0.3);
      animation: qr-pulse 2s infinite;
    `;

    // Corner indicators
    const corners = ['top-left', 'top-right', 'bottom-left', 'bottom-right'];
    corners.forEach(corner => {
      const cornerEl = document.createElement('div');
      cornerEl.className = `qr-corner ${corner}`;
      cornerEl.style.cssText = `
        position: absolute;
        width: 30px;
        height: 30px;
        border: 4px solid #00ff00;
        ${corner.includes('top') ? 'top: -4px;' : 'bottom: -4px;'}
        ${corner.includes('left') ? 'left: -4px;' : 'right: -4px;'}
        ${corner.includes('top') && corner.includes('left') ? 'border-right: none; border-bottom: none;' : ''}
        ${corner.includes('top') && corner.includes('right') ? 'border-left: none; border-bottom: none;' : ''}
        ${corner.includes('bottom') && corner.includes('left') ? 'border-right: none; border-top: none;' : ''}
        ${corner.includes('bottom') && corner.includes('right') ? 'border-left: none; border-top: none;' : ''}
      `;
      frame.appendChild(cornerEl);
    });

    // Scanning line
    const scanLine = document.createElement('div');
    scanLine.style.cssText = `
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 2px;
      background: linear-gradient(90deg, transparent, #00ff00, transparent);
      animation: qr-scan-line 2s linear infinite;
    `;
    frame.appendChild(scanLine);

    // Instructions
    const instructions = document.createElement('div');
    instructions.style.cssText = `
      position: absolute;
      bottom: -60px;
      left: 50%;
      transform: translateX(-50%);
      color: #00ff00;
      font-size: 14px;
      text-align: center;
      background: rgba(0, 0, 0, 0.7);
      padding: 8px 16px;
      border-radius: 20px;
      white-space: nowrap;
    `;
    instructions.textContent = 'Position QR code within the frame';
    frame.appendChild(instructions);

    overlay.appendChild(frame);
    
    // Add CSS animations
    this.addScanningCSS();
    
    this.container.style.position = 'relative';
    this.container.appendChild(overlay);
    
    return overlay;
  }

  addScanningCSS() {
    if (document.getElementById('qr-scanner-styles')) return;

    const style = document.createElement('style');
    style.id = 'qr-scanner-styles';
    style.textContent = `
      @keyframes qr-pulse {
        0%, 100% { 
          border-color: #00ff00; 
          box-shadow: 0 0 20px rgba(0, 255, 0, 0.3);
        }
        50% { 
          border-color: #00aa00; 
          box-shadow: 0 0 30px rgba(0, 255, 0, 0.6);
        }
      }
      
      @keyframes qr-scan-line {
        0% { top: 0; opacity: 1; }
        50% { opacity: 1; }
        100% { top: calc(100% - 2px); opacity: 0; }
      }
      
      .qr-detection-success {
        animation: qr-success-flash 0.5s ease-out;
      }
      
      @keyframes qr-success-flash {
        0% { background-color: rgba(0, 255, 0, 0); }
        50% { background-color: rgba(0, 255, 0, 0.3); }
        100% { background-color: rgba(0, 255, 0, 0); }
      }
    `;
    document.head.appendChild(style);
  }

  showDetectionSuccess() {
    const overlay = document.getElementById('qr-scanning-overlay');
    if (overlay) {
      overlay.classList.add('qr-detection-success');
      setTimeout(() => {
        overlay.classList.remove('qr-detection-success');
      }, 500);
    }
  }

  updateInstructions(message, color = '#00ff00') {
    const instructions = document.querySelector('#qr-scanning-overlay .instructions');
    if (instructions) {
      instructions.textContent = message;
      instructions.style.color = color;
    }
  }

  removeScanningOverlay() {
    const overlay = document.getElementById('qr-scanning-overlay');
    if (overlay) {
      overlay.remove();
    }
  }

  showScanningTips() {
    const tips = [
      "Hold device steady",
      "Ensure good lighting", 
      "Keep QR code flat",
      "Move closer if needed",
      "Avoid reflections"
    ];

    let tipIndex = 0;
    const tipInterval = setInterval(() => {
      if (!this.isActive) {
        clearInterval(tipInterval);
        return;
      }
      
      this.updateInstructions(tips[tipIndex]);
      tipIndex = (tipIndex + 1) % tips.length;
    }, 3000);

    return tipInterval;
  }

  activate() {
    this.isActive = true;
    this.addScanningOverlay();
    return this.showScanningTips();
  }

  deactivate() {
    this.isActive = false;
    this.removeScanningOverlay();
  }
}

window.QRScannerUI = QRScannerUI;