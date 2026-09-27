"""
Central configuration for the multi-agent system.
Loads settings from environment variables (via .env) with sensible defaults.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")
DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Per-agent generation limits. Kept modest so a full demo session
# (assess -> plan -> teach -> quiz -> critique -> repeat) stays fast and cheap.
MAX_TOKENS = {
    "assessor": 700,
    "planner": 900,
    "tutor": 1000,
    "quiz": 700,
    "critic": 500,
    "progress": 400,
    "orchestrator": 300,
}

MASTERY_THRESHOLD = 0.75  # quiz score (0-1) needed to advance to next topic
MAX_REMEDIATION_ROUNDS = 2  # how many times the Tutor re-teaches a topic before moving on anyway
