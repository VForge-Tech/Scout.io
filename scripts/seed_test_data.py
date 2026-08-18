#!/usr/bin/env python3
"""Wrapper around backend/scripts/seed_demo.py for host-side seeding.

Usage (from the repo root):

    python scripts/seed_test_data.py

Requires a reachable DATABASE_URL (backend/.env) and the backend dependencies.
"""

import os
import runpy
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
sys.path.insert(0, BACKEND_DIR)

sys.exit(runpy.run_path(os.path.join(BACKEND_DIR, "scripts", "seed_demo.py"), run_name="__main__"))