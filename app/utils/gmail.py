# /app/utils/gmail.py

import re
from app.services.gmail import GmailService
from datetime import date, timedelta
import base64
from bs4 import BeautifulSoup
import requests

class GmailUtils:
    def __init__(self, service: GmailService):
        """
        Initialize GmailUtils with an existing Gmail API service.

        Args:
            service: The Gmail API service object.
        """
        self.service = service

    def fetch_emails(self, days=30):
        """
        Fetch emails from the past specified number of days.

        Args:
            days (int): Number of days to look back for emails. Default is 30.

        Returns:
            list: A list of email message objects.
        """
        past_date = date.today() - timedelta(days=days)
        query = f"after:{past_date.strftime('%Y/%m/%d')}"
        print(f"Fetching emails after {past_date.strftime('%Y/%m/%d')}")

        messages = []
        page_token = None
        while True:
            response = self.service.users().messages().list(userId='me', q=query, pageToken=page_token).execute()
            messages.extend(response.get('messages', []))
            page_token = response.get('nextPageToken')
            if not page_token:
                break
        return messages
    
    def _find_url(input: str) -> str:
        """Finds the first URL in a string.

        Args:
            input: The string to search for URLs in.

        Returns:
            The first URL found in the string, or None if no URL is found.
        """
        match = re.search(r"<(https?://[^>]+)>", input)
        if match:
            return match.group(1)
        else:
            return None

    def _get_html_body(self, message):
        """
        Extract and decode the HTML body from a Gmail message.

        Args:
            message (dict): The full message object from Gmail API.

        Returns:
            str or None: The decoded HTML content if found, else None.
        """
        def find_html_part(part):
            if part['mimeType'] == 'text/html':
                return part
            elif 'parts' in part:
                for subpart in part['parts']:
                    result = find_html_part(subpart)
                    if result:
                        return result
            return None

        payload = message['payload']
        html_part = find_html_part(payload)
        if html_part:
            headers = html_part.get('headers', [])
            content_type = next((h['value'] for h in headers if h['name'].lower() == 'content-type'), '')
            charset = 'utf-8'  # Default charset
            if 'charset=' in content_type.lower():
                charset = content_type.split('charset=')[1].split(';')[0].strip().lower()
            body_data = html_part['body']['data']
            # Add padding if necessary for base64 decoding
            body_bytes = base64.urlsafe_b64decode(body_data + '==')
            try:
                return body_bytes.decode(charset)
            except (LookupError, UnicodeDecodeError):
                return body_bytes.decode('utf-8', errors='replace')
        return None

    def process_email(self, message_id):
        """
        Process a single email to find and follow unsubscribe links.

        Args:
            message_id (str): The ID of the email message to process.
        """
        message = self.service.users().messages().get(userId='me', id=message_id, format='full').execute()
        labels = message['labelIds']
        if 'CATEGORY_PROMOTIONS' in labels:
            subject = next((h['value'] for h in message['payload']['headers'] if h['name'].lower() == 'subject'), 'No Subject')
            unsubscribe_header = next((h['value'] for h in message['payload']['headers'] if h['name'].lower() == 'list-unsubscribe'), None)
            print(f"Processing email: {subject}")
            
            unsubscribe_url = re.findall(r'<(https?://[^>]+)>', unsubscribe_header) or [None]
            unsubscribe_url = unsubscribe_url[0]
            
            print(f"Found unsubscribe link: {unsubscribe_url}")

            if not unsubscribe_url:
                print("No unsubscribe link found.")
                return False
            
            print(f"Found unsubscribe link: {unsubscribe_url}")
            try:
                # Attempt to unsubscribe by visiting the link
                response = requests.get(
                    unsubscribe_url, 
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3' 
                    },
                    timeout=10, 
                    allow_redirects=True)
                response.raise_for_status()
                print(f"Successfully unsubscribed from {unsubscribe_url}")
                return True
            except requests.RequestException as e:
                print(f"Error unsubscribing from {unsubscribe_url}: {e}")
        return False

    def unsubscribe_from_marketing_emails(self, days=30):
        """
        Fetch emails from the past specified number of days and attempt to unsubscribe from those with unsubscribe links.

        Args:
            days (int): Number of days to look back for emails. Default is 30.
        """
        messages = self.fetch_emails(days)
        print(f"Found {len(messages)} emails to process.")
        for msg in messages:
            self.process_email(msg['id'])