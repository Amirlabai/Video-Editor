# 4. Frontend and PyWebView Integration

Sources: `src/web/splash.html`, `src/web/index.html` (~2200 lines inline JS), `src/web/style.css`.

## Two-page application model

CMS uses **two local HTML entry points**, not a JavaScript bundler or SPA framework:

| Page | Loaded when | Purpose |
|------|-------------|---------|
| `splash.html` (materialized) | `webview.create_window` initial `url` | Branding + IDEA boot gate |
| `index.html` | `window.location.href` after splash success | Full application |

There is no React/Vue build step—deployment copies static files into the PyInstaller bundle.

### Why not a single page?

1. **Time-to-first-paint** — splash is tiny; no workflow table or modals parsed on cold start.
2. **Clear phase separation** — backend IDEA boot is tied to splash lifecycle only.
3. **WebView2 asset rules** — splash materialization is isolated; main page loads `style.css` sibling-relative (same `web/` folder).

## PyWebView JavaScript API surface

### Global objects

| Global | Description |
|--------|-------------|
| `window.pywebview` | Namespace injected when bridge is ready |
| `window.pywebview.api` | Your `CMSApi` instance methods |
| Event `pywebviewready` | Fires when `api` is safe to call |

### Calling convention

Always wait for readiness:

```javascript
window.addEventListener('pywebviewready', async function () {
    const data = await window.pywebview.api.get_initial_data();
});
```

Use `async/await` — PyWebView promises for Python calls.

### Attribute exposure

PyWebView can mirror **public primitive attributes** on `js_api` to JS. CMS primarily uses **methods** returning envelopes; state lives in JS (`workflows` object) and is refreshed via `get_initial_data` / project change responses.

## Splash page lifecycle

### Visual structure

- Full-viewport branded gradient (`body.splash-page`).
- Logo from materialized absolute URI.
- Hint text: “Starting…”

### Script flow

```javascript
window.addEventListener('pywebviewready', async function () {
    const result = await window.pywebview.api.prepare_idea_startup();
    if (result && result.status === 'success') {
        window.location.href = '__INDEX_HTML_URI__';  // replaced at materialize time
        return;
    }
    hint.textContent = result.message || 'Failed to start IDEA.';
});
```

**Failure UX:** user stays on splash with error text—no navigation to broken main UI.

### CSS isolation

Scoped styles on `body.splash-page` prevent shared `style.css` body rules from breaking splash layout (comment in splash head).

## Main shell (`index.html`) structure

### Document layout (top to bottom)

1. `#loading-overlay` — global blocking spinner during API calls.
2. `.top-bar` — license, help, tour, exit.
3. `.main-header` — company name input (RTL Hebrew).
4. `.project-bar` — project badge, change project, new group, IDEA restart.
5. `.main-content` — `#workflowsTable` grouped by `table_id`.
6. `.status-bar` — active count, license line, version.
7. Modals — wizard, run, edit, group, tour (`.modal-overlay` pattern).

### RTL and typography

```html
<html lang="he" dir="rtl">
```

Google Font **Outfit** loaded from CDN (requires network on first run unless cached—acceptable for corporate desktops with internet; offline installs may need bundling fonts into `assets/` for a fork).

### Modal keyboard contract

Documented in `context.md`:

- `data-modal-confirm` — Enter triggers primary action.
- `data-modal-cancel` — Esc closes.
- `handleModalKeyboard` respects topmost `.modal-overlay`.
- Textareas exclude Enter-to-submit.

Replicate this in any migrated app for keyboard parity with Tkinter default button behavior.

## Initialization sequence (main page)

```javascript
window.addEventListener('pywebviewready', async function () {
    flushLogs();
    await get_asset_uri for loading splash image;
    await loadInitialData();      // get_initial_data
    await LicenseExpirationDate();
    bind group action delegation on #workflowsBody;
});
```

### `loadInitialData`

1. `showLoading(true)`
2. `get_initial_data()`
3. Populate company name, project badge, version label.
4. `workflows = data.workflows`; `renderTable()`.
5. If `is_new_user` → `startTour()`.
6. `showLoading(false)`

### Logger bridge

Before `pywebviewready`, `logger.info(...)` pushes to `logQueue`. After ready, `flushLogs()` drains to `log_js`. Prevents lost diagnostics during early script execution.

### Global error handlers

- `window.onerror` → `log_js('ERROR', ...)`
- `unhandledrejection` → same

## Client-side state model

### `workflows` (global object)

Mirror of server JSON:

- Keys = report names (except reserved `__*`).
- Values = workflow dicts (`report_name`, `table_id`, `pipeline`, metadata fields, `run_report` checkbox).

Updated after:

- `loadInitialData`
- `save_new_workflow` / `update_workflow` / `delete_workflow`
- `save_workflows` (bulk checkbox sync)
- `select_project` / `change_project` responses

### `wizardState`

Tracks multi-step wizard:

- Current step index, group `table_id`, imported file paths, metadata objects, summarize/DE flags, equation string.

Orchestrates calls to pipeline APIs step-by-step; see `context.md` workflow section.

### Metadata waterfall (join setup)

When summarize or DE steps are skipped, JS copies prior step metadata forward so join always has valid `de_file_metadata` / `secondary_file_metadata`. Documented in `context.md`:

- `prime_file_metadata` → import
- `summ_file_metadata` → summarize or waterfall
- `de_file_metadata` → DE or waterfall
- `secondary_file_metadata` → baseline for join

Python does not reconstruct this logic—it trusts persisted workflow JSON from JS.

### Group import cache — `__group_meta__`

Per `table_id`:

```javascript
{
  imported_file: "...",
  output_name: "...",
  metadata: { columns, column_types, file }
}
```

Helper `persistGroupMeta()` calls `update_group_meta` only—avoids clobbering workflows via stale `save_workflows`.

## Representative UI → API mappings

| User action | JS function | API methods |
|-------------|-------------|-------------|
| Blur company field | `onblur` on input | `save_company_name` |
| Change project button | `changeProject()` | `change_project` |
| New group | `createGroup()` modal | `create_group` |
| Add report in group | `openWizard(tid)` | wizard chain |
| Toggle run checkbox | table handler | `save_workflows` (merged server-side) |
| Run group | `confirmRun()` | `import_to_idea`?, `run_analysis` |
| Edit report | edit modal | `update_workflow`, `validate_equation` |
| Exit | `exitApp()` | `exit_app(stopIdea)` |
| License button | `showLicense()` | `show_license` |

## Wizard pipeline (frontend-owned)

Typical **new report** flow inside `wizardNext()`:

1. **Import step** — `browse_file` → optional `import_to_idea` (skip if `__group_meta__` hit).
2. **Summarize** (optional, may be hidden in UI) — `execute_summarize`.
3. **DE step** — `validate_equation` then `execute_de`.
4. **Join fields** — populate dropdowns from `get_file_metadata` / cached metadata.
5. **Finish** — `save_new_workflow(wizard_data)` then `persistGroupMeta()`.

Each step checks `result.status` and uses `showAlert` for Hebrew error messages.

## Loading overlay pattern

```javascript
function showLoading(show) {
    document.getElementById('loading-overlay').style.display = show ? 'flex' : 'none';
}
```

Long COM operations (`run_analysis`, `import_to_idea`) wrap with `showLoading(true/false)` so users cannot double-submit.

**Tkinter equivalent:** `grab_set` modal or disabling all buttons—same UX goal.

## Tour system

- Driven by `is_new_user` from `get_initial_data`.
- `tourSteps` array: title, content, optional CSS `target` selector.
- `complete_tour()` or `skipTour()` → `api.complete_tour()`.

Pure HTML modal `#tourModal`—no Python tour state except the boolean flag in JSON config.

## Styling architecture (`style.css`)

- CSS variables in `:root` for brand colors (`--top-bar-bg`, `--hero-bg`, etc.).
- Component classes: `.action-btn`, `.modal-overlay`, `.group-header-row`, `.wizard-stepper`.
- Loading overlay uses same variables as splash for visual continuity.

For a new app, **copy the modal + button tokens** first to get consistent polish before feature porting.

## Security considerations (local app)

- Content is `file://` — no CORS, but WebView2 blocks cross-directory relative loads (hence `get_asset_uri`).
- `get_asset_uri` rejects `..` path segments.
- Inline script has full access to `pywebview.api`—do not inject untrusted HTML.
- External font CDN is the main network exposure on index load.

## Replication checklist (frontend)

1. Create `web/splash.html` with `pywebviewready` → one backend boot method → redirect.
2. Create `web/index.html` with `pywebviewready` → `get_initial_data` pattern.
3. Implement `logger` + `flushLogs` + global error forwarding.
4. Implement `showLoading` + `showAlert` (toast div—search `showAlert` in index.html).
5. Port each Tkinter screen to a modal or main panel section.
6. Replace every `button command=` with `onclick` + `await api....`
7. Materialize splash URIs in Python (or run local HTTP server).

## Cross-references

- Splash materialization: [02-web-app-entry-point.md](02-web-app-entry-point.md)
- API method details: [03-api-bridge-contract.md](03-api-bridge-contract.md)
- Tkinter port plan: [06-tkinter-to-pywebview-playbook.md](06-tkinter-to-pywebview-playbook.md)
