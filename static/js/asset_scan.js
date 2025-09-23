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
    scanResult.classList.remove('d-none');
    scanError.classList.add('d-none');
    assetDetails.innerHTML = `<table class='table table-bordered'>
      <tr><th>Name</th><td>${(data.dynamic_data && (data.dynamic_data.name || data.dynamic_data.serial_number)) || ''}</td></tr>
      <tr><th>Model</th><td>${(data.dynamic_data && data.dynamic_data.model) || ''}</td></tr>
      <tr><th>Category</th><td>${data.category_name || ''}</td></tr>
      <tr><th>Status</th><td>${data.status || ''}</td></tr>
      <tr><th>Location</th><td>${(data.dynamic_data && data.dynamic_data.location) || ''}</td></tr>
      <tr><th>Assigned To</th><td>${data.assigned_to || ''}</td></tr>
      <tr><th>Created</th><td>${data.created_at || ''}</td></tr>
    </table>
    <a href='/assets/${data.id}/' class='btn btn-outline-primary btn-sm'>View Full Details</a>`;
  }

  function showError(msg) {
    scanError.textContent = msg;
    scanError.classList.remove('d-none');
    scanResult.classList.add('d-none');
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
  function startScanner() {
    if (!window.Html5Qrcode) {
      showError('QR scanner library not available. Please use manual input.');
      return;
    }
    
    // Secure context check
    if (location.protocol !== 'https:' && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
      showError('Camera requires HTTPS or localhost.');
      return;
    }
    
    const elemId = 'qr-reader';
    scanner = new Html5Qrcode(elemId);
    
    Html5Qrcode.getCameras().then(cameras => {
      const cameraId = (cameras && cameras[0] && cameras[0].id) || null;
      if (!cameraId) { 
        showError('No camera found. Please use manual input.'); 
        return; 
      }
      
      scanner.start(
        cameraId,
        { 
          fps: 10, 
          qrbox: { width: 250, height: 250 },
          aspectRatio: 1.0
        },
        decodedText => {
          stopScanner();
          fetchAssetByCode(decodedText);
        },
        errorMessage => {
          // Ignore continuous scanning errors
        }
      ).then(() => {
        startBtn.disabled = true; 
        stopBtn.disabled = false;
        console.log('QR Scanner started successfully');
      }).catch(err => {
        showError('Camera initialization failed: ' + err);
      });
    }).catch(err => {
      showError('Unable to access camera: ' + err);
    });
  }

  function stopScanner() {
    if (scanner) {
      scanner.stop().then(() => {
        scanner.clear();
      }).finally(() => {
        startBtn.disabled = false; stopBtn.disabled = true;
      });
    }
  }

  startBtn && startBtn.addEventListener('click', startScanner);
  stopBtn && stopBtn.addEventListener('click', stopScanner);

  manualForm && manualForm.addEventListener('submit', function(e) {
    e.preventDefault();
    if (manualCode.value.trim()) {
      fetchAssetByCode(manualCode.value.trim());
    }
  });
})();



