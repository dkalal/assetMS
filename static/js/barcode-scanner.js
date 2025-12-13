/**
 * Barcode/QR Scanner Component - World-Class Implementation
 * Inspired by: ServiceNow ITAM, IBM Maximo Mobile, SAP Fiori Scanner
 * 
 * Features:
 * - HTML5 camera access (front/back)
 * - Real-time barcode/QR detection
 * - Batch scanning mode
 * - Manual entry fallback
 * - Scan history
 * - Export results
 * - Offline support
 * - Accessibility
 * 
 * Libraries: html5-qrcode (lightweight, no dependencies)
 * 
 * Usage:
 *   const scanner = new BarcodeScanner('scanner-container', {
 *     onScan: (result) => console.log('Scanned:', result),
 *     batchMode: true
 *   });
 */

class BarcodeScanner {
  /**
   * Initialize barcode scanner
   * @param {string} containerId - Container element ID
   * @param {Object} options - Configuration options
   */
  constructor(containerId, options = {}) {
    this.containerId = containerId;
    this.container = document.getElementById(containerId);
    
    if (!this.container) {
      console.warn(`BarcodeScanner: Container "${containerId}" not found`);
      return;
    }

    // Configuration
    this.options = {
      onScan: options.onScan || ((result) => console.log('Scanned:', result)),
      onError: options.onError || ((error) => console.error('Scanner error:', error)),
      batchMode: options.batchMode !== false, // Batch mode by default
      autoStop: options.autoStop !== false, // Auto-stop after scan in single mode
      fps: options.fps || 10, // Frames per second
      qrbox: options.qrbox || 250, // Scanner box size
      aspectRatio: options.aspectRatio || 1.0,
      disableFlip: options.disableFlip !== true,
      formatsToSupport: options.formatsToSupport || [
        'QR_CODE',
        'CODE_128',
        'CODE_39',
        'EAN_13',
        'EAN_8',
        'UPC_A',
        'UPC_E'
      ],
      showHistory: options.showHistory !== false,
      maxHistory: options.maxHistory || 50,
      allowDuplicates: options.allowDuplicates !== true,
    };

    // State
    this.isScanning = false;
    this.scanner = null;
    this.scanHistory = [];
    this.currentCamera = 'environment'; // 'user' or 'environment'
    
    // Initialize
    this.init();
  }

  /**
   * Initialize scanner UI and components
   */
  init() {
    this.createUI();
    this.loadHistory();
    this.bindEvents();
  }

  /**
   * Create scanner UI
   */
  createUI() {
    this.container.innerHTML = `
      <div class="scanner-wrapper">
        <!-- Scanner Header -->
        <div class="scanner-header">
          <h3 class="scanner-title">
            <i class="bi bi-qr-code-scan"></i>
            Scan Asset Barcode/QR Code
          </h3>
          <button type="button" class="btn-close-scanner" aria-label="Close scanner">
            <i class="bi bi-x-lg"></i>
          </button>
        </div>

        <!-- Scanner Controls -->
        <div class="scanner-controls">
          <button type="button" class="btn-scanner btn-scanner-primary" id="btn-start-scan">
            <i class="bi bi-camera"></i>
            Start Scanning
          </button>
          <button type="button" class="btn-scanner btn-scanner-secondary" id="btn-stop-scan" style="display: none;">
            <i class="bi bi-stop-circle"></i>
            Stop Scanning
          </button>
          <button type="button" class="btn-scanner btn-scanner-secondary" id="btn-switch-camera">
            <i class="bi bi-arrow-repeat"></i>
            Switch Camera
          </button>
          <button type="button" class="btn-scanner btn-scanner-secondary" id="btn-manual-entry">
            <i class="bi bi-keyboard"></i>
            Manual Entry
          </button>
        </div>

        <!-- Scanner View -->
        <div class="scanner-view" id="scanner-view" style="display: none;">
          <div class="scanner-frame">
            <div id="qr-reader"></div>
            <div class="scanner-overlay">
              <div class="scanner-box"></div>
              <div class="scanner-instructions">
                Position barcode/QR code within the frame
              </div>
            </div>
          </div>
        </div>

        <!-- Manual Entry Form -->
        <div class="manual-entry-form" id="manual-entry-form" style="display: none;">
          <div class="form-group">
            <label for="manual-code-input" class="form-label">Enter Code Manually</label>
            <div class="input-group">
              <input type="text" 
                     class="form-control" 
                     id="manual-code-input" 
                     placeholder="Enter barcode or QR code"
                     autocomplete="off">
              <button type="button" class="btn btn-primary" id="btn-submit-manual">
                <i class="bi bi-check-lg"></i>
                Submit
              </button>
            </div>
            <small class="form-text">Use this if camera scanning is not available</small>
          </div>
        </div>

        <!-- Scan Status -->
        <div class="scan-status" id="scan-status">
          <div class="scan-count">
            <i class="bi bi-check-circle"></i>
            <span id="scan-count-value">0</span> scanned
          </div>
          <button type="button" class="btn-scanner btn-scanner-sm" id="btn-clear-history">
            <i class="bi bi-trash"></i>
            Clear
          </button>
        </div>

        <!-- Scan History -->
        <div class="scan-history" id="scan-history" style="display: ${this.options.showHistory ? 'block' : 'none'};">
          <h4 class="scan-history-title">Scan History</h4>
          <div class="scan-history-list" id="scan-history-list">
            <div class="scan-history-empty">
              <i class="bi bi-inbox"></i>
              <p>No scans yet</p>
            </div>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="scanner-actions">
          <button type="button" class="btn btn-secondary" id="btn-export-scans">
            <i class="bi bi-download"></i>
            Export Scans
          </button>
          <button type="button" class="btn btn-primary" id="btn-process-scans">
            <i class="bi bi-arrow-right"></i>
            Process Scans
          </button>
        </div>
      </div>
    `;
  }

  /**
   * Bind event listeners
   */
  bindEvents() {
    // Start/Stop scanning
    document.getElementById('btn-start-scan')?.addEventListener('click', () => this.startScanning());
    document.getElementById('btn-stop-scan')?.addEventListener('click', () => this.stopScanning());
    
    // Switch camera
    document.getElementById('btn-switch-camera')?.addEventListener('click', () => this.switchCamera());
    
    // Manual entry
    document.getElementById('btn-manual-entry')?.addEventListener('click', () => this.toggleManualEntry());
    document.getElementById('btn-submit-manual')?.addEventListener('click', () => this.submitManualCode());
    document.getElementById('manual-code-input')?.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') this.submitManualCode();
    });
    
    // History management
    document.getElementById('btn-clear-history')?.addEventListener('click', () => this.clearHistory());
    document.getElementById('btn-export-scans')?.addEventListener('click', () => this.exportScans());
    document.getElementById('btn-process-scans')?.addEventListener('click', () => this.processScans());
    
    // Close scanner
    document.querySelector('.btn-close-scanner')?.addEventListener('click', () => this.close());
  }

  /**
   * Start scanning
   */
  async startScanning() {
    try {
      // Check camera permission
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Camera not supported on this device');
      }

      // Show scanner view
      document.getElementById('scanner-view').style.display = 'block';
      document.getElementById('manual-entry-form').style.display = 'none';
      document.getElementById('btn-start-scan').style.display = 'none';
      document.getElementById('btn-stop-scan').style.display = 'inline-flex';

      // Initialize Html5Qrcode (if library is loaded)
      if (typeof Html5Qrcode !== 'undefined') {
        this.scanner = new Html5Qrcode("qr-reader");
        
        const config = {
          fps: this.options.fps,
          qrbox: this.options.qrbox,
          aspectRatio: this.options.aspectRatio,
          disableFlip: this.options.disableFlip,
          formatsToSupport: this.options.formatsToSupport
        };

        await this.scanner.start(
          { facingMode: this.currentCamera },
          config,
          (decodedText, decodedResult) => this.onScanSuccess(decodedText, decodedResult),
          (errorMessage) => {
            // Ignore frequent errors
            if (!errorMessage.includes('NotFoundException')) {
              console.warn('Scanner error:', errorMessage);
            }
          }
        );

        this.isScanning = true;
      } else {
        // Fallback: Show manual entry
        this.showNotification('Camera library not loaded. Please use manual entry.', 'warning');
        this.toggleManualEntry();
      }
    } catch (error) {
      console.error('Failed to start scanning:', error);
      this.showNotification('Failed to access camera. Please check permissions.', 'error');
      this.options.onError(error);
      this.stopScanning();
    }
  }

  /**
   * Stop scanning
   */
  async stopScanning() {
    if (this.scanner && this.isScanning) {
      try {
        await this.scanner.stop();
        this.scanner.clear();
      } catch (error) {
        console.error('Error stopping scanner:', error);
      }
    }

    this.isScanning = false;
    document.getElementById('scanner-view').style.display = 'none';
    document.getElementById('btn-start-scan').style.display = 'inline-flex';
    document.getElementById('btn-stop-scan').style.display = 'none';
  }

  /**
   * Switch camera (front/back)
   */
  async switchCamera() {
    if (!this.isScanning) return;

    this.currentCamera = this.currentCamera === 'environment' ? 'user' : 'environment';
    await this.stopScanning();
    await this.startScanning();
  }

  /**
   * Handle successful scan
   */
  onScanSuccess(decodedText, decodedResult) {
    // Check for duplicates
    if (!this.options.allowDuplicates && this.scanHistory.some(item => item.code === decodedText)) {
      this.showNotification('Duplicate code detected', 'warning');
      return;
    }

    // Add to history
    const scanItem = {
      code: decodedText,
      format: decodedResult.result.format?.formatName || 'Unknown',
      timestamp: new Date().toISOString(),
      method: 'camera'
    };

    this.addToHistory(scanItem);

    // Callback
    this.options.onScan(scanItem);

    // Show success feedback
    this.showNotification(`Scanned: ${decodedText}`, 'success');

    // Auto-stop in single mode
    if (!this.options.batchMode && this.options.autoStop) {
      setTimeout(() => this.stopScanning(), 1000);
    }

    // Play beep sound (optional)
    this.playBeep();
  }

  /**
   * Toggle manual entry form
   */
  toggleManualEntry() {
    const form = document.getElementById('manual-entry-form');
    const isVisible = form.style.display === 'block';
    
    form.style.display = isVisible ? 'none' : 'block';
    
    if (!isVisible) {
      document.getElementById('manual-code-input')?.focus();
      if (this.isScanning) {
        this.stopScanning();
      }
    }
  }

  /**
   * Submit manual code
   */
  submitManualCode() {
    const input = document.getElementById('manual-code-input');
    const code = input.value.trim();

    if (!code) {
      this.showNotification('Please enter a code', 'warning');
      return;
    }

    // Check for duplicates
    if (!this.options.allowDuplicates && this.scanHistory.some(item => item.code === code)) {
      this.showNotification('Duplicate code detected', 'warning');
      return;
    }

    // Add to history
    const scanItem = {
      code: code,
      format: 'Manual Entry',
      timestamp: new Date().toISOString(),
      method: 'manual'
    };

    this.addToHistory(scanItem);

    // Callback
    this.options.onScan(scanItem);

    // Clear input
    input.value = '';
    input.focus();

    // Show success
    this.showNotification(`Added: ${code}`, 'success');
  }

  /**
   * Add item to scan history
   */
  addToHistory(scanItem) {
    this.scanHistory.unshift(scanItem);

    // Limit history size
    if (this.scanHistory.length > this.options.maxHistory) {
      this.scanHistory = this.scanHistory.slice(0, this.options.maxHistory);
    }

    this.updateHistoryUI();
    this.saveHistory();
  }

  /**
   * Update history UI
   */
  updateHistoryUI() {
    const listEl = document.getElementById('scan-history-list');
    const countEl = document.getElementById('scan-count-value');

    // Update count
    if (countEl) {
      countEl.textContent = this.scanHistory.length;
    }

    // Update list
    if (listEl) {
      if (this.scanHistory.length === 0) {
        listEl.innerHTML = `
          <div class="scan-history-empty">
            <i class="bi bi-inbox"></i>
            <p>No scans yet</p>
          </div>
        `;
      } else {
        listEl.innerHTML = this.scanHistory.map((item, index) => `
          <div class="scan-history-item" data-index="${index}">
            <div class="scan-history-item-content">
              <div class="scan-history-code">${this.escapeHtml(item.code)}</div>
              <div class="scan-history-meta">
                <span class="scan-history-format">${item.format}</span>
                <span class="scan-history-time">${this.formatTime(item.timestamp)}</span>
              </div>
            </div>
            <button type="button" class="btn-remove-scan" data-index="${index}" aria-label="Remove">
              <i class="bi bi-x-lg"></i>
            </button>
          </div>
        `).join('');

        // Bind remove buttons
        listEl.querySelectorAll('.btn-remove-scan').forEach(btn => {
          btn.addEventListener('click', (e) => {
            const index = parseInt(e.currentTarget.dataset.index);
            this.removeFromHistory(index);
          });
        });
      }
    }
  }

  /**
   * Remove item from history
   */
  removeFromHistory(index) {
    this.scanHistory.splice(index, 1);
    this.updateHistoryUI();
    this.saveHistory();
  }

  /**
   * Clear all history
   */
  clearHistory() {
    if (this.scanHistory.length === 0) return;

    if (confirm('Clear all scanned codes?')) {
      this.scanHistory = [];
      this.updateHistoryUI();
      this.saveHistory();
      this.showNotification('History cleared', 'info');
    }
  }

  /**
   * Export scans to CSV
   */
  exportScans() {
    if (this.scanHistory.length === 0) {
      this.showNotification('No scans to export', 'warning');
      return;
    }

    const csv = [
      ['Code', 'Format', 'Method', 'Timestamp'],
      ...this.scanHistory.map(item => [
        item.code,
        item.format,
        item.method,
        item.timestamp
      ])
    ].map(row => row.join(',')).join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `scans_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);

    this.showNotification('Scans exported', 'success');
  }

  /**
   * Process scans (callback to parent)
   */
  processScans() {
    if (this.scanHistory.length === 0) {
      this.showNotification('No scans to process', 'warning');
      return;
    }

    // Trigger custom event
    const event = new CustomEvent('scansProcessed', {
      detail: { scans: this.scanHistory }
    });
    this.container.dispatchEvent(event);
  }

  /**
   * Save history to localStorage
   */
  saveHistory() {
    try {
      localStorage.setItem(`scanner_history_${this.containerId}`, JSON.stringify(this.scanHistory));
    } catch (error) {
      console.warn('Failed to save scan history:', error);
    }
  }

  /**
   * Load history from localStorage
   */
  loadHistory() {
    try {
      const saved = localStorage.getItem(`scanner_history_${this.containerId}`);
      if (saved) {
        this.scanHistory = JSON.parse(saved);
        this.updateHistoryUI();
      }
    } catch (error) {
      console.warn('Failed to load scan history:', error);
    }
  }

  /**
   * Show notification
   */
  showNotification(message, type = 'info') {
    // Use existing notification system or create simple toast
    console.log(`[${type.toUpperCase()}] ${message}`);
    
    // TODO: Integrate with global notification system
    // For now, use browser notification API if available
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('Scanner', { body: message });
    }
  }

  /**
   * Play beep sound
   */
  playBeep() {
    try {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      oscillator.frequency.value = 800;
      oscillator.type = 'sine';
      gainNode.gain.value = 0.1;

      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.1);
    } catch (error) {
      // Silently fail if audio not supported
    }
  }

  /**
   * Close scanner
   */
  async close() {
    await this.stopScanning();
    this.container.innerHTML = '';
    
    // Trigger close event
    const event = new CustomEvent('scannerClosed');
    this.container.dispatchEvent(event);
  }

  /**
   * Utility: Escape HTML
   */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Utility: Format timestamp
   */
  formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    
    return date.toLocaleDateString();
  }
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = BarcodeScanner;
}
