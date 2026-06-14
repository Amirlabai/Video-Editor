# 5. Paths, Packaging, and WebView2 Constraints

Sources: `src/utils/core_functions.py`, `src/web_app.py`, `prod_esential/gen_exe_web_app.py`.

## The two path systems

CMS deliberately separates **read-only bundled resources** from **writable user data**.

### `resource_path(relative_path)` — read-only assets

**Development:**

```
base_path = <repo>/src/
full_path = base_path + relative_path
```

Example: `resource_path("web/index.html")` → `.../src/web/index.html`.

**Frozen (PyInstaller / Nuitka):**

```
base_path = sys._MEIPASS
# or fallback: dirname(executable)/_internal
```

Used for: HTML, CSS, icons, help HTML, license DLL adjacent paths in bundle.

### `get_data_path(relative_path)` — writable user data

**Development:**

```
<repo>/user_data/<relative_path>
```

**Frozen:**

```
%APPDATA%\CMS\<relative_path>
```

Used for: `user_config.json`, `user_workflows/*.json`, logs (via separate logic in `web_app.py`), materialized splash cache.

### `asset_file_uri(relative_path)`

```python
Path(resource_path(relative_path)).resolve().as_uri()
# → file:///C:/.../assets/button_icons/logo.ico
```

Required for WebView2 to load images/styles across directories.

## WebView2 `file://` rules (why CMS materializes HTML)

| Approach | Works in WebView2? |
|----------|-------------------|
| `splash.html` with `../assets/logo.ico` | Often **broken** |
| Materialized HTML with `file:///C:/.../logo.ico` | **Yes** |
| `get_asset_uri()` from JS for each asset | **Yes** |
| Local HTTP server `http://127.0.0.1:port/...` | **Yes** (not used in CMS) |
| Remote `https://` CDN (fonts) | **Yes** (network required) |

CMS chose **materialize splash + runtime `get_asset_uri`** to avoid maintaining a static file server.

## `web_app.py` path usage summary

| Function | Path helper | Output |
|----------|-------------|--------|
| Dev log | hardcoded beside `src/` | `CMS_dev_log.log` |
| Frozen log | `%APPDATA%\CMS\` | `CMS_log.log` |
| Splash template read | `resource_path("web/splash.html")` | |
| Splash cache write | `_splash_cache_path()` | APPDATA or `src/` |
| Asset URIs in splash | `asset_file_uri("assets/...")` | |

## PyInstaller packaging (`gen_exe_web_app.py`)

High-level steps:

1. Read `APP_VERSION` from `src/version.py`.
2. Bundle `src/web_app.py` as entry.
3. `--add-data` trees: `src/web`, `src/assets`, `src/modules` (license DLL), etc.
4. Icon: `assets/button_icons/app-icon.ico`.
5. Output installer directory `installer_files_{version}`.

**Replication:** mirror the spec for your app’s `web/` and `assets/` folders; ensure `resource_path` relative strings match `--add-data` mount points.

### Frozen detection

```python
getattr(sys, "frozen", False)
```

True when running as packaged exe. Also check `sys._MEIPASS` for one-file PyInstaller extract dir.

## Environment variables and directories

| Variable / path | Usage |
|-----------------|-------|
| `%APPDATA%\CMS` | User JSON, logs, splash cache (frozen) |
| `%ProgramData%\CMS` | Shared defaults (mentioned in context for VDI) |
| IDEA registry `ManagedProjectsDirectory` | Fallback project root in bridge |

## JSON persistence helpers

### `save_json(data, filepath, use_temp=False)`

- Creates parent directories.
- Optional atomic write: `.tmp` then `os.replace` (crash-safe).

### `load_json(filepath)`

- Missing file → create `{}` and return empty dict.
- Invalid JSON → log error, return `{}`.

Workflow files and `user_config.json` use these—replicate for any Tkinter app state previously in pickle or ad hoc text files (prefer JSON for JS interoperability).

## `migrate_workflows_to_table_id`

Server-side migration on load ensures every workflow has `table_id` derived from `prime_file` basename. Called from `load_workflows()`.

Frontend may still send `table_id` explicitly on new saves.

## Debugging tips

| Symptom | Likely cause |
|---------|----------------|
| Broken images on splash | Forgot materialization or wrong `resource_path` in frozen build |
| `get_initial_data` timeout | `prepare_idea_startup` not called or IDEA failed |
| Empty workflows | Wrong `get_data_path` in dev (check `user_data/`) |
| ImportError on exe | Missing `--add-data` for `web/` or `modules/` |
| COM errors on random thread | Calling IDEA without `_invoke_com` |

Enable `debug=True` in `webview.start` during development for WebView2 devtools.

## Cross-references

- Entry materialization: [02-web-app-entry-point.md](02-web-app-entry-point.md)
- Bridge `get_data_path` usage: [03-api-bridge-contract.md](03-api-bridge-contract.md)
