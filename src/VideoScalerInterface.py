"""
Deprecated entry point — use web_app.py instead.
"""

import sys


def main():
    print("ffmpegMagic now uses PyWebView. Run:")
    print("  .\\.venv\\Scripts\\python.exe src\\web_app.py")
    sys.exit(1)


if __name__ == "__main__":
    main()
