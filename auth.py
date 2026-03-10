"""Gmail OAuth 2.0 authentication."""

import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

from config import SCOPES


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
