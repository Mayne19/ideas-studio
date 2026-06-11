#!/usr/bin/env python3
"""Run the Ideas Studio background worker.

Usage:
    python worker.py          # Start the background scheduler
    python worker.py once     # Run all scheduled tasks once
"""
import sys
from app.cli import run_worker, run_scheduler

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "once":
        run_scheduler()
    else:
        run_worker()
