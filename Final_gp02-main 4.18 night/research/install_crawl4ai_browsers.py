"""Install Playwright Chromium for Crawl4AI (run once per environment).

Usage (from repo root)::

    python -m research.install_crawl4ai_browsers
"""

from __future__ import annotations

import subprocess
import sys


def main() -> int:
    try:
        subprocess.check_call(
            [sys.executable, "-m", "playwright", "install", "chromium"],
        )
    except subprocess.CalledProcessError as e:
        return int(e.returncode or 1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
