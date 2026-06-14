# 3. API Bridge (`CMSApi`) — Deep Dive

Source: `src/bridge/api_bridge.py` (~1450 lines). This is the **largest integration surface** between the web UI and the Python backend.

## Class role

`CMSApi` is registered as PyWebView’s `js_api`. JavaScript calls:

```javascript
const result = await window.pywebview.api.get_initial_data();
```

Python executes the matching method and returns a dict that PyWebView serializes to JSON.

## Response envelope contract

### Success

```python
def _ok(payload=None):
    base = {"status": "success"}
    if payload:
        base.update(payload)
    return base
```

Example:

```json
{
  "status": "success",
  "company_name": "Acme",
  "project_name": "FY2025",
  "version": "2.3.0",
  "workflows": { },
  "is_new_user": false
}
```

### Error

```python
def _err(message):
    return {"status": "error", "message": str(message)}
```

JavaScript pattern throughout `index.html`:

```javascript
const data = await window.pywebview.api.some_method();
if (!data || data.status !== 'success') {
    showAlert((data && data.message) ? data.message : 'שגיאה', 'error');
    return;
}
```

**Replication rule:** Never raise uncaught exceptions across the JS boundary for expected failures—return `_err`. Reserve exceptions for programmer bugs; PyWebView may surface them as generic script errors.

## Instance state (what lives on `self`)

### Public JSON-friendly fields (may be read by PyWebView attribute sync)

| Attribute | Meaning |
|-----------|---------|
| `working_directory` | IDEA working directory path |
| `working_directory_basename` | Managed project name |
| `idea_projects_directory` | Parent of project folders |
| `is_ascii` | IDEA encoding flag for pipeline |
| `work_flows` | In-memory workflow map (also on disk) |
| `project_file_json` | Path to current project’s workflow JSON |
| `user_config_json` | Path to user config file |

### Private infrastructure

| Member | Role |
|--------|------|
| `_license_wrapper` | IACS license API |
| `_window` | PyWebView window ref for dialogs |
| `_client` | IDEA COM client object |
| `_com_queue`, `_com_worker` | STA worker dispatch |
| `_ready_event` | Set when COM client init finished |
| `_com_allow_connect` | Gate: splash must call `prepare_idea_startup` first |
| `_prepare_lock` | Prevent double IDEA boot |
| `_metadata_cache` | Per-session file column metadata |
| `_last_joined_db` | Paths for Excel export after `run_analysis` |

## COM worker architecture

### Why it exists

IDEA automation uses **win32com** / COM. COM objects created in one apartment must be used on that thread. PyWebView invokes API methods from **arbitrary threads** (not the main thread, not necessarily the same thread each time).

### Worker loop (simplified)

```python
def _run_com_worker(self):
    pythoncom.CoInitialize()
    self._com_allow_connect.wait()          # blocked until splash
    self._client = idealib.idea_client()
    self._sync_client_from_idea()
    self._ready_event.set()

    while True:
        item = self._com_queue.get()
        if item is None: break              # shutdown sentinel
        func, args, kwargs, result_queue = item
        try:
            res = func(*args, **kwargs)
            result_queue.put(("success", res))
        except Exception as e:
            result_queue.put(("error", str(e)))
```

### `_invoke_com`

```python
def _invoke_com(self, func, *args, **kwargs):
    if threading.current_thread() == self._com_worker:
        return func(*args, **kwargs)   # avoid deadlock
    res_q = queue.Queue()
    self._com_queue.put((func, args, kwargs, res_q))
    status, result = res_q.get()
    if status == "error":
        raise Exception(result)
    return result
```

**Pattern for public methods:** wrap COM work in nested `def _do(): ...` and `return self._invoke_com(_do)`.

**Replication for non-COM apps:** You may omit the worker entirely if your backend is thread-safe pure Python. For **any** COM, ODBC STA drivers, or UIAutomation, use the same queue pattern.

### Shutdown

`exit_app(stop_idea=False)` calls `_shutdown_com_worker()`:

1. `self._com_queue.put(None)` — sentinel stops loop.
2. `join(timeout=10)`.
3. `window.destroy()` and `sys.exit(0)`.

## Startup gating: `prepare_idea_startup` vs `get_initial_data`

### `prepare_idea_startup()` (called from splash)

Under `_prepare_lock`:

1. If `_com_allow_connect` already set → return `_ok()` immediately.
2. If IDEA not running:
   - `idea_controller.search_disk_for_idea()` → exe path
   - `idea_controller.start_idea(exe)`
   - `time.sleep(IDEA_STARTUP_WAIT_SEC)` (10s)
3. If IDEA already running:
   - `time.sleep(SPLASH_MIN_WHEN_IDEA_ALREADY_RUNNING_SEC)` (2s) for branding
4. `_com_allow_connect.set()` — unblocks COM worker connect

Returns `_err(...)` if exe not found or exception.

### `get_initial_data()` (called from main UI)

1. `_ready_event.wait(timeout=45)` — COM client must finish init.
2. Optionally `load_workflows()` if project active.
3. Returns company name, project name, version, workflows dict, `is_new_user`.

If timeout → `_err("IDEA connection timed out...")`.

**Ordering invariant:** splash **must** run `prepare_idea_startup` before index calls `get_initial_data`. Navigating to index without successful prepare yields timeout errors.

## Native dialogs (Tkinter replacement)

### File picker — `browse_file`

```python
files = self._window.create_file_dialog(
    webview.OPEN_DIALOG,
    file_types=(
        "Excel Files (*.xlsx;*.xls)",
        "IDEA Databases (*.imd;*.idm)",
        "All files (*.*)",
    ),
)
```

Returns `_ok({"file_path": files[0]})` or `_ok({"file_path": None})`.

**PyWebView filter format:** description string must not contain `/` (library regex limitation—documented in bridge comments).

### Folder picker — `change_project`

```python
folders = self._window.create_file_dialog(webview.FOLDER_DIALOG, directory=projects_path)
```

Then COM switches `ManagedProject` on the worker thread.

## WebView-safe assets — `get_asset_uri`

```python
def get_asset_uri(self, relative_path):
    # Validates no '..', joins under assets/
    uri = cf.asset_file_uri(key)
    return _ok({"uri": uri})
```

Used on main load for loading splash image in overlay:

```javascript
const ar = await window.pywebview.api.get_asset_uri('button_icons/iacslogo.ico');
document.getElementById('loading-splash').src = ar.uri;
```

## Workflow persistence semantics

### File location

`WORKFLOWS_DIR = cf.get_data_path("user_workflows")`  
Per-project file: `{WORKFLOWS_DIR}/{ManagedProject}.json`

### Reserved keys in workflow dict

| Key | Meaning |
|-----|---------|
| `__groups__` | List of group id strings |
| `__group_meta__` | Per-group import cache `{ table_id: { imported_file, ... } }` |
| Keys starting with `__` | Reserved; not report names |

### `save_workflows(updated_workflows)` merge rules

Critical for VDI/multi-tab safety:

- Report keys come from client.
- `__group_meta__` is **always server-owned** (client cannot wipe).
- `__groups__` updated from client only if `_valid_groups_list`; empty client list does not wipe server groups.
- Other `__*` keys preserved from server if missing in client payload.

### Group APIs

- `create_group(group_id)` — append to `__groups__`
- `delete_group(group_id)` — rejects if any workflow in group has `run_report: true`
- `update_group_meta` / `clear_group_meta` — surgical cache updates without full map replace

**Frontend pitfall documented in bridge:** after `save_new_workflow`, do not call `save_workflows` with a stale JS object—it can overwrite server state. Use `update_group_meta` or targeted APIs.

## Pipeline-facing public methods

| Method | Purpose |
|--------|---------|
| `execute_summarize` | Run summarization; return output path + metadata |
| `validate_equation` | Open IDEA equation editor (minimize web window) |
| `execute_de` | Direct extraction with equation string |
| `import_to_idea` | Excel/CSV → IDEA database |
| `run_analysis` | Full pipeline for checked workflows in group |
| `get_file_metadata` | Column names/types (COM or pandas) |
| `get_project_files` | List `.imd`/`.idm` in project |

All path arguments may be relative; `_resolve_path` applies anchor + dated-folder rules for CMS folder layout.

## Path resolution — `_resolve_path`

Handles IDEA project layouts where relative paths repeat folder segments or sibling dated folders exist (`260515` vs `260513`):

1. **Anchor search** — walk working directory path segments to match first segment of relative path.
2. **Sibling dated folder** — if both ends look like `YYMMDD`, join via parent directory.
3. **Default** — `os.path.join(working_directory, relative_path)`.

Replicate this only if your domain has similar folder conventions; otherwise return paths unchanged.

## License and config methods

| Method | Notes |
|--------|-------|
| `get_license_expiration` | Date string + warning flags |
| `show_license` | Delegates to .NET wrapper UI |
| `save_company_name` | Updates `user_config.json` |
| `get_user_config` / `save_user_config` | Full config blob |
| `complete_tour` | Sets `is_new_user: false` |
| `show_help` | `os.startfile` on bundled HTML manual |
| `exit_app(stop_idea)` | Optional IDEA shutdown |

## Logging from JavaScript — `log_js`

```python
def log_js(self, level, message):
    logging.log(mapped_level, f"[JS] {message}")
```

Frontend `logger` buffers until `pywebviewready`, then `flushLogs()`. Global `window.onerror` and unhandled rejections forward to `log_js('ERROR', ...)`.

Wizard steps log with `[Wizard]` prefix via convention in JS.

## Public API inventory (JS-callable)

Grouped by concern—use as checklist when porting a Tkinter app.

**Startup / config:** `get_asset_uri`, `prepare_idea_startup`, `get_initial_data`, `get_license_expiration`, `log_js`, `save_company_name`, `get_user_config`, `save_user_config`, `complete_tour`, `show_license`, `show_help`, `exit_app`

**Project / files:** `get_available_projects`, `select_project`, `change_project`, `browse_file`, `get_project_files`, `get_file_metadata`

**Pipeline:** `execute_summarize`, `validate_equation`, `execute_de`, `import_to_idea`

**Workflow CRUD:** `save_new_workflow`, `update_workflow`, `delete_workflow`, `save_workflows`, `update_group_meta`, `clear_group_meta`, `create_group`, `delete_group`

**Run / maintenance:** `run_analysis`, `refresh_connections`, `restart_idea`

Methods starting with `_` are **not** exposed to JavaScript.

## Error handling and reconnection

- `_init_connection` — probes `WorkingDirectory`; on failure calls `_reconnect_idea_com`.
- `run_analysis` — on exception per report, logs and may `_init_connection`.
- `restart_idea` — kills/restarts process, `_reconnect_idea_com` on worker.

## Testing strategy

`tests/test_api_bridge.py` mocks:

- `_run_com_worker` / `_invoke_com` to run synchronously on test thread
- COM client with fake `WorkingDirectory`, `ManagedProject`
- File system with temp workflow JSON

When replicating, **mock the bridge class**, not `web_app.py`, for business logic tests.

## Cross-references

- Entry boot: [02-web-app-entry-point.md](02-web-app-entry-point.md)
- JS usage patterns: [04-frontend-and-pywebview.md](04-frontend-and-pywebview.md)
- Tkinter mapping: [06-tkinter-to-pywebview-playbook.md](06-tkinter-to-pywebview-playbook.md)
