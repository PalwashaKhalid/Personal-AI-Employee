"""
Email MCP Server

Simple MCP server for sending emails via Gmail.
This is a basic implementation for Silver tier.
For production, use the official Gmail MCP server.

Usage:
    python email_mcp_server.py --credentials path/to/credentials.json

Environment:
    GMAIL_CREDENTIALS_PATH: Path to OAuth2 credentials.json
"""

import os
import sys
import json
import base64
import argparse
from pathlib import Path
from email.mime.text import MIMEText
from datetime import datetime

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
except ImportError:
    print("Installing required dependencies...")
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 
                          'google-api-python-client', 'google-auth-httplib2', 'google-auth-oauthlib'])
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build


SCOPES = ['https://www.googleapis.com/auth/gmail.send']


class EmailMCPServer:
    """Simple email MCP server."""
    
    def __init__(self, credentials_path: str, vault_path: str):
        self.credentials_path = Path(credentials_path)
        self.vault_path = Path(vault_path)
        self.logs_dir = self.vault_path / 'Logs'
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.token_path = self.logs_dir / 'gmail_token.json'
        self.service = None
        self._authenticate()
    
    def _authenticate(self) -> None:
        """Authenticate with Gmail."""
        creds = None
        
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except:
                    creds = None
            
            if not creds:
                print("Please complete OAuth2 flow in browser...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0, open_browser=False)
            
            with open(self.token_path, 'w') as f:
                f.write(creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=creds)
        print("Email MCP Server authenticated")
    
    def send_email(self, to: str, subject: str, body: str, 
                   in_reply_to: str = None) -> dict:
        """Send an email."""
        try:
            message = MIMEText(body)
            message['to'] = to
            message['from'] = 'me'
            message['subject'] = subject
            
            if in_reply_to:
                message['In-Reply-To'] = in_reply_to
                message['References'] = in_reply_to
            
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            sent = self.service.users().messages().send(
                userId='me', body={'raw': raw}
            ).execute()
            
            # Log the action
            self._log_action('send_email', {
                'to': to,
                'subject': subject,
                'message_id': sent['id'],
                'status': 'success'
            })
            
            return {'success': True, 'message_id': sent['id']}
            
        except Exception as e:
            error_msg = str(e)
            self._log_action('send_email', {
                'to': to,
                'subject': subject,
                'error': error_msg,
                'status': 'failed'
            })
            return {'success': False, 'error': error_msg}
    
    def _log_action(self, action_type: str, details: dict) -> None:
        """Log action for audit trail."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action_type,
            'details': details
        }
        
        log_file = self.logs_dir / f'email_mcp_{datetime.now().strftime("%Y-%m-%d")}.json'
        logs = []
        if log_file.exists():
            try:
                logs = json.loads(log_file.read_text())
            except:
                pass
        
        logs.append(log_entry)
        log_file.write_text(json.dumps(logs, indent=2))


def main():
    """Main entry point for MCP server."""
    parser = argparse.ArgumentParser(description='Email MCP Server')
    parser.add_argument('--credentials', type=str, 
                        default=os.getenv('GMAIL_CREDENTIALS_PATH', 'credentials.json'),
                        help='Path to Gmail credentials.json')
    parser.add_argument('--vault', type=str, default='../Vault',
                        help='Path to Obsidian vault')
    
    args = parser.parse_args()
    
    server = EmailMCPServer(args.credentials, args.vault)
    
    # Simple command-line interface
    print("\nEmail MCP Server Ready")
    print("Commands: send, quit")
    
    while True:
        try:
            cmd = input("\n> ").strip()
            
            if cmd.lower() == 'quit':
                break
            
            elif cmd.lower() == 'send':
                to = input("To: ").strip()
                subject = input("Subject: ").strip()
                body = input("Body: ").strip()
                
                result = server.send_email(to, subject, body)
                print(f"Result: {result}")
            
            else:
                print("Unknown command. Use 'send' or 'quit'.")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
    
    print("Email MCP Server stopped")


if __name__ == '__main__':
    main()
