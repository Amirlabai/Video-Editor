/* Join videos view */

const JoinUI = (function () {
  let jobId = null;

  function appendLog(line) {
    const log = document.getElementById('join-log');
    log.textContent += line;
    log.scrollTop = log.scrollHeight;
  }

  function init() {
    document.getElementById('join-pick-input').addEventListener('click', async () => {
      const r = await window.pywebview.api.pick_folder('', 'Select folder with videos', 'join_input');
      if (r && r.status === 'success' && r.path) {
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
      if (r && r.status === 'success' && r.path) {
        document.getElementById('join-output').value = r.path;
      }
    });

    document.getElementById('join-start').addEventListener('click', async () => {
      const input = document.getElementById('join-input').value;
      const output = document.getElementById('join-output').value;
      if (!input) { showAlert('Select input folder.', 'error'); return; }
      document.getElementById('join-log').textContent = '';
      const r = await window.pywebview.api.join_start(input, output);
      if (!r || r.status !== 'success') {
        showAlert((r && r.message) || 'Join failed to start', 'error');
        return;
      }
      jobId = r.job_id;
    });

    document.getElementById('join-cancel').addEventListener('click', async () => {
      await window.pywebview.api.join_cancel(jobId || '');
    });
  }

  window.onJoinLog = function (data) {
    if (data.line) appendLog(data.line);
  };

  window.onJoinProgress = function (data) {
    if (data.message) appendLog(data.message + '\n');
  };

  window.onJoinComplete = function (data) {
    jobId = null;
    if (data.success) {
      showAlert('Videos joined: ' + data.output, 'success');
    } else {
      showAlert('Join failed or was cancelled.', 'error');
    }
  };

  return { init };
})();

window.JoinUI = JoinUI;
