"""
Gmail Automation Agent — Entry Point

Modules
-------
config.py          → Environment variables and constants
auth.py            → Gmail OAuth 2.0 authentication
discord_notify.py  → Discord webhook notifications
tracking.py        → Processed email persistence
classifier.py      → AI email classification (Hugging Face)
email_actions.py   → Inbox scanning, deletion, daily summary
"""

from googleapiclient.discovery import build

from auth import authenticate
from email_actions import read_emails, delete_promotions, delete_social, send_daily_summary


def main():
    """Entry point — authenticate, scan inbox, and clean up categories."""

    # Step 1: Authenticate with Gmail
    creds = authenticate()

    # Step 2: Build the Gmail API client
    service = build("gmail", "v1", credentials=creds)

    # Step 3: Scan inbox — classify, trash promos, alert on jobs
    inbox_deleted = read_emails(service)

    # Step 4: Bulk-delete remaining promotional emails
    promo_deleted = delete_promotions(service)

    # Step 5: Bulk-delete social emails
    social_deleted = delete_social(service)

    # Step 6: Combine all deleted emails and send a daily summary to Discord
    all_deleted = inbox_deleted + promo_deleted + social_deleted
    send_daily_summary(all_deleted)


if __name__ == "__main__":
    main()