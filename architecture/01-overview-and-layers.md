# 1. Overview and Layer Model

## What `web_app.py` is (and is not)

`src/web_app.py` is the **process entry point** for the modern CMS UI. It does not implement business rules, workflow tables, or IDEA automation. Its job is limited to:

1. Configure logging before any heavy imports.
2. Validate the IACS license.
3. Construct the backend bridge (`CMSApi`).
4. Open a native window (Microsoft WebView2 via PyWebView).
5. Run the GUI event loop until the user exits.

All feature logic lives elsewhere: `bridge/api_bridge.py`, `pipeline/`, `engine/`, and the single-page application in `web/index.html`.

The legacy stack used **Tkinter / CustomTkinter** (`CMS.py`, dialog modules). That UI layer was removed; the backend modules were kept and exposed through the bridge instead of Tk callbacks.

## Layer diagram

```mermaid
flowchart TB
    subgraph entry ["Entry (web_app.py)"]
        LOG[Logging setup]
        LIC[ensure_license]
        SPL[materialize_splash_url]
        WIN[webview.create_window]
        LOOP[webview.start edgechromium]
    end

    subgraph shell ["Presentation (web/)"]
        SH[splash.html]
        IX[index.html + style.css]
        JS[In-page JS: wizard, table, tour]
    end

    subgraph bridge ["Bridge (api_bridge.py)"]
        API[CMSApi public methods]
        COM[COM worker thread + queue]
        ENV["_ok / _err JSON envelopes]
    end

    subgraph backend ["Backend"]
        IDEA[engine: IDEALib, idea_controller]
        PIPE[pipeline: summarize, DE, join]
        UTIL[utils: paths, JSON]
        MOD[modules: license_wrapper]
    end

  LOG --> LIC --> API
  LIC --> SPL --> WIN
  API --> WIN
  WIN --> LOOP
  SH -->|prepare_idea_startup| API
  SH -->|location.href| IX
  IX -->|window.pywebview.api.*| API
  API --> COM --> IDEA
  API --> PIPE
  API --> UTIL
  LIC --> MOD
```

## Responsibility matrix

| Layer | Path | Owns | Must not own |
|-------|------|------|----------------|
| Entry | `web_app.py` | Boot order, splash file materialization, window geometry, `js_api=` hookup | Workflow UI, COM calls, file pickers beyond window creation |
| Frontend | `web/*.html`, `style.css` | Layout, modals, wizards, validation UX, Hebrew RTL, loading overlays | Direct filesystem access, COM, license DLL |
| Bridge | `bridge/api_bridge.py` | JSON API, threading rules, native dialogs via `window.create_file_dialog`, persistence orchestration | HTML rendering, CSS |
| Engine | `engine/*` | IDEA COM client, table metadata via COM | User-visible strings for multi-step wizards |
| Pipeline | `pipeline/*` | Summarize, direct extraction, join algorithms | Checkbox state in the workflow grid |
| Utils | `utils/core_functions.py` | `resource_path`, `get_data_path`, JSON load/save | Application screens |

## Core design principles (stable contracts)

### 1. No Python GUI except unavoidable native surfaces

The bridge docstring states the contract explicitly: **Python never renders GUI widgets** except:

- PyWebView **native** file/folder dialogs (`OPEN_DIALOG`, `FOLDER_DIALOG`).
- IDEA’s own COM dialogs (e.g. Equation Editor), with the web window minimized during the call.

Everything else—tables, wizards, tours, alerts—is HTML.

### 2. JSON-serializable boundary

Every method exposed to JavaScript must:

- Return a `dict` with at least `"status": "success"` or `"status": "error"`.
- Use only JSON-friendly values (str, int, float, bool, list, dict, None).
- Avoid returning custom Python objects, `Path`, or `datetime` without converting them.

Helpers `_ok(payload)` and `_err(message)` standardize this at the bridge.

### 3. Frontend orchestrates multi-step flows; backend executes atoms

Example: creating a workflow is **not** one giant Python wizard. JavaScript runs:

`browse_file` → `import_to_idea` → (optional) `execute_summarize` → `validate_equation` → `execute_de` → `save_new_workflow`.

Python implements each step once; the web UI decides order and collects parameters.

### 4. COM apartment threading

Windows COM (IDEA) requires a **single-threaded apartment (STA)**. `CMSApi` runs a dedicated `_com_worker` thread that:

- Calls `pythoncom.CoInitialize()` once on that thread.
- Processes all IDEA work through a `queue.Queue`.
- Exposes `_invoke_com(func, ...)` so other threads (including PyWebView’s JS callback thread) never touch COM directly.

### 5. Deferred heavy startup for perceived performance

The window shows **splash HTML immediately**. IDEA process start and COM connect happen only after `prepare_idea_startup()` from the splash page—so the user sees feedback within milliseconds of launch.

## Data flow: one user action end-to-end

**Example: user clicks “Run group” and confirms.**

1. `index.html` — `confirmRun()` builds paths from modal fields, may call `import_to_idea`.
2. JS — `await window.pywebview.api.run_analysis(file_path, groupId)`.
3. PyWebView — marshals call to `CMSApi.run_analysis` on a background thread.
4. Bridge — `_invoke_com(_do)` runs pipeline steps on COM worker.
5. Pipeline — `summarization`, `direct_extraction`, `join_db` use `self._client`.
6. Bridge — `_export_joined_table_to_excel`, `_save_workflows`, returns `_ok()`.
7. JS — hides loading overlay, shows toast via `showAlert`.

## Persistence locations

| Data | Dev path | Frozen (installed) path |
|------|----------|-------------------------|
| User config, workflows JSON | `user_data/` at repo root | `%APPDATA%\CMS\` |
| Application logs | `src/CMS_dev_log.log` | `%APPDATA%\CMS\CMS_log.log` |
| Materialized splash cache | `src/cms_splash_materialized.html` | `%APPDATA%\CMS\cms_splash_materialized.html` |
| Bundled assets (read-only) | `src/assets/`, `src/web/` | PyInstaller `_MEIPASS` or `_internal` |

See [05-paths-packaging-webview2.md](05-paths-packaging-webview2.md) for path resolution details.

## Version and packaging touchpoints

- Version string: `src/version.py` → exposed via `get_initial_data()`.
- Windows installer build: `prod_esential/gen_exe_web_app.py` (PyInstaller, bundles `web/`, `assets/`, license DLL).
- GUI backend: `webview.start(gui='edgechromium')` → **WebView2** on Windows (not legacy IE).

## Mental model for Tkinter developers

| Tkinter concept | CMS PyWebView equivalent |
|-----------------|-------------------------|
| `Tk()` / `CTk()` root | `webview.create_window()` + `webview.start()` |
| `Button(command=fn)` | `<button onclick="fn()">` calling `pywebview.api` |
| `tkinter.filedialog` | `window.create_file_dialog(...)` on bridge |
| `StringVar` / widget state | JS variables (`workflows`, `wizardState`) |
| `mainloop()` | `webview.start()` (blocks until window closes) |
| Modal `Toplevel` | HTML `.modal-overlay` + `data-modal-confirm` keyboard handling |
| After idle / `root.after` | `async/await` + `pywebviewready` event |

The next documents unpack each layer in implementation detail.
