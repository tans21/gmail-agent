"""Discord webhook notifications."""

import requests
from config import DISCORD_WEBHOOK


def send_discord_notification(message):
    """Send a text message to the configured Discord channel via webhook.

    Args:
        message: The notification text to post (supports Discord Markdown).
    """

    payload = {
        "content": message
    }

    try:
        # POST the payload; Discord returns 204 No Content on success
        response = requests.post(DISCORD_WEBHOOK, json=payload)

        if response.status_code == 204:
            print("Discord notification sent")
        else:
            print("Discord notification failed")

    except Exception as e:
        print("Discord error:", e)
