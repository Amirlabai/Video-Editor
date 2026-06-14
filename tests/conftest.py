"""
Pytest configuration file.
Adds project root to Python path for all tests.
"""

import sys
from pathlib import Path

# Add project root and src/ to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
for p in (str(src_path), str(project_root)):
    if p not in sys.path:
        sys.path.insert(0, p)

