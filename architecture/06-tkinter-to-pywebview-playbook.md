# 6. Playbook: Replicate This Architecture in Another Tkinter App

This guide assumes you have an existing **Tkinter or CustomTkinter** desktop app and want the same architecture CMS uses: **PyWebView shell + HTML UI + Python bridge class**.

CMS is the reference implementation; adapt names and drop IDEA/COM sections if your app does not need them.

---

## Phase 0 — Inventory the Tkinter app

Before writing code, produce a table:

| Tkinter screen / dialog | Widgets & state | Backend functions called | Keep in Python? |
|-------------------------|-----------------|--------------------------|-----------------|
| Main window | Treeview, buttons | `load_data()`, `save()` | Backend only |
| File open dialog | `filedialog` | `process_file(path)` | Native dialog via PyWebView |
| Settings | Entries | read/write ini | Bridge methods |
| Progress / long task | `after()`, thread | worker fn | Bridge + loading overlay in HTML |

**Rule:** If it draws widgets, move to HTML. If it touches files, database, hardware, license, or OS—keep in Python bridge.

---

## Phase 1 — Repository layout

Recommended structure (mirror CMS):

```
your_app/
├── src/
│   ├── web_app.py              # thin entry (copy pattern from CMS)
│   ├── bridge/
│   │   └── api_bridge.py       # YourAppApi class
│   ├── web/
│   │   ├── splash.html
│   │   ├── index.html
│   │   └── style.css
│   ├── assets/                 # icons, images
│   └── utils/
│       └── core_functions.py   # resource_path, get_data_path, json
├── user_data/                  # dev-only writable data
└── prod/
    └── gen_exe.py              # PyInstaller spec
```

---

## Phase 2 — Minimal `web_app.py`

Implement in order:

### 2.1 Logging (copy CMS block)

Adjust log filename prefix (`YourApp_log.log`) and folder (`%APPDATA%\YourApp`).

### 2.2 License / single-instance / other pre-window gates

If no license, delete `ensure_license()` and pass `None` into API.

### 2.3 Materialize splash (if using local `file://` assets)

Copy `materialize_splash_url()` and placeholder convention from CMS.

### 2.4 `main()`

```python
def main():
    api = YourAppApi()  # add license arg if needed

    splash_uri = materialize_splash_url()  # or resource_path URI to index only for tiny apps

    window = webview.create_window(
        title="Your Application",
        url=splash_uri,
        js_api=api,
        width=1024,
        height=768,
        min_size=(800, 600),
        text_select=False,
    )
    api.set_window(window)
    webview.start(gui="edgechromium", debug=not getattr(sys, "frozen", False))
```

**Windows note:** Install [WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) on target machines (usually already present on Windows 11).

### 2.5 Dependencies

```
pip install pywebview pythonnet  # pythonnet only if .NET license like CMS
```

Pin versions in `requirements.txt` to match your CI.

---

## Phase 3 — Bridge class skeleton

```python
class YourAppApi:
    """
    - Public methods return {"status": "success"|"error", ...}
    - No Tk code
    - No HTML strings
    """

    def __init__(self):
        self._window = None
        # COM worker optional — see CMS _com_worker if needed

    def set_window(self, window):
        self._window = window

    def _ok(self, payload=None):
        base = {"status": "success"}
        if payload:
            base.update(payload)
        return base

    def _err(self, message):
        return {"status": "error", "message": str(message)}

    # --- exposed to JS ---

    def prepare_startup(self):
        """Optional: heavy init before main UI (like prepare_idea_startup)."""
        # load DB, start services, etc.
        return self._ok()

    def get_initial_data(self):
        return self._ok({
            "user_name": "...",
            "items": [],
        })

    def pick_file(self):
        if not self._window:
            return self._err("no window")
        files = self._window.create_file_dialog(webview.OPEN_DIALOG)
        path = files[0] if files else None
        return self._ok({"path": path})

    def exit_app(self):
        if self._window:
            self._window.destroy()
        sys.exit(0)
```

### Map Tkinter → bridge methods

| Tkinter pattern | Bridge method |
|-----------------|---------------|
| `filedialog.askopenfilename` | `pick_file()` using `OPEN_DIALOG` |
| `filedialog.askdirectory` | `pick_folder()` using `FOLDER_DIALOG` |
| `messagebox.showinfo` | Return `_err` / `_ok` and `showAlert()` in JS |
| `messagebox.askyesno` | Custom confirm modal in HTML |
| `root.after(0, fn)` | JS `await api.fn()` after async call |
| `threading.Thread(target=work)` | Worker in bridge; return job id + poll, or block with loading overlay |
| `Toplevel` wizard | HTML modal + step state object (`wizardState`) |

---

## Phase 4 — Frontend shell

### 4.1 Splash (`splash.html`)

```html
<script>
window.addEventListener('pywebviewready', async () => {
  const r = await window.pywebview.api.prepare_startup();
  if (r && r.status === 'success') {
    window.location.href = 'FILE_URI_TO_INDEX';  // materialized
  } else {
    document.getElementById('hint').textContent = r?.message || 'Startup failed';
  }
});
</script>
```

Skip splash for trivial apps: point `create_window(url=index_uri)` directly.

### 4.2 Main page (`index.html`)

Required primitives (copy from CMS):

1. `pywebviewready` → `get_initial_data()`.
2. `logger` + `flushLogs`.
3. `showLoading` / `showAlert`.
4. Global `onerror` forwarding.

Build UI in HTML/CSS first with **mock data**, then wire `onclick` handlers to `pywebview.api`.

### 4.3 Replace CustomTkinter styling

- Buttons → `<button class="action-btn primary">`
- Tables → `<table>` or CSS grid
- Tabs → modal steps or tab buttons + `display:none` panels
- CTkProgressBar → CSS spinner in `#loading-overlay`

---

## Phase 5 — Migrate feature by feature

Recommended order:

1. **Read-only main view** — lists data from `get_initial_data`.
2. **Settings** — form fields → `save_user_config` pattern.
3. **File pickers** — one dialog at a time.
4. **Long-running job** — show loading overlay; bridge runs work synchronously on worker thread or COM queue.
5. **Multi-step wizard** — last; highest JS complexity.

For each Tkinter dialog:

1. Screenshot the old UI for parity.
2. Build HTML modal.
3. Add bridge method(s) that accept plain dicts (not widget references).
4. Delete Tkinter code only when feature parity tested.

---

## Phase 6 — COM / threading (if applicable)

If your Tkinter app used `win32com`, **copy CMS COM worker verbatim**:

- `_com_worker` thread + `CoInitialize`
- `_invoke_com` for every public API touching COM
- Startup gate if external app must launch first
- `exit_app` sends queue sentinel and `join`s worker

If your app uses only SQLite/REST, a single `threading.Lock` around DB may suffice—simpler than COM but still avoid blocking the WebView2 UI thread for seconds without `showLoading`.

---

## Phase 7 — Packaging

1. Copy `resource_path` / `get_data_path` from CMS `core_functions.py`.
2. PyInstaller `--add-data` for `web` and `assets` with paths matching `resource_path("web/...")`.
3. Test frozen exe on a clean VM without Python installed.
4. Verify `%APPDATA%\YourApp` receives writable JSON.

---

## Phase 8 — Testing

| Layer | What to test |
|-------|----------------|
| Bridge | pytest with mocked `_window`, no webview |
| `web_app.py` | materialize paths, license mock |
| Manual | splash → main, each modal, exit |

CMS tests: `tests/test_api_bridge.py`, `tests/test_webapp_coverage.py`.

---

## Anti-patterns (learned from CMS migration)

| Anti-pattern | Why it hurts | Do instead |
|--------------|--------------|------------|
| Huge `js_api` method that runs entire wizard | Hard to test, poor error UX | Atomic API steps called from JS |
| Returning Python objects to JS | Serialization failure | Dict envelopes |
| Relative `../assets` in `file://` HTML | Broken images in WebView2 | `asset_file_uri` / materialize |
| Calling COM from JS callback thread | Random crashes | `_invoke_com` |
| `save_workflows` with stale full object | Overwrites server merge fields | Targeted update APIs |
| Putting business logic in `web_app.py` | Un-testable, import cycles | Bridge + pipeline modules |

---

## Minimal diff from “Tkinter only” mindset

```
BEFORE (Tkinter)                    AFTER (PyWebView)
─────────────────────────────────────────────────────────
CMS.py mainloop                       web_app.main() → webview.start
wizard_handler.Dialog                 index.html #wizardModal + wizardState
dialog_handlers.ask_file              CMSApi.browse_file + create_file_dialog
StringVar tracked in widgets          JS let state + JSON on server
PIL images in Label                   <img src="{uri from get_asset_uri}">
ttk.Treeview                          HTML <table> + renderTable()
```

---

## Optional: run Tkinter alongside (transitional)

CMS **removed** Tkinter entirely. For a gradual migration you *could* run Tk dialogs from the bridge on the main thread, but PyWebView’s event loop ownership makes this fragile. Preferred approach: port dialogs to PyWebView native dialogs or HTML modals immediately.

---

## Checklist before shipping

- [ ] All `pywebview.api` calls guarded with `status === 'success'`
- [ ] Splash or loading state for slow startup
- [ ] Logs in `%APPDATA%` when frozen
- [ ] No `..` in asset paths
- [ ] WebView2 runtime present on target OS
- [ ] Exit path shuts down background threads
- [ ] Hebrew/RTL tested if applicable (`dir="rtl"` on `<html>`)
- [ ] Keyboard: Enter/Esc on modals

---

## Where to read CMS reference code

| Concern | File |
|---------|------|
| Entry | `src/web_app.py` |
| Bridge | `src/bridge/api_bridge.py` |
| Paths | `src/utils/core_functions.py` |
| Splash | `src/web/splash.html` |
| Main UI | `src/web/index.html` |
| Styles | `src/web/style.css` |
| Packager | `prod_esential/gen_exe_web_app.py` |

---

## Document index

Return to [README.md](README.md) for the full architecture series.
