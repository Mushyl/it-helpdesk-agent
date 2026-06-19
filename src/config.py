"""
Central runtime configuration (12-factor style).

Every value can be overridden with an environment variable — set either in
the shell or in the key.env file in the project root — without touching any
code. This module is also the single place where key.env is loaded, so every
other module can simply read os.environ at runtime.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# key.env is the single source of truth for secrets and local overrides.
# override=True: the file wins over stale/empty variables already present
# in the environment.
_ENV_PATH = Path(__file__).parent.parent / "key.env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)

APP_VERSION = "1.0.0"

# --- LLM (Anthropic Claude) -------------------------------------------------
ANTHROPIC_MODEL = os.getenv("HELPDESK_LLM_MODEL", "claude-sonnet-4-6")
LLM_TIMEOUT_SECONDS = float(os.getenv("HELPDESK_LLM_TIMEOUT", "30"))
LLM_MAX_RETRIES = int(os.getenv("HELPDESK_LLM_MAX_RETRIES", "2"))

# --- RAG retrieval ----------------------------------------------------------
# Multilingual by default so that e.g. Italian questions retrieve the right
# documents from the English knowledge base (cross-lingual retrieval).
EMBEDDING_MODEL = os.getenv(
    "HELPDESK_EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2"
)
TOP_K = int(os.getenv("HELPDESK_TOP_K", "3"))

# --- Audit signals ----------------------------------------------------------
# Below this cosine-similarity score the run is flagged low_confidence
# (likely knowledge-base coverage gap).
LOW_CONFIDENCE_THRESHOLD = float(
    os.getenv("HELPDESK_LOW_CONFIDENCE_THRESHOLD", "0.30")
)

# --- Ticketing (Jira / ServiceNow export) -----------------------------------
JIRA_PROJECT_KEY = os.getenv("HELPDESK_JIRA_PROJECT_KEY", "IT")

# --- Slack bot --------------------------------------------------------------
# Needed only to run the Slack bot (src/slack_bot.py), in Socket Mode.
# SLACK_BOT_TOKEN starts with "xoxb-", SLACK_APP_TOKEN with "xapp-".
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
