"""Email actions — inbox scanning, promotion/social deletion, daily summary."""

from classifier import ai_classify_email
from discord_notify import send_discord_notification
from tracking import load_processed, save_processed


# ======================================================
# READ EMAILS WITH PAGINATION
# ======================================================

def read_emails(service):
    """Scan the entire inbox, classify each email, and take action.

    Paginates through all inbox messages (100 per page), skips
    already-processed emails, checks Gmail labels first for quick
    categorization, then falls back to AI classification for the rest.
    Trashes newsletters and spam, sends Discord alerts for job emails.

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

            # --------------------------------------------------
            # Optimization: check Gmail labels before calling AI
            # --------------------------------------------------
            label_ids = message.get("labelIds", [])

            if "CATEGORY_PROMOTIONS" in label_ids:
                # Gmail already tagged it as a promotion — skip AI
                category = "newsletter"
            elif "CATEGORY_SOCIAL" in label_ids:
                # Gmail already tagged it as social — skip AI
                category = "social"
            else:
                # Fall back to AI zero-shot classification
                category = ai_classify_email(subject, snippet)

            print("Sender:", sender)
            print("Subject:", subject)
            print("Category:", category)

            # ------------------------------------------------
            # Newsletter / Spam cleanup
            # ------------------------------------------------

            if category in ("newsletter", "spam"):
                # Move newsletters and spam to trash automatically
                print("Deleting", category + ":", subject)

                service.users().messages().trash(
                    userId="me",
                    id=msg["id"]
                ).execute()

                # Track the deleted email for the daily summary
                deleted_emails.append({"subject": subject, "sender": sender, "category": category.title()})

            # ------------------------------------------------
            # Social cleanup
            # ------------------------------------------------

            elif category == "social":
                # Move social emails to trash
                print("Deleting social:", subject)

                service.users().messages().trash(
                    userId="me",
                    id=msg["id"]
                ).execute()

                deleted_emails.append({"subject": subject, "sender": sender, "category": "Social"})

            # ------------------------------------------------
            # Job notification
            # ------------------------------------------------

            elif category == "job opportunity":
                # Send a Discord alert so we don't miss job-related emails
                notification = f"""
📧 **New Job Email**

Sender: {sender}
Subject: {subject}
"""

                send_discord_notification(notification)

            # "important email" → keep in inbox, no action needed

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
# DAILY SUMMARY
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
    newsletters = [e for e in deleted_emails if e["category"] == "Newsletter"]
    spams = [e for e in deleted_emails if e["category"] == "Spam"]
    socials = [e for e in deleted_emails if e["category"] == "Social"]

    # Build the summary message
    lines = [
        "🗑️ **Daily Cleanup Summary**",
        f"\nTotal emails deleted: **{len(deleted_emails)}**",
    ]

    for label, group, emoji in [
        ("Promotions", promotions, "📢"),
        ("Newsletters", newsletters, "📰"),
        ("Spam", spams, "🚫"),
        ("Social", socials, "💬"),
    ]:
        if group:
            lines.append(f"\n{emoji} **{label} deleted ({len(group)}):**")
            for email in group[:15]:  # Cap per category to stay within Discord's 2000-char limit
                lines.append(f"• {email['subject']} — _{email['sender']}_")
            if len(group) > 15:
                lines.append(f"  ...and {len(group) - 15} more")

    summary = "\n".join(lines)

    # Discord messages have a 2000-char limit; truncate if needed
    if len(summary) > 1990:
        summary = summary[:1990] + "\n…"

    send_discord_notification(summary)
