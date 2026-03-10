"""Configuration — loads secrets from .env and defines constants."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Gmail API scopes — loaded from .env (comma-separated if multiple)
SCOPES = os.getenv("GMAIL_SCOPES", "").split(",")

# File to persist IDs of already-processed emails between runs
PROCESSED_FILE = "processed_emails.json"

# Discord webhook URL — loaded from .env
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "")
