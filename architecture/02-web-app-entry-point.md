# 2. `web_app.py` Entry Point — Deep Dive

Source: `src/web_app.py` (~140 lines). This file is intentionally small: every line exists to solve a boot-time concern that cannot live in the bridge without circular imports or late logging.

## File structure (execution order)

```
Imports guarded by logging
├── Logging configuration (frozen vs dev)
├── try/import webview, license, CMSApi, core_functions
├── _splash_cache_path()
├── materialize_splash_url()
├── ensure_license()
└── main()
```

## Logging block (lines 7–31)

### Why logging comes first

PyWebView and the bridge pull in many dependencies. If an `ImportError` occurs, you still want a log file. The comment in source states this explicitly:

> Logging must be configured before webview / bridge imports so import failures are logged.

### Frozen vs development behavior

| Mode | Detection | Log file | Level |
|------|-----------|----------|-------|
| Installed `.exe` | `getattr(sys, "frozen", False)` | `%APPDATA%\CMS\CMS_log.log` | `INFO` |
| Dev script | else | `src/CMS_dev_log.log` (next to package) | `DEBUG` |

`logging.basicConfig(..., force=True)` overwrites any prior handlers so repeated imports in tests do not duplicate logs.

### Failure mode

If APPDATA logging fails (permissions), the code prints to stdout and continues without crashing—boot may still proceed in dev.

## Import block (lines 33–40)

```python
try:
    import webview
    import modules.license_wrapper as lw
    from bridge.api_bridge import CMSApi
    import utils.core_functions as cf
except ImportError:
    logging.exception("Failed to import webview or application modules")
    raise
```

**Dependency chain:**

- `webview` — [pywebview](https://pywebview.flowrl.com/) package; on Windows with `gui='edgechromium'` uses Edge WebView2 runtime.
- `license_wrapper` — pythonnet + `IACS License.dll` (STA thread for .NET dialogs).
- `CMSApi` — pulls pipeline, engine, COM (heavy).
- `core_functions` — path helpers used for splash materialization.

Keeping `CMSApi` out of the top-level import until after logging is a deliberate boot hygiene choice.

## `_splash_cache_path()` (lines 43–50)

Returns where the **materialized** splash HTML is written:

- **Frozen:** `%APPDATA%\CMS\cms_splash_materialized.html`
- **Dev:** `src/cms_splash_materialized.html`

`mkdir(parents=True, exist_ok=True)` ensures the directory exists. The splash template in `web/splash.html` is not loaded directly by WebView2 from the bundle in all cases; the materialized copy carries resolved `file://` URIs (see below).

## `materialize_splash_url()` (lines 53–73)

### Problem being solved

Microsoft **WebView2** enforces strict rules for `file://` documents:

- A page at `file:///.../web/splash.html` **cannot** reliably load relative assets like `../assets/button_icons/logo.ico`.
- Users see broken images (alt text only) if paths are relative across directories.

### Algorithm

1. Read template `web/splash.html` via `cf.resource_path(...)` (works in dev and PyInstaller).
2. Replace placeholders with absolute URIs from `cf.asset_file_uri(...)`:
   - `__PYWEBVIEW_ASSET_SPLASH__` → logo `.ico`
   - `__INDEX_HTML_URI__` → main `index.html`
   - `__STYLE_CSS_URI__` → `style.css`
3. Write result to `_splash_cache_path()`.
4. Return `path.resolve().as_uri()` for `webview.create_window(url=...)`.

### Placeholders in `splash.html`

```html
<link rel="stylesheet" href="__STYLE_CSS_URI__">
<img src="__PYWEBVIEW_ASSET_SPLASH__" alt="">
<!-- in script -->
window.location.href = '__INDEX_HTML_URI__';
```

**Replication note:** Any new Tkinter→WebView app that loads local HTML must either materialize absolute URIs or serve files via a custom `http://127.0.0.1` server (PyWebView supports this; CMS uses materialization for simplicity).

## `ensure_license()` (lines 76–100)

### Flow

1. Construct `IACSLicenseWrapper(app_name="CMS")`.
2. Call `ensure_license(prompt_user=True)` — may show .NET license UI on an STA thread inside the wrapper.
3. Map exceptions:
   - `LicenseDeniedError` → user refused install/renewal → `(False, None)`
   - `IACSLicenseError` → init/validation failure → `(False, None)`
4. Require `status == LicenseStatus.VALID` else exit.

### Contract with `main()`

```python
valid, license_wrapper = ensure_license()
if not valid:
    sys.exit(1)
```

No window is created if license fails—fail fast before WebView2 starts.

The **same wrapper instance** is passed into `CMSApi(license_wrapper)` for later `get_license_expiration()` and `show_license()`.

## `main()` (lines 103–135)

### Step 1 — License (already covered)

### Step 2 — Bridge construction

```python
api = CMSApi(license_wrapper)
```

At this moment:

- COM worker thread **starts** but blocks on `_com_allow_connect` (IDEA not connected yet).
- User config JSON may load from `get_data_path("user_config.json")`.
- No window reference yet (`_window` is None until `set_window`).

### Step 3 — Window creation

```python
html_file = materialize_splash_url()
window = webview.create_window(
    title='Continuous Monitoring System',
    url=html_file,
    js_api=api,
    width=1000,
    height=850,
    min_size=(900, 850),
    text_select=False,
)
api.set_window(window)
```

| Parameter | Purpose |
|-----------|---------|
| `url=html_file` | Initial navigation is splash (fast, local `file://`) |
| `js_api=api` | Exposes **public methods** of `CMSApi` as `window.pywebview.api` in JS |
| `text_select=False` | Reduces “web page” text selection feel |
| `set_window` | Enables `create_file_dialog`, `destroy`, `minimize`/`restore` |

**PyWebView `js_api` rules (important for replication):**

- Only **public** methods are exposed (no leading `_`).
- Method names are available in camelCase on the JS side in some versions; CMS uses snake_case matching Python (`get_initial_data`).
- Return values must be JSON-serializable (PyWebView uses JSON RPC internally).
- Calls from JS are **async** from the browser’s perspective—use `await` in modern code.

### Step 4 — Event loop

```python
webview.start(gui='edgechromium', debug=not getattr(sys, "frozen", False))
```

| Flag | Effect |
|------|--------|
| `gui='edgechromium'` | WebView2 on Windows (required for modern CSS/ES6) |
| `debug=True` (dev only) | Right-click inspect / devtools where supported |

`webview.start()` **blocks** the main thread until all windows close—equivalent to Tk’s `mainloop()`.

There is no explicit `if __name__` guard beyond `main()` call; packaging invokes `web_app.main` or module run.

## Startup timeline (wall clock)

```
T+0ms    logging configured
T+?      license dialog (user-dependent)
T+?      CMSApi constructed, COM worker waiting
T+~      splash HTML materialized, window shown
T+~      pywebviewready on splash → prepare_idea_startup()
         ├── start IDEA exe if needed (up to 10s sleep)
         └── _com_allow_connect.set() → COM connects
T+~      splash navigates to index.html
T+~      pywebviewready on index → get_initial_data() (waits _ready_event, max 45s)
T+~      UI populated, tour optional
```

Constants in bridge:

- `IDEA_STARTUP_WAIT_SEC = 10` — after launching IDEA process.
- `SPLASH_MIN_WHEN_IDEA_ALREADY_RUNNING_SEC = 2.0` — minimum branding display.
- `get_initial_data` waits `_ready_event` up to **45 seconds**.

## What `web_app.py` should never grow

Avoid adding to this file:

- New API methods (belong in `CMSApi`).
- HTML strings (belong in `web/`).
- COM or pipeline imports (already in bridge).

If you replicate for another app, keep a **thin entry** module mirroring this file (~100–150 lines) and resist merging the bridge into it.

## Testing hook

`tests/test_webapp_coverage.py` smoke-tests import and helper functions (`materialize_splash_url`, `ensure_license` with mocks). Full UI tests mock `CMSApi` and webview.

## Cross-references

- Splash behavior: [04-frontend-and-pywebview.md](04-frontend-and-pywebview.md)
- Path helpers used here: [05-paths-packaging-webview2.md](05-paths-packaging-webview2.md)
- Tkinter migration checklist: [06-tkinter-to-pywebview-playbook.md](06-tkinter-to-pywebview-playbook.md)
