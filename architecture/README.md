# CMS Web Application Architecture — Deep Dive

This folder documents how `src/web_app.py` boots the Continuous Monitoring System (CMS) as a **PyWebView + WebView2** desktop shell, how Python and JavaScript communicate, and how the same pattern can be applied when migrating **another Tkinter (or CustomTkinter) application**.

## Document map

| # | File | Contents |
|---|------|----------|
| 1 | [01-overview-and-layers.md](01-overview-and-layers.md) | Stack diagram, responsibilities per layer, design principles |
| 2 | [02-web-app-entry-point.md](02-web-app-entry-point.md) | Line-by-line `web_app.py`: logging, license, splash materialization, window creation |
| 3 | [03-api-bridge-contract.md](03-api-bridge-contract.md) | `CMSApi`: JSON envelopes, COM worker thread, startup gating, public API surface |
| 4 | [04-frontend-and-pywebview.md](04-frontend-and-pywebview.md) | `splash.html` / `index.html`, `pywebviewready`, wizard orchestration in JS |
| 5 | [05-paths-packaging-webview2.md](05-paths-packaging-webview2.md) | `resource_path`, `get_data_path`, frozen exe, `file://` security limits |
| 6 | [06-tkinter-to-pywebview-playbook.md](06-tkinter-to-pywebview-playbook.md) | Step-by-step replication guide for a different Tkinter app |

## Related repo docs

- `context.md` — living project context (updated when architecture changes)
- `docs/src/web_app.md` — auto-generated API stubs for `web_app.py`
- `docs/src/bridge/api_bridge.md` — auto-generated `CMSApi` method list
- `product_requirements_document.md` — product-level API catalog

## One-sentence summary

**Python owns process lifecycle, licensing, COM, and disk I/O; HTML/CSS/JS owns every screen and workflow step; PyWebView is the thin glue that exposes a Python object as `window.pywebview.api`.**
