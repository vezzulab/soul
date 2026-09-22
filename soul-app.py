#!/usr/bin/env python3
"""SOul by Vezzu Studio — punto de entrada."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from soul.ui import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
