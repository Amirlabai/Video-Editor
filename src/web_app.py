"""
ffmpegMagic — PyWebView + WebView2 entry point.
"""

import logging
import os
import sys

# Ensure src/ is on path when run as script
_SRC = os.path.dirname(os.path.abspath(__file__))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


def _setup_logging() -> None:
    from utils.core_functions import get_log_path
    log_path = get_log_path()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )


def main() -> None:
    _setup_logging()
    logger = logging.getLogger("web_app")

    try:
        import webview
        from bridge.api_bridge import VideoEditorApi
        from utils.core_functions import asset_file_uri, is_frozen, materialize_splash_url
    except ImportError:
        logger.exception("Failed to import webview or application modules")
        raise

    api = VideoEditorApi()

    if os.environ.get("FFMPEGMAGIC_SKIP_SPLASH") == "1" and not is_frozen():
        start_url = asset_file_uri("web/index.html")
    else:
        start_url = materialize_splash_url()

    window = webview.create_window(
        title="ffmpegMagic",
        url=start_url,
        js_api=api,
        width=1024,
        height=768,
        min_size=(800, 600),
        text_select=True,
    )
    api.set_window(window)
    webview.start(gui="edgechromium", debug=not is_frozen())


if __name__ == "__main__":
    main()
