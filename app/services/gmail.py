# /app/services/gmail.py
import os
import secrets

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import CREDENTIALS_DIR, CREDENTIALS_FILE, TOKEN_FILE

class GmailService:
    def __init__(self, credentials_file=CREDENTIALS_FILE):
        """
        Initialize the GmailService class with paths to credentials and token files.

        Args:
            credentials_file (str): Path to the OAuth 2.0 client credentials JSON file.
            token_file (str): Path to the file where OAuth tokens are stored.
        """
        self.scopes = ['https://www.googleapis.com/auth/gmail.modify']
        self.redirect_uri = "http://localhost:8000/auth/callback/google"
        self.credentials_file = os.path.join(CREDENTIALS_DIR, credentials_file)
        self.flow = Flow.from_client_secrets_file(
            self.credentials_file,
            scopes=self.scopes,
            redirect_uri=self.redirect_uri
        )
    
    def get_auth_url(self):
        """
        Generate the authorization URL for the user to consent.

        Returns:
            tuple: (auth_url, state) where auth_url is the URL to redirect to, and state is a CSRF token.
        """
        state = secrets.token_urlsafe(16)
        auth_url, _ = self.flow.authorization_url(prompt='consent', state=state)
        return auth_url, state

    def fetch_token(self, code):
        """
        Exchange the authorization code for access and refresh tokens.

        Args:
            code (str): The authorization code from Google.

        Returns:
            Credentials: The user's OAuth2 credentials.
        """
        self.flow.fetch_token(code=code)
        return self.flow.credentials
    
    def get_service(self, creds):
        """
        Build and return the Gmail API service object.

        Args:
            creds (Credentials): The user's OAuth2 credentials.

        Returns:
            googleapiclient.discovery.Resource: The Gmail API service object.
        """
        return build('gmail', 'v1', credentials=creds)