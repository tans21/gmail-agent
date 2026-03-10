"""Processed email tracking — avoids re-processing emails across runs."""

import os
import json
from config import PROCESSED_FILE


def load_processed():
    """Load previously processed email IDs from disk.

    Returns:
        set: Email IDs that have already been handled in prior runs.
    """

    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, "r") as f:
            return set(json.load(f))

    # First run — no processed emails yet
    return set()


def save_processed(processed_ids):
    """Persist the set of processed email IDs to disk.

    Args:
        processed_ids: Set of Gmail message IDs to save.
    """

    # Convert set to list for JSON serialization
    with open(PROCESSED_FILE, "w") as f:
        json.dump(list(processed_ids), f)
