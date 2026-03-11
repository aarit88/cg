document.addEventListener('DOMContentLoaded', () => {
  // DOM
  const fileInput = document.getElementById('file-input');
  const uploadArea = document.getElementById('upload-area');

  const uploadForm = document.getElementById('upload-form');
  const blurType = document.getElementById('blur-type');
  const quantizer = document.getElementById('quantizer');
  const numColors = document.getElementById('num-colors');
  const lineStrength = document.getElementById('line-strength');
  const targetLongSide = document.getElementById('target-long-side');
  const upscaleSmall = document.getElementById('upscale-small');

  const labelColors = document.getElementById('label-colors');
  const labelEdge = document.getElementById('label-edge');

  const stage = document.getElementById('stage');
  const stageInner = document.getElementById('stage-inner');
  const stageTools = document.getElementById('stage-tools');
  const beforeImg = document.getElementById('img-before');
  const afterImg = document.getElementById('img-after');
  const handle = document.getElementById('ba-handle');
  const empty = document.getElementById('empty-state');
  const loader = document.getElementById('loader');

  const bottomBar = document.getElementById('bottom-bar');
  const downloadBtn = document.getElementById('download-btn');
  const status = document.getElementById('status');

  const zoomInBtn = document.getElementById('zoom-in');
  const zoomOutBtn = document.getElementById('zoom-out');
  const zoomFitBtn = document.getElementById('zoom-fit');
  const zoomLevelLabel = document.getElementById('zoom-level');
  const openFileBtn = document.getElementById('open-file');

  // State
  let zoom = 1.0;
  let split = 50;
  let hasImage = false;

  // ===== helpers =====
  const setZoom = (z) => {
    zoom = Math.max(0.25, Math.min(4, z));
    stageInner.style.transform = `scale(${zoom})`;
    zoomLevelLabel.textContent = `${Math.round(zoom * 100)}%`;
  };
  const fitToStage = () => {
    const pad = 32;
    const rect = stage.getBoundingClientRect();
    const w = rect.width - pad;
    const h = rect.height - pad;
    const baseW = stageInner.clientWidth || 1200;
    const baseH = stageInner.clientHeight || 800;
    const factor = Math.max(0.25, Math.min(4, Math.min(w / baseW, h / baseH)));
    setZoom(factor);
  };
  const setSplit = (pct) => {
    split = Math.max(0, Math.min(100, pct));
    const right = 100 - split;
    afterImg.style.clipPath = `inset(0 ${right}% 0 0)`;
    handle.style.left = `${split}%`;
    handle.setAttribute('aria-valuenow', String(split));
  };
  const setStatus = (msg) => { status.textContent = msg; };
  const showCanvas = () => {
    stage.classList.add('has-image');
    if (empty) empty.hidden = true;
    bottomBar.hidden = false;
    stageTools.hidden = false;
    beforeImg.style.display = 'block';
    afterImg.style.display = 'block';
  };

  // labels + live range fill
  const fmt = (val, step) => (String(step).includes('.') ? Number(val).toFixed(1) : String(val));
  const refreshLabels = () => {
    labelColors.textContent = fmt(numColors.value, numColors.step || 1);
    labelEdge.textContent   = fmt(lineStrength.value, lineStrength.step || 1);
    // paint the filled portion of the track (WebKit)
    const pct1 = (numColors.value - numColors.min) / (numColors.max - numColors.min) * 100;
    const pct2 = (lineStrength.value - lineStrength.min) / (lineStrength.max - lineStrength.min) * 100;
    numColors.style.setProperty('--_fill', `${pct1}%`);
    lineStrength.style.setProperty('--_fill', `${pct2}%`);
  };

  // init
  refreshLabels();
  setSplit(50);
  setZoom(1);

  // ===== Sparkle effect =====
  const SPARKLE_COLORS = ['#c4b5fd','#818cf8','#f5d0fe','#fce7f3','#6366f1','#a78bfa'];
  const spawnSparkles = (x, y, count = 12) => {
    for (let i = 0; i < count; i++) {
      const el = document.createElement('div');
      el.className = 'sparkle-particle';
      const angle = (Math.PI * 2 * i) / count + (Math.random() - .5) * .5;
      const dist = 30 + Math.random() * 50;
      const tx = Math.cos(angle) * dist;
      const ty = Math.sin(angle) * dist;
      el.style.cssText = `
        left:${x}px; top:${y}px;
        background:${SPARKLE_COLORS[i % SPARKLE_COLORS.length]};
        --tx:${tx}px; --ty:${ty}px;
        width:${4 + Math.random() * 4}px;
        height:${4 + Math.random() * 4}px;
      `;
      document.body.appendChild(el);
      el.addEventListener('animationend', () => el.remove());
    }
  };

  // ===== Dropzone =====
  ['dragenter','dragover'].forEach(ev =>
    uploadArea.addEventListener(ev, e => {
      e.preventDefault();
      uploadArea.classList.add('drag-over');
    })
  );
  ['dragleave','drop'].forEach(ev =>
    uploadArea.addEventListener(ev, e => {
      e.preventDefault();
      uploadArea.classList.remove('drag-over');
    })
  );
  uploadArea.addEventListener('drop', e => {
    const f = e.dataTransfer.files?.[0];
    if (f) { fileInput.files = e.dataTransfer.files; loadFile(f); }
  });

  // topbar
  openFileBtn.addEventListener('click', () => fileInput.click());

  // zoom
  zoomInBtn.addEventListener('click', () => setZoom(zoom * 1.1));
  zoomOutBtn.addEventListener('click', () => setZoom(zoom / 1.1));
  zoomFitBtn.addEventListener('click', fitToStage);
  window.addEventListener('resize', () => { if (hasImage) fitToStage(); });

  // range labels live
  ['input','change','keyup','pointerup'].forEach(ev => {
    numColors.addEventListener(ev, refreshLabels);
    lineStrength.addEventListener(ev, refreshLabels);
  });

  // file load
  const loadFile = (file) => {
    const reader = new FileReader();
    reader.onload = e => {
      beforeImg.src = e.target.result;
      afterImg.removeAttribute('src');
      downloadBtn.hidden = true;
      showCanvas();
      hasImage = true;
      fitToStage();
      setStatus('Image loaded');
    };
    reader.readAsDataURL(file);
  };
  fileInput.addEventListener('change', function () {
    const f = this.files?.[0];
    if (f) loadFile(f);
  });

  // ===== Compare slider — mouse + touch + glow =====
  const onMove = (clientX) => {
    const rect = stageInner.getBoundingClientRect();
    const pct = ((clientX - rect.left) / rect.width) * 100;
    setSplit(pct);
  };
  let dragging = false;

  const startDrag = () => { dragging = true; handle.classList.add('dragging'); };
  const endDrag = () => {
    if (!dragging) return;
    dragging = false;
    handle.classList.remove('dragging');
    if (split < 3) setSplit(0);
    if (split > 97) setSplit(100);
  };

  handle.addEventListener('mousedown', e => { startDrag(); e.preventDefault(); });
  stageInner.addEventListener('mousedown', e => { startDrag(); onMove(e.clientX); });
  window.addEventListener('mousemove', e => { if (dragging) onMove(e.clientX); });
  window.addEventListener('mouseup', endDrag);

  // touch
  handle.addEventListener('touchstart', e => { startDrag(); e.preventDefault(); }, { passive:false });
  stageInner.addEventListener('touchstart', e => { startDrag(); const t = e.touches[0]; onMove(t.clientX); }, { passive:true });
  window.addEventListener('touchmove', e => { if (!dragging) return; const t = e.touches[0]; onMove(t.clientX); }, { passive:true });
  window.addEventListener('touchend', endDrag);

  // keyboard + dblclick reset
  handle.addEventListener('keydown', e => { if (e.key === 'ArrowLeft') setSplit(split - 2); if (e.key === 'ArrowRight') setSplit(split + 2); });
  stageInner.addEventListener('dblclick', () => setSplit(50));

  // ===== Keyboard shortcuts =====
  document.addEventListener('keydown', e => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
    if (e.key === 'o' || e.key === 'O') fileInput.click();
    if (e.key === 'r' || e.key === 'R') uploadForm.requestSubmit?.() || uploadForm.dispatchEvent(new Event('submit'));
    if (e.key === 'f' || e.key === 'F') fitToStage();
    if (e.key === '+' || e.key === '=') setZoom(zoom * 1.1);
    if (e.key === '-') setZoom(zoom / 1.1);
  });

  // ===== Submit =====
  uploadForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const srcFile = fileInput.files?.[0];
    if (!srcFile) { setStatus('Select an image first'); return; }

    stage.classList.add('has-image');
    if (empty) empty.hidden = true;

    loader.hidden = false; setStatus('Processing…');

    const formData = new FormData(uploadForm);
    formData.set('file', srcFile);
    formData.set('blur_type', blurType.value);
    formData.set('quantizer', quantizer.value);
    formData.set('num_colors', numColors.value);
    formData.set('line_strength', lineStrength.value);
    formData.set('target_long_side', targetLongSide.value);
    formData.set('upscale_small', upscaleSmall.checked ? 'true' : 'false');

    fetch('/upload', { method: 'POST', body: formData })
      .then(r => r.json())
      .then(data => {
        if (data.error) throw new Error(data.error);
        const url = data.cartoon_image_url + '?t=' + Date.now();
        afterImg.onload = () => {
          loader.hidden = true;
          downloadBtn.href = url;
          downloadBtn.hidden = false;
          setStatus('Done ✦');
          setSplit(50);
          fitToStage();

          // Sparkle burst on completion
          const stageRect = stage.getBoundingClientRect();
          const cx = stageRect.left + stageRect.width / 2;
          const cy = stageRect.top + stageRect.height / 2;
          spawnSparkles(cx, cy, 16);
        };
        afterImg.src = url;
      })
      .catch(err => {
        loader.hidden = true;
        setStatus(err.message || 'Failed');
      });
  });
});
