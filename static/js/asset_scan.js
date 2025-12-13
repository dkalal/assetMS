// QR scanning using html5-qrcode (works for QR; no barcodes). Complies with CSP.
(function() {
  const startBtn = document.getElementById('start-scan');
  const stopBtn = document.getElementById('stop-scan');
  const scanResult = document.getElementById('scan-result');
  const assetDetails = document.getElementById('asset-details');
  const scanError = document.getElementById('scan-error');
  const manualForm = document.getElementById('manual-form');
  const manualCode = document.getElementById('manual-code');

  function showAssetDetails(data) {
    if (scanResult) scanResult.classList.remove('d-none');
    if (scanError) scanError.classList.add('d-none');
    if (assetDetails) {
      assetDetails.innerHTML = `<table class='table table-bordered'>
        <tr><th>Name</th><td>${escapeHtml((data.dynamic_data && (data.dynamic_data.name || data.dynamic_data.serial_number)) || '')}</td></tr>
        <tr><th>Model</th><td>${escapeHtml((data.dynamic_data && data.dynamic_data.model) || '')}</td></tr>
        <tr><th>Category</th><td>${escapeHtml(data.category_name || '')}</td></tr>
        <tr><th>Status</th><td>${escapeHtml(data.status || '')}</td></tr>
        <tr><th>Location</th><td>${escapeHtml((data.dynamic_data && data.dynamic_data.location) || '')}</td></tr>
        <tr><th>Assigned To</th><td>${escapeHtml(data.assigned_to || '')}</td></tr>
        <tr><th>Created</th><td>${escapeHtml(data.created_at || '')}</td></tr>
      </table>
      <a href='/assets/${data.id}/' class='btn btn-outline-primary btn-sm'>View Full Details</a>`;
    }
  }

  function showError(msg) {
    if (scanError) {
      scanError.textContent = msg;
      scanError.classList.remove('d-none');
    }
    if (scanResult) scanResult.classList.add('d-none');
  }

  function fetchAssetByCode(code) {
    fetch(`/api/asset-by-code/?code=${encodeURIComponent(code)}`)
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          showAssetDetails(data.asset);
        } else {
          showError('Asset not found.');
        }
      })
      .catch(() => showError('Error fetching asset.'));
  }

  let scanner = null;
  let scannerUI = null;
  
  async function startScanner() {
    if (!window.Html5Qrcode) {
      showError('QR scanner library not available. Please use manual input.');
      return;
    }
    
    if (!window.CameraDiagnostics) {
      showError('Camera diagnostics not available. Please refresh the page.');
      return;
    }
    
    // Initialize UI enhancements
    if (window.QRScannerUI) {
      scannerUI = new window.QRScannerUI('qr-reader');
      scannerUI.activate();
    }

    // Run comprehensive camera diagnostics
    const diagnostics = await window.CameraDiagnostics.checkCameraAccess();
    
    if (!diagnostics.cameraAccessible) {
      const errorMsg = window.CameraDiagnostics.getErrorMessage(diagnostics);
      
      // Try to request permission if it's a permission issue
      if (diagnostics.permissions === 'prompt' || diagnostics.cameraError?.includes('NotAllowedError')) {
        showError('Requesting camera permission...');
        const permissionResult = await window.CameraDiagnostics.requestCameraPermission();
        
        if (!permissionResult.success) {
          showError(`Camera permission required: ${permissionResult.message}`);
          return;
        }
        
        // Retry diagnostics after permission granted
        const retryDiagnostics = await window.CameraDiagnostics.checkCameraAccess();
        if (!retryDiagnostics.cameraAccessible) {
          showError(window.CameraDiagnostics.getErrorMessage(retryDiagnostics));
          return;
        }
      } else {
        showError(errorMsg);
        return;
      }
    }
    
    const elemId = 'qr-reader';
    scanner = new Html5Qrcode(elemId);
    
    try {
      const cameras = await Html5Qrcode.getCameras();
      
      if (!cameras || cameras.length === 0) {
        showError('No cameras available. Please connect a camera and try again.');
        return;
      }
      
      // Prefer back camera for QR scanning
      const backCamera = cameras.find(camera => 
        camera.label.toLowerCase().includes('back') || 
        camera.label.toLowerCase().includes('rear') ||
        camera.label.toLowerCase().includes('environment')
      );
      
      const cameraId = backCamera ? backCamera.id : cameras[0].id;
      
      // Use enhanced scanner if available, fallback to basic
      if (window.EnhancedQRScanner) {
        const enhancedScanner = new window.EnhancedQRScanner(elemId);
        scanner = enhancedScanner; // Store reference for stopping
        
        await enhancedScanner.start(
          (decodedText) => {
            if (scannerUI) scannerUI.showDetectionSuccess();
            setTimeout(() => {
              stopScanner();
              fetchAssetByCode(decodedText);
            }, 500);
          },
          (error) => {
            showError(`Enhanced scanner error: ${error.message}`);
          }
        );
      } else {
        // Fallback to basic scanner with enhanced settings
        await scanner.start(
          cameraId,
          { 
            fps: 15,
            qrbox: function(viewfinderWidth, viewfinderHeight) {
              const minEdge = Math.min(viewfinderWidth, viewfinderHeight);
              const qrboxSize = Math.floor(minEdge * 0.7);
              return { width: qrboxSize, height: qrboxSize };
            },
            aspectRatio: 1.0,
            disableFlip: false,
            videoConstraints: {
              facingMode: { ideal: "environment" },
              focusMode: { ideal: "continuous" }
            }
          },
          decodedText => {
            if (scannerUI) scannerUI.showDetectionSuccess();
            setTimeout(() => {
              stopScanner();
              fetchAssetByCode(decodedText);
            }, 500);
          },
          errorMessage => {
            // Ignore continuous scanning errors
          }
        );
      }
      
      if (startBtn) startBtn.disabled = true;
      if (stopBtn) stopBtn.disabled = false;
      console.log('QR Scanner started successfully');
      
    } catch (err) {
      showError(`Scanner initialization failed: ${err.message || err}`);
    }
  }

  function stopScanner() {
    if (scanner) {
      if (scanner.stop && typeof scanner.stop === 'function') {
        scanner.stop().then(() => {
          if (scanner.clear && typeof scanner.clear === 'function') {
            scanner.clear();
          }
        }).finally(() => {
          if (startBtn) startBtn.disabled = false;
          if (stopBtn) stopBtn.disabled = true;
          if (scannerUI) scannerUI.deactivate();
        });
      } else {
        // Handle enhanced scanner
        if (startBtn) startBtn.disabled = false;
        if (stopBtn) stopBtn.disabled = true;
      }
    }
  }

  startBtn && startBtn.addEventListener('click', startScanner);
  stopBtn && stopBtn.addEventListener('click', stopScanner);

  manualForm && manualForm.addEventListener('submit', function(e) {
    e.preventDefault();
    if (manualCode && manualCode.value.trim()) {
      fetchAssetByCode(manualCode.value.trim());
    }
  });
  
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
})();



