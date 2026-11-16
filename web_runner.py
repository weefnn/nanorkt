#!/usr/bin/env python3
"""
Backward-compatible web entrypoint.

Older installations may still execute `python web_runner.py` from systemd.
Keep this shim so upgrades do not break existing service units.
"""

from run_web import main


if __name__ == "__main__":
    main()
