(() => {
  'use strict';
  const root = document.querySelector('[data-asset-scanner]');
  if (!root) return;

  const startButton = root.querySelector('[data-scan-start]');
  const stopButton = root.querySelector('[data-scan-stop]');
  const placeholder = root.querySelector('[data-scan-placeholder]');
  const status = root.querySelector('[data-scan-status]');
  const result = root.querySelector('[data-scan-result]');
  const codeInput = root.querySelector('#manual-asset-code');
  const historyContainer = root.querySelector('[data-recent-scans]');
  let scanner = null;
  let scanning = false;
  let recent = [];

  try {
    const stored = JSON.parse(localStorage.getItem('assetScannerRecent') || '[]');
    recent = Array.isArray(stored) ? stored.slice(0, 5) : [];
  } catch (_) {
    recent = [];
  }

  const setStatus = (message) => { status.textContent = message; };
  const setScanning = (active) => {
    scanning = active;
    startButton.classList.toggle('d-none', active);
    stopButton.classList.toggle('d-none', !active);
    if (placeholder) placeholder.classList.toggle('d-none', active);
  };

  const renderHistory = () => {
    historyContainer.replaceChildren();
    if (!recent.length) {
      const empty = document.createElement('p');
      empty.className = 'text-muted mb-0';
      empty.textContent = 'No recent lookups on this device.';
      historyContainer.append(empty);
      return;
    }
    recent.forEach((item) => {
      const row = document.createElement('div');
      row.className = 'asset-scanner__history-item';
      const text = document.createElement('span');
      const code = document.createElement('strong');
      const time = document.createElement('small');
      code.className = 'd-block';
      code.textContent = item.code;
      time.className = 'text-muted';
      time.textContent = new Date(item.timestamp).toLocaleString();
      text.append(code, time);
      const button = document.createElement('button');
      button.className = 'btn btn-sm btn-outline-primary';
      button.type = 'button';
      button.textContent = 'Look up';
      button.addEventListener('click', () => lookup(item.code));
      row.append(text, button);
      historyContainer.append(row);
    });
  };

  const remember = (code) => {
    recent = [{ code, timestamp: new Date().toISOString() }, ...recent.filter((item) => item.code !== code)].slice(0, 5);
    localStorage.setItem('assetScannerRecent', JSON.stringify(recent));
    renderHistory();
  };

  const stop = async () => {
    if (!scanner || !scanning) return;
    try {
      await scanner.stop();
      scanner.clear();
    } catch (_) {
      // The camera may already have stopped after a successful detection.
    }
    setScanning(false);
  };

  const showResult = (asset) => {
    root.querySelector('[data-result-name]').textContent = asset.dynamic_data?.name || 'Unnamed asset';
    root.querySelector('[data-result-category]').textContent = asset.category_name || 'Not specified';
    root.querySelector('[data-result-model]').textContent = asset.dynamic_data?.model || 'Not specified';
    const badge = root.querySelector('[data-result-status]');
    badge.textContent = asset.status || 'Unknown';
    badge.className = 'status-badge status-badge--' + String(asset.status || 'unknown').replace(/[^a-z0-9_-]/gi, '');
    root.querySelector('[data-result-link]').href = root.dataset.detailBase + asset.id + '/';
    result.classList.remove('d-none');
  };

  const lookup = async (code) => {
    const normalized = String(code || '').trim();
    if (!normalized) return;
    setStatus('Searching for the asset…');
    try {
      const url = new URL(root.dataset.lookupUrl, window.location.origin);
      url.searchParams.set('code', normalized);
      const response = await fetch(url, { headers: { Accept: 'application/json' } });
      const data = await response.json();
      if (!response.ok || !data.success) throw new Error('Asset not found.');
      showResult(data.asset);
      remember(normalized);
      setStatus('Asset found.');
    } catch (error) {
      result.classList.add('d-none');
      setStatus(error.message || 'Unable to complete the lookup.');
    }
  };

  const start = async () => {
    if (scanning) return;
    if (!window.Html5Qrcode || !navigator.mediaDevices) {
      setStatus('Camera scanning is unavailable. Use manual lookup.');
      codeInput.focus();
      return;
    }
    setStatus('Requesting camera access…');
    try {
      const cameras = await window.Html5Qrcode.getCameras();
      if (!cameras.length) throw new Error('No camera was found.');
      const preferred = cameras.find((camera) => /back|rear|environment/i.test(camera.label)) || cameras[0];
      scanner = new window.Html5Qrcode('scanner-preview');
      await scanner.start(
        preferred.id,
        { fps: 12, qrbox: (width, height) => {
          const size = Math.floor(Math.min(width, height) * .7);
          return { width: size, height: size };
        }},
        async (decodedText) => {
          await stop();
          await lookup(decodedText);
        },
        () => {}
      );
      setScanning(true);
      setStatus('Scanning. Hold the QR code inside the camera view.');
    } catch (error) {
      setScanning(false);
      setStatus(error.message || 'Camera access failed. Use manual lookup.');
    }
  };

  startButton.addEventListener('click', start);
  stopButton.addEventListener('click', async () => { await stop(); setStatus('Scanner stopped.'); });
  root.querySelector('[data-manual-form]').addEventListener('submit', (event) => {
    event.preventDefault();
    lookup(codeInput.value);
  });
  root.querySelector('[data-scan-reset]').addEventListener('click', () => {
    result.classList.add('d-none');
    codeInput.value = '';
    setStatus('Ready to scan.');
    codeInput.focus();
  });
  root.querySelector('[data-scan-history]').addEventListener('click', () => {
    const history = document.getElementById('scan-history-panel');
    history.scrollIntoView({ behavior: 'smooth', block: 'center' });
    history.focus();
  });
  window.addEventListener('pagehide', stop);
  renderHistory();
})();
