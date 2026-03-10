"""Gmail Agent - A simple script to authenticate and read Gmail messages.

This script uses the Gmail API to authenticate via OAuth 2.0 and fetch
the most recent emails from the user's inbox.
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# Gmail API scopes - currently set to read-only access
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authenticate():
    """Authenticate with Gmail API using OAuth 2.0.
    
    This function handles the OAuth 2.0 authentication flow:
    1. Checks if a saved token exists and loads it
    2. If no valid token exists, initiates the OAuth flow
    3. Saves the new token for future use
    
    Returns:
        Credentials: Authenticated credentials object for Gmail API
    """
    creds = None

    # Load token if it exists - avoids re-authentication on every run
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # If no valid credentials, login again using OAuth flow
    if not creds or not creds.valid:
        # Create OAuth flow from client secrets file (downloaded from Google Cloud Console)
        flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json", SCOPES
        )
        # Run local server to handle OAuth callback
        creds = flow.run_local_server(port=0)

        # Save token for future use to avoid repeated logins
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds


def read_emails(service):
    """Fetch and display email snippets from the inbox.
    
    Args:
        service: Authenticated Gmail API service object
    """
    # List the most recent 5 messages from the inbox
    results = service.users().messages().list(
        userId="me",  # "me" refers to the authenticated user
        labelIds=["INBOX"],  # Filter to inbox only
        maxResults=5  # Limit to 5 most recent emails
    ).execute()

    # Extract message list from results
    messages = results.get("messages", [])

    # Iterate through each message and fetch full details
    for msg in messages:
        # Get the full message details using message ID
        message = service.users().messages().get(
            userId="me",
            id=msg["id"]
        ).execute()

        # Print the email snippet (preview text)
        print("Email snippet:", message["snippet"])
        print("-" * 50)


def main():
    """Main function to orchestrate Gmail authentication and email reading."""
    # Authenticate and get credentials
    creds = authenticate()
    
    # Build the Gmail API service object
    service = build("gmail", "v1", credentials=creds)

    # Fetch and display recent emails
    read_emails(service)


if __name__ == "__main__":
    main()