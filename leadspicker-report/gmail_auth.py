"""
One-time Gmail OAuth2 setup.
Run this once in the terminal to get a refresh token.
It will open a browser for you to approve access, then write
GMAIL_REFRESH_TOKEN to your .env file automatically.

Usage:
  python3 leadspicker-report/gmail_auth.py
"""

import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import dotenv_values, set_key

CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "gmail_credentials.json")
ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]

def main():
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)

    refresh_token = creds.refresh_token
    client_id     = creds.client_id
    client_secret = creds.client_secret

    set_key(ENV_PATH, "GMAIL_REFRESH_TOKEN", refresh_token)
    set_key(ENV_PATH, "GMAIL_CLIENT_ID",     client_id)
    set_key(ENV_PATH, "GMAIL_CLIENT_SECRET", client_secret)

    print()
    print("✓ Auth complete. The following were written to .env:")
    print("  GMAIL_REFRESH_TOKEN")
    print("  GMAIL_CLIENT_ID")
    print("  GMAIL_CLIENT_SECRET")
    print()
    print("You can now run report.py — Gmail drafts will be created automatically.")

if __name__ == "__main__":
    main()
