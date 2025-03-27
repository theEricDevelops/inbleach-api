# /app/utils/gmail.py

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
        subject = next((h['value'] for h in message['payload']['headers'] if h['name'].lower() == 'subject'), 'No Subject')
        print(f"Processing email: {subject}")

        # Extract HTML content
        html = self._get_html_body(message)
        if html:
            # Parse HTML to find unsubscribe links
            soup = BeautifulSoup(html, 'html.parser')
            for a_tag in soup.find_all('a'):
                href = a_tag.get('href', '')
                text = a_tag.text.strip()
                # Check for unsubscribe link in href or link text
                if (('unsubscribe' in href.lower() or 'unsubscribe' in text.lower()) and 
                    href.startswith(('http://', 'https://'))):
                    unsubscribe_url = href
                    print(f"Found unsubscribe link: {unsubscribe_url}")
                    try:
                        # Attempt to unsubscribe by visiting the link
                        response = requests.get(unsubscribe_url, timeout=10)
                        if response.status_code == 200:
                            print(f"Successfully unsubscribed from {unsubscribe_url}")
                        else:
                            print(f"Failed to unsubscribe from {unsubscribe_url} - Status code: {response.status_code}")
                    except requests.RequestException as e:
                        print(f"Error unsubscribing from {unsubscribe_url}: {e}")
                    break  # Unsubscribe only once per email
        else:
            print("No HTML content found in this email.")

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