"""
Gmail Watcher Module

Monitors Gmail for new unread/important emails and creates action files.
Uses Gmail API with OAuth2 authentication.

Setup:
1. Enable Gmail API: https://console.cloud.google.com/apis/library/gmail.googleapis.com
2. Create OAuth2 credentials
3. Download credentials.json to scripts/ folder
4. First run will open browser for authentication

Usage:
    python gmail_watcher.py ../Vault

Environment Variables:
    GMAIL_CREDENTIALS_PATH: Path to credentials.json (default: credentials.json)
"""

import os
import base64
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from email.mime.text import MIMEText

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("Gmail dependencies not installed. Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    raise

from base_watcher import BaseWatcher


# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 
          'https://www.googleapis.com/auth/gmail.send']


class GmailMessage:
    """Represents a Gmail message."""
    
    def __init__(self, message_id: str, thread_id: str, snippet: str, headers: Dict[str, str], body: str = ''):
        self.message_id = message_id
        self.thread_id = thread_id
        self.snippet = snippet
        self.headers = headers
        self.body = body
        self.from_email = headers.get('From', '')
        self.to_email = headers.get('To', '')
        self.subject = headers.get('Subject', 'No Subject')
        self.date = headers.get('Date', '')
        self.created = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'message_id': self.message_id,
            'thread_id': self.thread_id,
            'snippet': self.snippet,
            'headers': self.headers,
            'body': self.body,
            'from': self.from_email,
            'to': self.to_email,
            'subject': self.subject,
            'date': self.date,
            'created': self.created.isoformat()
        }


class GmailWatcher(BaseWatcher):
    """
    Watches Gmail for new unread/important messages.
    
    Creates action files in Needs_Action folder for each new email.
    """
    
    def __init__(self, vault_path: str, credentials_path: Optional[str] = None, 
                 check_interval: int = 120, query: str = 'is:unread is:important'):
        """
        Initialize the Gmail watcher.
        
        Args:
            vault_path: Path to the Obsidian vault root
            credentials_path: Path to Gmail OAuth credentials.json
            check_interval: Seconds between checks (default: 120)
            query: Gmail search query for messages to fetch
        """
        super().__init__(vault_path, check_interval)
        
        # Set up credentials path
        if credentials_path:
            self.credentials_path = Path(credentials_path)
        else:
            self.credentials_path = Path(os.getenv('GMAIL_CREDENTIALS_PATH', 'credentials.json'))
        
        self.token_path = self.logs_dir / 'gmail_token.json'
        self.query = query
        self.service: Optional[Any] = None
        
        # Track processed message IDs
        self.load_processed_ids()
        
        # Authenticate
        self._authenticate()
        
        self.logger.info(f'Gmail query: {self.query}')
    
    def _authenticate(self) -> None:
        """Authenticate with Gmail API using OAuth2."""
        creds = None
        
        # Load existing token
        if self.token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(
                    self.token_path, SCOPES
                )
                self.logger.info('Loaded existing Gmail credentials')
            except Exception as e:
                self.logger.warning(f'Could not load token: {e}')
                creds = None
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    self.logger.info('Refreshed Gmail credentials')
                except Exception as e:
                    self.logger.warning(f'Could not refresh token: {e}')
                    creds = None
            
            if not creds:
                if not self.credentials_path.exists():
                    self.logger.error(
                        f'Credentials file not found: {self.credentials_path}\n'
                        'Please download credentials.json from Google Cloud Console'
                    )
                    raise FileNotFoundError(f'Gmail credentials not found at {self.credentials_path}')
                
                self.logger.info('Starting OAuth2 flow...')
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0, open_browser=False)
                self.logger.info('OAuth2 flow complete')
            
            # Save credentials
            try:
                with open(self.token_path, 'w') as token:
                    token.write(creds.to_json())
                self.logger.info(f'Saved token to {self.token_path}')
            except Exception as e:
                self.logger.warning(f'Could not save token: {e}')
        
        # Build service
        self.service = build('gmail', 'v1', credentials=creds)
        self.logger.info('Gmail service initialized')
    
    def check_for_updates(self) -> List[GmailMessage]:
        """
        Check Gmail for new unread/important messages.
        
        Returns:
            List of new GmailMessage objects
        """
        if not self.service:
            self.logger.warning('Gmail service not available')
            return []
        
        try:
            # Fetch messages
            results = self.service.users().messages().list(
                userId='me',
                q=self.query,
                maxResults=10
            ).execute()
            
            messages = results.get('messages', [])
            new_messages = []
            
            for msg in messages:
                if msg['id'] not in self.processed_ids:
                    # Fetch full message
                    message = self._fetch_message(msg['id'])
                    if message:
                        new_messages.append(message)
                        self.logger.info(f'New email: {message.subject} from {message.from_email}')
            
            return new_messages
            
        except HttpError as error:
            self.logger.error(f'Gmail API error: {error}')
            return []
        except Exception as e:
            self.logger.error(f'Error checking Gmail: {e}')
            return []
    
    def _fetch_message(self, message_id: str) -> Optional[GmailMessage]:
        """
        Fetch full message details.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            GmailMessage object or None
        """
        try:
            msg = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = {}
            for header in msg['payload'].get('headers', []):
                headers[header['name']] = header['value']
            
            # Extract body
            body = self._extract_body(msg['payload'])
            
            return GmailMessage(
                message_id=message_id,
                thread_id=msg['threadId'],
                snippet=msg.get('snippet', ''),
                headers=headers,
                body=body
            )
            
        except Exception as e:
            self.logger.error(f'Error fetching message {message_id}: {e}')
            return None
    
    def _extract_body(self, payload: Dict) -> str:
        """Extract email body from payload."""
        body = ''
        
        # Check for multipart
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain' and 'body' in part:
                    data = part['body'].get('data', '')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
                        break
        # Check for simple body
        elif 'body' in payload:
            data = payload['body'].get('data', '')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
        
        return body
    
    def create_action_file(self, message: GmailMessage) -> Optional[Path]:
        """
        Create action file for new email.
        
        Args:
            message: GmailMessage to process
            
        Returns:
            Path to created action file
        """
        try:
            # Create action file
            safe_subject = self._sanitize_filename(message.subject)
            action_path = self.needs_action / f'EMAIL_{message.message_id}_{safe_subject[:30]}.md'
            
            # Determine priority based on sender/subject
            priority = self._determine_priority(message)
            
            content = f'''---
type: email
from: {message.from_email}
to: {message.to_email}
subject: {message.subject}
received: {datetime.now().isoformat()}
message_id: {message.message_id}
thread_id: {message.thread_id}
priority: {priority}
status: pending
---

# Email Received

## Header Information
- **From:** {message.from_email}
- **To:** {message.to_email}
- **Subject:** {message.subject}
- **Date:** {message.date}
- **Received:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Email Content

{message.body if message.body else message.snippet}

---

## Suggested Actions

- [ ] Read and understand email
- [ ] Draft reply (if needed)
- [ ] Take required action
- [ ] Mark as read in Gmail
- [ ] Move to Done when complete

---

## Reply Draft

*Draft your reply here*

---

## Processing Notes

*Add notes about how this email was processed*

'''
            action_path.write_text(content)
            
            # Mark as processed
            self.save_processed_id(message.message_id)
            
            # Update dashboard
            self.update_dashboard(f'Email received: {message.subject[:50]} from {message.from_email}')
            
            return action_path
            
        except Exception as e:
            self.logger.error(f'Error creating action file: {e}', exc_info=True)
            return None
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize string for use in filename."""
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename.strip()
    
    def _determine_priority(self, message: GmailMessage) -> str:
        """Determine email priority based on content."""
        subject_lower = message.subject.lower()
        from_lower = message.from_email.lower()
        
        # High priority keywords
        high_priority_keywords = ['urgent', 'asap', 'invoice', 'payment', 'deadline', 'important']
        
        # Check for high priority
        if any(keyword in subject_lower for keyword in high_priority_keywords):
            return 'high'
        
        # Check for known important domains
        important_domains = ['client', 'customer', 'boss', 'manager']
        if any(domain in from_lower for domain in important_domains):
            return 'high'
        
        # Check for low priority
        low_priority_keywords = ['newsletter', 'unsubscribe', 'promotion', 'sale']
        if any(keyword in subject_lower for keyword in low_priority_keywords):
            return 'low'
        
        return 'medium'
    
    def mark_as_read(self, message_id: str) -> bool:
        """
        Mark a Gmail message as read.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            True if successful
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            self.logger.info(f'Marked message {message_id} as read')
            return True
        except Exception as e:
            self.logger.error(f'Error marking message as read: {e}')
            return False
    
    def send_email(self, to: str, subject: str, body: str, 
                   in_reply_to: Optional[str] = None) -> bool:
        """
        Send an email via Gmail.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body
            in_reply_to: Message ID to reply to (optional)
            
        Returns:
            True if successful
        """
        try:
            # Create message
            message = MIMEText(body)
            message['to'] = to
            message['from'] = 'me'
            message['subject'] = subject
            
            if in_reply_to:
                message['In-Reply-To'] = in_reply_to
                message['References'] = in_reply_to
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send
            sent_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            self.logger.info(f'Email sent to {to}, message ID: {sent_message["id"]}')
            return True
            
        except Exception as e:
            self.logger.error(f'Error sending email: {e}')
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Gmail Watcher for AI Employee')
    parser.add_argument('vault_path', type=str, help='Path to Obsidian vault')
    parser.add_argument('--credentials', type=str, default=None,
                        help='Path to Gmail credentials.json')
    parser.add_argument('--interval', type=int, default=120,
                        help='Check interval in seconds (default: 120)')
    parser.add_argument('--query', type=str, default='is:unread is:important',
                        help='Gmail search query (default: is:unread is:important)')
    
    args = parser.parse_args()
    
    watcher = GmailWatcher(
        vault_path=args.vault_path,
        credentials_path=args.credentials,
        check_interval=args.interval,
        query=args.query
    )
    watcher.run()


if __name__ == '__main__':
    main()
