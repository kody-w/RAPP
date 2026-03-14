"""Rapp configuration — single source of truth for paths and settings.

All modules import from here instead of hardcoding paths.
Set RAPPTERBOOK_PATH env var to override the default.
"""
from __future__ import annotations

import os
from pathlib import Path

# The Rappterbook repo this engine operates on
RAPPTERBOOK_PATH = Path(os.environ.get(
    "RAPPTERBOOK_PATH",
    "/Users/kodyw/Projects/rappterbook"
))

# Derived paths
STATE_DIR = RAPPTERBOOK_PATH / "state"
SEEDS_FILE = STATE_DIR / "seeds.json"
AGENTS_FILE = STATE_DIR / "agents.json"
MISSIONS_FILE = STATE_DIR / "missions.json"
PROMPTS_DIR = RAPPTERBOOK_PATH / "scripts" / "prompts"
SCRIPTS_DIR = RAPPTERBOOK_PATH / "scripts"
LOGS_DIR = RAPPTERBOOK_PATH / "logs"

# Rapp app settings
RAPP_DIR = Path(__file__).parent
SESSIONS_FILE = RAPP_DIR / "sessions.json"
DEFAULT_PORT = 7777
