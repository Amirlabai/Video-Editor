/* ffmpegMagic — shared UI primitives */

const logQueue = [];
const logger = {
  info(msg) { logQueue.push(['INFO', msg]); },
  error(msg) { logQueue.push(['ERROR', msg]); },
};

let appData = {};
let updateInfo = null;
let modalReturnFocus = null;

function flushLogs() {
  if (!window.pywebview || !window.pywebview.api) return;
  while (logQueue.length) {
    const [level, msg] = logQueue.shift();
    window.pywebview.api.log_js(level, msg).catch(() => {});
  }
}

function uiLog(msg) {
  logger.info(msg);
  flushLogs();
}

function showAlert(message, type = 'info') {
  const region = document.getElementById('alert-region');
  while (region.children.length >= 3) {
    region.firstChild.remove();
  }
  const toast = document.createElement('div');
  toast.className = 'alert-toast ' + (type === 'error' ? 'error' : type === 'success' ? 'success' : '');
  toast.setAttribute('role', 'alert');
  toast.textContent = message;
  region.appendChild(toast);
  setTimeout(() => toast.remove(), 5000);
}

function trapModalFocus(overlay) {
  const modalId = overlay.id;
  const focusable = overlay.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  function onKey(e) {
    if (e.key === 'Escape') {
      hideModal(modalId);
      overlay.removeEventListener('keydown', onKey);
      return;
    }
    if (e.key !== 'Tab') return;
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }
  overlay.addEventListener('keydown', onKey);
  if (first) first.focus();
}

function showModal(id) {
  const el = document.getElementById(id);
  modalReturnFocus = document.activeElement;
  el.classList.add('open');
  trapModalFocus(el);
}

function hideModal(id) {
  document.getElementById(id).classList.remove('open');
  if (modalReturnFocus) modalReturnFocus.focus();
}

function navigate(view) {
  uiLog('Navigate: ' + view);
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  const section = document.getElementById('view-' + view);
  if (section) section.classList.add('active');
  document.querySelectorAll('.nav-btn[data-view]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.view === view);
  });
  if (view === 'settings') loadSettingsView();
  if (view === 'compress' && window.CompressUI) CompressUI.loadOptions();
}

async function loadSettingsView() {
  try {
    const pathR = await window.pywebview.api.settings_get_path();
    if (pathR && pathR.status === 'success') {
      document.getElementById('settings-config-path').textContent = pathR.file;
    }
    const sumR = await window.pywebview.api.settings_get_summary();
    if (sumR && sumR.status === 'success') {
      const s = sumR;
      const text = [
        'Performance Settings:',
        `  Use GPU: ${s.performance.use_gpu}`,
        `  Use All CPU Cores: ${s.performance.use_all_cores}`,
        `  Cap CPU 50%: ${s.performance.cap_cpu_50}`,
        '',
        'Encoding Defaults:',
        `  Default CRF: ${s.encoding.crf}`,
        `  Default Preset: ${s.encoding.preset}`,
        `  Default Resolution: ${s.encoding.resolution}`,
        '',
        'Last Used Folders:',
        `  Input: ${s.folders.last_input}`,
        `  Output: ${s.folders.last_output}`,
        `  Join Input: ${s.folders.last_join_input}`,
        `  Join Output: ${s.folders.last_join_output}`,
        '',
        'Note: Settings are saved automatically when you use the application.',
      ].join('\n');
      document.getElementById('settings-summary').textContent = text;
    }
    const ff = await window.pywebview.api.get_ffmpeg_notice();
    if (ff && ff.status === 'success') {
      const bundled = ff.bundled ? 'bundled with this application' : 'from system PATH';
      document.getElementById('settings-ffmpeg-credit').textContent =
        `Video processing uses FFmpeg (${bundled}). FFmpeg is a trademark of Fabrice Bellard.`;
      const notice = [
        ff.version_line || '',
        '',
        ff.notice || '',
        '',
        `Project: ${ff.project_url}`,
        `Legal: ${ff.legal_url}`,
        `Build source: ${ff.source_url}`,
      ].join('\n');
      document.getElementById('settings-ffmpeg-notice').textContent = notice;
    }
  } catch (e) {
    showAlert('Failed to load settings: ' + e, 'error');
  }
}

function showUpdateModal(info) {
  updateInfo = info;
  document.getElementById('update-modal-version').textContent =
    `Version ${info.latest_version} is available (you have ${info.current_version || 'unknown'}).`;
  document.getElementById('update-modal-notes').textContent = info.notes || '';
  showModal('update-modal');
}

async function checkForUpdates(force) {
  try {
    const r = await window.pywebview.api.check_for_updates(!!force);
    if (!r || r.status !== 'success') {
      showAlert((r && r.message) || 'Update check failed', 'error');
      return;
    }
    if (r.available || r.update_available) {
      showUpdateModal(r);
    } else if (force) {
      const msgs = {
        up_to_date: 'You are up to date.',
        recently_checked: 'Checked recently. Try again later.',
        snooze: 'Update snoozed.',
        skipped: 'This version was skipped.',
        offline: 'Could not reach update server.',
        disabled: 'Update checks are disabled.',
      };
      showAlert(msgs[r.reason] || 'No update available.', r.reason === 'offline' ? 'error' : 'info');
    }
  } catch (e) {
    showAlert('Update check error: ' + e, 'error');
  }
}

async function downloadUpdate() {
  if (!updateInfo) return;
  const url = updateInfo.installer_url || updateInfo.release_page;
  await window.pywebview.api.open_update_download(url);
  hideModal('update-modal');
}

async function dismissUpdateNotice(action) {
  if (!updateInfo) return;
  await window.pywebview.api.dismiss_update_notice(updateInfo.latest_version, action);
  hideModal('update-modal');
}

function setupNavigation() {
  document.querySelectorAll('[data-view]').forEach(btn => {
    btn.addEventListener('click', () => navigate(btn.dataset.view));
  });
  document.getElementById('btn-exit').addEventListener('click', () => {
    uiLog('Exit application');
    window.pywebview.api.exit_app();
  });
  navigate('home');
}

function setupSettings() {
  document.getElementById('settings-open-file').addEventListener('click', async () => {
    const r = await window.pywebview.api.open_config_in_editor();
    if (!r || r.status !== 'success') showAlert((r && r.message) || 'Failed', 'error');
    else showAlert('Configuration file opened.', 'success');
  });
  document.getElementById('settings-open-folder').addEventListener('click', async () => {
    const r = await window.pywebview.api.settings_get_path();
    if (r && r.status === 'success') {
      const openR = await window.pywebview.api.open_path_in_explorer(r.directory);
      if (!openR || openR.status !== 'success') {
        showAlert((openR && openR.message) || 'Could not open folder', 'error');
      }
    } else {
      showAlert((r && r.message) || 'Could not get config path', 'error');
    }
  });
  document.getElementById('settings-copy-path').addEventListener('click', async () => {
    const r = await window.pywebview.api.settings_get_path();
    if (r && r.status === 'success') {
      await window.pywebview.api.copy_to_clipboard(r.file);
      showAlert('Path copied to clipboard.', 'success');
    }
  });
  document.getElementById('settings-check-updates').addEventListener('click', () => checkForUpdates(true));
  document.getElementById('settings-ffmpeg-legal').addEventListener('click', async () => {
    const ff = await window.pywebview.api.get_ffmpeg_notice();
    if (ff && ff.status === 'success' && ff.legal_url) {
      await window.pywebview.api.open_update_download(ff.legal_url);
    }
  });
  document.getElementById('update-download').addEventListener('click', downloadUpdate);
  document.getElementById('update-later').addEventListener('click', () => dismissUpdateNotice('later'));
  document.getElementById('update-skip').addEventListener('click', () => dismissUpdateNotice('skip'));
}

window.onerror = (msg, url, line) => {
  logger.error(`${msg} at ${url}:${line}`);
  flushLogs();
};
window.onunhandledrejection = (e) => {
  logger.error(String(e.reason));
  flushLogs();
};

window.addEventListener('pywebviewready', async () => {
  flushLogs();
  uiLog('Main UI ready');
  setupNavigation();
  setupSettings();
  try {
    const data = await window.pywebview.api.get_initial_data();
    if (data && data.status === 'success') {
      appData = data;
      document.getElementById('app-version').textContent = 'v' + data.version;
      if (data.cpu_cores) {
        const el = document.getElementById('compress-cores-label');
        if (el) el.textContent = `Use all CPU cores (${data.cpu_cores} threads)`;
      }
    }
    if (window.CompressUI) await CompressUI.init();
    if (window.JoinUI) await JoinUI.init();
    await checkForUpdates(false);
  } catch (e) {
    showAlert('Startup error: ' + e, 'error');
  }
});
