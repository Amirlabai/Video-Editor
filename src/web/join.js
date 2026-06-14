/* Join videos view */

const JoinUI = (function () {
  let jobId = null;
  let processing = false;

  function setBusy(busy) {
    processing = busy;
    document.getElementById('join-start').disabled = busy;
    document.getElementById('join-pick-input').disabled = busy;
    document.getElementById('join-pick-output').disabled = busy;
  }

  function appendLog(line) {
    const log = document.getElementById('join-log');
    log.textContent += line;
    log.scrollTop = log.scrollHeight;
  }

  async function loadLastFolders() {
    const r = await window.pywebview.api.settings_get_summary();
    if (!r || r.status !== 'success') return;
    const input = r.folders.last_join_input;
    const output = r.folders.last_join_output;
    if (input && input !== '(none)') {
      document.getElementById('join-input').value = input;
    }
    if (output && output !== '(none)') {
      document.getElementById('join-output').value = output;
    }
  }

  async function init() {
    await loadLastFolders();

    document.getElementById('join-pick-input').addEventListener('click', async () => {
      const initial = document.getElementById('join-input').value;
      const r = await window.pywebview.api.pick_folder(initial, 'Select folder with videos', 'join_input');
      if (!r || r.status !== 'success') {
        showAlert((r && r.message) || 'Could not open folder picker', 'error');
        return;
      }
      if (r.path) {
        document.getElementById('join-input').value = r.path;
        const scan = await window.pywebview.api.join_scan_folder(r.path);
        if (scan && scan.status === 'success') {
          appendLog(`Found ${scan.count} video file(s). Compatible: ${scan.compatible}\n`);
          if (scan.count < 2) appendLog('Need at least 2 files to join.\n');
          else if (!scan.compatible) appendLog('Warning: files may be incompatible.\n');
        }
      }
    });

    document.getElementById('join-pick-output').addEventListener('click', async () => {
      const input = document.getElementById('join-input').value;
      const r = await window.pywebview.api.pick_folder(input, 'Output folder (optional)', 'join_output');
      if (!r || r.status !== 'success') {
        showAlert((r && r.message) || 'Could not open folder picker', 'error');
        return;
      }
      if (r.path) {
        document.getElementById('join-output').value = r.path;
      }
    });

    document.getElementById('join-start').addEventListener('click', async () => {
      if (processing) return;
      const input = document.getElementById('join-input').value;
      const output = document.getElementById('join-output').value;
      if (!input) { showAlert('Select input folder.', 'error'); return; }
      document.getElementById('join-log').textContent = '';
      setBusy(true);
      const r = await window.pywebview.api.join_start(input, output);
      if (!r || r.status !== 'success') {
        showAlert((r && r.message) || 'Join failed to start', 'error');
        setBusy(false);
        return;
      }
      jobId = r.job_id;
    });

    document.getElementById('join-cancel').addEventListener('click', async () => {
      await window.pywebview.api.join_cancel(jobId || '');
    });
  }

  window.join_log = function (data) {
    if (data.line) appendLog(data.line);
  };

  window.join_progress = function (data) {
    if (data.message) appendLog(data.message + '\n');
  };

  window.join_complete = function (data) {
    jobId = null;
    setBusy(false);
    if (data.cancelled) {
      showAlert('Join cancelled.', 'info');
    } else if (data.success) {
      showAlert('Videos joined: ' + data.output, 'success');
    } else {
      showAlert('Join failed.', 'error');
    }
  };

  return { init };
})();

window.JoinUI = JoinUI;
