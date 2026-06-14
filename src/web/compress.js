/* Compress / scale view */

const CompressUI = (function () {
  let videos = [];
  let selectedIndex = -1;
  let jobId = null;
  let processing = false;

  const METRIC_KEYS = [
    'Total Files:', 'Files Processed:', 'Current File:',
    'Frames Processed:', 'Progress:', 'Average Frame Rate:',
    'Time Running:', 'Time Remaining:',
  ];

  function fillSelect(id, options, value) {
    const sel = document.getElementById(id);
    sel.innerHTML = '';
    options.forEach(o => {
      const opt = document.createElement('option');
      opt.value = o;
      opt.textContent = o;
      sel.appendChild(opt);
    });
    if (value) sel.value = value;
  }

  function initMetrics() {
    const grid = document.getElementById('compress-metrics');
    grid.innerHTML = '';
    METRIC_KEYS.forEach(key => {
      const div = document.createElement('div');
      div.className = 'progress-metric';
      div.id = 'metric-' + key.replace(/[^a-z]/gi, '');
      div.innerHTML = `<strong>${key}</strong> <span>-</span>`;
      grid.appendChild(div);
    });
  }

  function updateMetric(key, value) {
    const id = 'metric-' + key.replace(/[^a-z]/gi, '');
    const el = document.getElementById(id);
    if (el) {
      const span = el.querySelector('span');
      if (span) span.textContent = value;
    }
    if (key === 'Progress:') {
      const pct = parseFloat(String(value).replace('%', '')) || 0;
      document.getElementById('compress-progress-bar').style.width = pct + '%';
      const wrap = document.getElementById('compress-progress-bar-wrap');
      wrap.setAttribute('aria-valuenow', String(Math.round(pct)));
    }
  }

  function renderTable() {
    const tbody = document.getElementById('compress-tbody');
    tbody.innerHTML = '';
    videos.forEach((v, i) => {
      const tr = document.createElement('tr');
      tr.dataset.index = i;
      if (i === selectedIndex) tr.classList.add('selected');
      tr.innerHTML = `
        <td>${escapeHtml(v.file || '')}</td>
        <td>${escapeHtml(v.resolution || '')}</td>
        <td>${escapeHtml(v.fps || '')}</td>
        <td>${escapeHtml(v.codec || '')}</td>
        <td>${escapeHtml(v.duration || '')}</td>
        <td>${escapeHtml(v.size || '')}</td>
        <td>${escapeHtml(v.orientation || '')}</td>
        <td>${escapeHtml(v.status || 'Pending')}</td>`;
      tr.addEventListener('click', () => {
        selectedIndex = i;
        renderTable();
      });
      tr.addEventListener('dblclick', () => {
        v.is_vertical = !v.is_vertical;
        v.orientation = v.is_vertical ? 'Vertical' : 'Horizontal';
        renderTable();
      });
      tbody.appendChild(tr);
    });
  }

  function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function appendLog(line) {
    const log = document.getElementById('compress-log');
    log.textContent += line;
    log.scrollTop = log.scrollHeight;
  }

  function getSettings() {
    return {
      use_gpu: document.getElementById('compress-gpu').checked,
      use_all_cores: document.getElementById('compress-all-cores').checked,
      cap_cpu_50: document.getElementById('compress-cap-50').checked,
      fps: document.getElementById('compress-fps').value,
      resolution: document.getElementById('compress-resolution').value,
      crf: document.getElementById('compress-crf').value,
      preset: document.getElementById('compress-preset').value,
      output_folder: document.getElementById('compress-output').value,
    };
  }

  async function loadOptions() {
    const r = await window.pywebview.api.compress_get_options();
    if (!r || r.status !== 'success') return;
    fillSelect('compress-fps', r.fps_options, r.defaults.fps);
    fillSelect('compress-resolution', r.resolution_options, r.defaults.resolution);
    fillSelect('compress-crf', r.crf_options, r.defaults.crf);
    fillSelect('compress-preset', r.preset_options, r.defaults.preset);
    document.getElementById('compress-output').value = r.defaults.output_folder || '';
    const gpu = document.getElementById('compress-gpu');
    gpu.disabled = !r.gpu_available;
    if (!r.gpu_available) gpu.checked = false;
  }

  async function addPaths(paths) {
    if (!paths.length) return;
    const r = await window.pywebview.api.compress_probe_videos(paths);
    if (r && r.status === 'success') {
      r.videos.forEach(v => {
        if (!videos.find(x => x.path === v.path)) videos.push(v);
      });
      renderTable();
    }
  }

  async function init() {
    initMetrics();
    await loadOptions();

    document.getElementById('compress-add-files').addEventListener('click', async () => {
      const opts = await window.pywebview.api.compress_get_options();
      const dir = (opts && opts.last_input_folder) || '';
      const r = await window.pywebview.api.pick_files(dir, '*.mp4;*.mkv;*.avi;*.mov;*.flv;*.wmv');
      if (r && r.status === 'success') await addPaths(r.paths);
    });

    document.getElementById('compress-add-folder').addEventListener('click', async () => {
      const opts = await window.pywebview.api.compress_get_options();
      const r = await window.pywebview.api.pick_folder((opts && opts.last_input_folder) || '', 'Select folder', 'input');
      if (r && r.status === 'success' && r.path) {
        const scan = await window.pywebview.api.join_scan_folder(r.path);
        if (scan && scan.status === 'success') await addPaths(scan.files || []);
      }
    });

    document.getElementById('compress-browse-output').addEventListener('click', async () => {
      const r = await window.pywebview.api.pick_folder(
        document.getElementById('compress-output').value, 'Output folder', 'output');
      if (r && r.status === 'success' && r.path) {
        document.getElementById('compress-output').value = r.path;
      }
    });

    document.getElementById('compress-remove').addEventListener('click', () => {
      if (selectedIndex >= 0) {
        videos.splice(selectedIndex, 1);
        selectedIndex = -1;
        renderTable();
      }
    });

    document.getElementById('compress-reset').addEventListener('click', async () => {
      await loadOptions();
      document.getElementById('compress-gpu').checked = false;
      document.getElementById('compress-all-cores').checked = false;
      document.getElementById('compress-cap-50').checked = false;
      const r = await window.pywebview.api.compress_get_options();
      if (r && r.status === 'success') {
        document.getElementById('compress-fps').value = r.fps_options[0];
        document.getElementById('compress-resolution').value = r.resolution_options[0];
        document.getElementById('compress-crf').value = String(r.crf_max);
        document.getElementById('compress-preset').value = 'ultrafast';
      }
    });

    document.getElementById('compress-run').addEventListener('click', async () => {
      if (processing) return;
      if (!videos.length) { showAlert('Add videos first.', 'error'); return; }
      const settings = getSettings();
      if (!settings.output_folder) { showAlert('Select output folder.', 'error'); return; }
      processing = true;
      document.getElementById('compress-log').textContent = '';
      document.getElementById('compress-run').disabled = true;
      const payload = {
        videos: videos.map(v => ({ path: v.path, is_vertical: !!v.is_vertical })),
        settings,
      };
      const r = await window.pywebview.api.compress_start(payload);
      if (!r || r.status !== 'success') {
        showAlert((r && r.message) || 'Failed to start', 'error');
        processing = false;
        document.getElementById('compress-run').disabled = false;
        return;
      }
      jobId = r.job_id;
    });

    document.getElementById('compress-cancel').addEventListener('click', async () => {
      await window.pywebview.api.compress_cancel(jobId || '');
    });
  }

  window.onCompressProgress = function (data) {
    Object.keys(data).forEach(k => {
      if (METRIC_KEYS.includes(k)) updateMetric(k, data[k]);
      if (k === 'Frames Processed:') updateMetric('Frames Processed:', data[k]);
    });
    if (data.percent !== undefined) updateMetric('Progress:', data.percent.toFixed(2) + '%');
  };

  window.onCompressLog = function (data) {
    if (data.line) appendLog(data.line);
  };

  window.onCompressFileStatus = function (data) {
    if (data.index >= 0 && videos[data.index]) {
      videos[data.index].status = data.status;
      renderTable();
    }
  };

  window.onCompressComplete = function (data) {
    processing = false;
    jobId = null;
    document.getElementById('compress-run').disabled = false;
    showAlert('Batch processing finished. Processed: ' + (data.processed || 0), 'success');
  };

  return { init, loadOptions };
})();

window.CompressUI = CompressUI;
