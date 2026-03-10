"""
Gmail Automation Agent

Features
--------
• Gmail OAuth authentication
• Full inbox pagination
• Email classification
• Promotion cleanup
• Social cleanup
• Discord notifications for job emails
• Processed email tracking
"""

import os
import json
import requests

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


# ======================================================
# CONFIGURATION
# ======================================================

# Gmail API scope — "gmail.modify" allows reading, trashing, and labeling emails
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

# File to persist IDs of already-processed emails between runs
PROCESSED_FILE = "processed_emails.json"

# Discord webhook URL for sending job-email notifications
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1480855611200639067/guidnW9EZ26F4hQv0e0rrcQBl0KorM1sDLfGonmZIZ1Txh1cPLB2LiFE9SS4FHjNFyMA"


# ======================================================
# DISCORD NOTIFICATION
# ======================================================

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


# ======================================================
# PROCESSED EMAIL TRACKING
# ======================================================

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


# ======================================================
# AUTHENTICATION
# ======================================================

def authenticate():
    """Authenticate with the Gmail API using OAuth 2.0.

    Loads saved credentials from token.json when available.
    If missing or expired, launches the browser-based OAuth flow
    and saves the new token for future runs.

    Returns:
        Credentials: Authenticated Google OAuth 2.0 credentials.
    """

    creds = None

    # Reuse saved token to skip the login flow on subsequent runs
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # No valid token — run interactive OAuth consent flow
    if not creds or not creds.valid:

        flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json", SCOPES
        )

        # Starts a temporary local server to receive the OAuth callback
        creds = flow.run_local_server(port=0)

        # Cache the token so we don't prompt the user every time
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds


# ======================================================
# EMAIL CLASSIFICATION
# ======================================================

def classify_email(sender, subject, snippet):
    """Classify an email into a category based on keyword matching.

    Checks the combined sender, subject, and snippet text for keywords
    and returns one of: "promotion", "job", "important", or "normal".

    Args:
        sender:  The From header value.
        subject: The Subject header value.
        snippet: Gmail's short preview text of the email body.

    Returns:
        str: The category label for the email.
    """

    # Combine all fields into one lowercase string for easy matching
    text = (sender + subject + snippet).lower()

    # Marketing / promotional keywords
    if any(word in text for word in ["unsubscribe", "sale", "offer", "deal", "newsletter"]):
        return "promotion"

    # Job-related keywords
    if any(word in text for word in ["job", "intern", "career", "linkedin"]):
        return "job"

    # Banking / financial alert keywords
    if any(word in text for word in ["bank", "transaction", "alert", "payment"]):
        return "important"

    # Default category when no keywords match
    return "normal"


# ======================================================
# READ EMAILS WITH PAGINATION
# ======================================================

def read_emails(service):
    """Scan the entire inbox, classify each email, and take action.

    Paginates through all inbox messages (100 per page), skips
    already-processed emails, classifies new ones, trashes promotions,
    sends Discord alerts for job emails, and saves progress.

    Args:
        service: Authenticated Gmail API service object.

    Returns:
        list: Dicts with subject, sender, and category of each deleted email.
    """

    # Load IDs we've already handled so we don't re-process them
    processed_ids = load_processed()

    # Collect info about deleted emails for the daily summary
    deleted_emails = []

    next_page_token = None
    page_number = 1
    total_processed = 0

    # Paginate through all inbox messages
    while True:

        # Fetch up to 100 message stubs per page
        results = service.users().messages().list(
            userId="me",
            labelIds=["INBOX"],
            maxResults=100,
            pageToken=next_page_token
        ).execute()

        messages = results.get("messages", [])

        print(f"\nReading Page {page_number} ({len(messages)} emails)")

        for msg in messages:

            # Skip emails we've already processed in a previous run
            if msg["id"] in processed_ids:
                continue

            # Fetch full message details (headers, snippet, etc.)
            message = service.users().messages().get(
                userId="me",
                id=msg["id"]
            ).execute()

            headers = message["payload"]["headers"]

            sender = ""
            subject = ""

            # Extract From and Subject from the headers list
            for header in headers:

                if header["name"] == "From":
                    sender = header["value"]

                if header["name"] == "Subject":
                    subject = header["value"]

            snippet = message["snippet"]

            # Determine the email's category for downstream actions
            category = classify_email(sender, subject, snippet)

            print("Sender:", sender)
            print("Subject:", subject)
            print("Category:", category)

            # ------------------------------------------------
            # Promotion cleanup
            # ------------------------------------------------

            if category == "promotion":
                # Move promotional emails to trash automatically
                print("Deleting promotion:", subject)

                service.users().messages().trash(
                    userId="me",
                    id=msg["id"]
                ).execute()

                # Track the deleted promotion for the daily summary
                deleted_emails.append({"subject": subject, "sender": sender, "category": "Promotion"})

            # ------------------------------------------------
            # Job notification
            # ------------------------------------------------

            if category == "job":
                # Send a Discord alert so we don't miss job-related emails
                notification = f"""
📧 **New Job Email**

Sender: {sender}
Subject: {subject}
"""

                send_discord_notification(notification)

            # Mark this email as processed and bump the counter
            processed_ids.add(msg["id"])
            total_processed += 1

            print("-" * 50)

        # Move to the next page of results, or exit the loop
        next_page_token = results.get("nextPageToken")

        if not next_page_token:
            break

        page_number += 1

    # Persist processed IDs so the next run picks up where we left off
    save_processed(processed_ids)

    print("\nInbox scan finished")
    print("Total emails processed:", total_processed)

    return deleted_emails


# ======================================================
# DELETE PROMOTIONS
# ======================================================

def delete_promotions(service):
    """Trash all emails in Gmail's built-in Promotions category.

    Paginates through CATEGORY_PROMOTIONS in batches of 100
    and moves each message to the trash.

    Args:
        service: Authenticated Gmail API service object.

    Returns:
        list: Dicts with subject, sender, and category of each deleted email.
    """

    deleted_emails = []
    deleted_count = 0

    # Keep fetching pages until no promotional emails remain
    while True:

        results = service.users().messages().list(
            userId="me",
            labelIds=["CATEGORY_PROMOTIONS"],
            maxResults=100
        ).execute()

        messages = results.get("messages", [])

        # No more promotions — we're done
        if not messages:
            break

        for msg in messages:

            # Fetch subject and sender before trashing
            message = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="metadata",
                metadataHeaders=["From", "Subject"]
            ).execute()

            sender = ""
            subject = ""
            for header in message["payload"]["headers"]:
                if header["name"] == "From":
                    sender = header["value"]
                if header["name"] == "Subject":
                    subject = header["value"]

            service.users().messages().trash(
                userId="me",
                id=msg["id"]
            ).execute()

            deleted_emails.append({"subject": subject, "sender": sender, "category": "Promotion"})
            deleted_count += 1

        print("Promotions deleted so far:", deleted_count)

    print("Total promotions deleted:", deleted_count)

    return deleted_emails


# ======================================================
# DELETE SOCIAL EMAILS
# ======================================================

def delete_social(service):
    """Trash all emails in Gmail's built-in Social category.

    Paginates through CATEGORY_SOCIAL in batches of 100
    and moves each message to the trash.

    Args:
        service: Authenticated Gmail API service object.

    Returns:
        list: Dicts with subject, sender, and category of each deleted email.
    """

    deleted_emails = []
    deleted_count = 0

    # Keep fetching pages until no social emails remain
    while True:

        results = service.users().messages().list(
            userId="me",
            labelIds=["CATEGORY_SOCIAL"],
            maxResults=100
        ).execute()

        messages = results.get("messages", [])

        # No more social emails — we're done
        if not messages:
            break

        for msg in messages:

            # Fetch subject and sender before trashing
            message = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="metadata",
                metadataHeaders=["From", "Subject"]
            ).execute()

            sender = ""
            subject = ""
            for header in message["payload"]["headers"]:
                if header["name"] == "From":
                    sender = header["value"]
                if header["name"] == "Subject":
                    subject = header["value"]

            service.users().messages().trash(
                userId="me",
                id=msg["id"]
            ).execute()

            deleted_emails.append({"subject": subject, "sender": sender, "category": "Social"})
            deleted_count += 1

        print("Social emails deleted so far:", deleted_count)

    print("Total social emails deleted:", deleted_count)

    return deleted_emails


# ======================================================
# MAIN
# ======================================================

def send_daily_summary(deleted_emails):
    """Send a Discord summary of all emails deleted during this run.

    Args:
        deleted_emails: List of dicts with subject, sender, and category.
    """

    if not deleted_emails:
        send_discord_notification("🗑️ **Daily Cleanup Summary**\n\nNo emails were deleted today.")
        return

    # Group deleted emails by category
    promotions = [e for e in deleted_emails if e["category"] == "Promotion"]
    socials = [e for e in deleted_emails if e["category"] == "Social"]

    # Build the summary message
    lines = [
        "🗑️ **Daily Cleanup Summary**",
        f"\nTotal emails deleted: **{len(deleted_emails)}**",
    ]

    if promotions:
        lines.append(f"\n📢 **Promotions deleted ({len(promotions)}):**")
        for email in promotions[:20]:  # Cap at 20 to stay within Discord's 2000-char limit
            lines.append(f"• {email['subject']} — _{email['sender']}_")
        if len(promotions) > 20:
            lines.append(f"  ...and {len(promotions) - 20} more")

    if socials:
        lines.append(f"\n💬 **Social emails deleted ({len(socials)}):**")
        for email in socials[:20]:
            lines.append(f"• {email['subject']} — _{email['sender']}_")
        if len(socials) > 20:
            lines.append(f"  ...and {len(socials) - 20} more")

    summary = "\n".join(lines)

    # Discord messages have a 2000-char limit; truncate if needed
    if len(summary) > 1990:
        summary = summary[:1990] + "\n…"

    send_discord_notification(summary)


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