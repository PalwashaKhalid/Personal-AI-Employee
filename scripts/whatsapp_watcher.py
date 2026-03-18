"""
WhatsApp Watcher Module

Monitors WhatsApp Web for new messages containing keywords.
Uses Playwright for browser automation.

Note: This uses WhatsApp Web automation. Be aware of WhatsApp's terms of service.
For production use, consider the official WhatsApp Business API.

Setup:
1. Install Playwright: pip install playwright
2. Install browsers: playwright install
3. First run will require QR code scan to authenticate

Usage:
    python whatsapp_watcher.py ../Vault

Environment Variables:
    WHATSAPP_SESSION_PATH: Path to store browser session data
"""

import os
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
except ImportError:
    print("Playwright not installed. Run: pip install playwright && playwright install")
    raise

from base_watcher import BaseWatcher


class WhatsAppMessage:
    """Represents a WhatsApp message."""
    
    def __init__(self, chat_name: str, message_text: str, timestamp: datetime, 
                 is_group: bool = False, sender: str = ''):
        self.chat_name = chat_name
        self.message_text = message_text
        self.timestamp = timestamp
        self.is_group = is_group
        self.sender = sender if sender else chat_name
        self.message_id = f'{chat_name}_{timestamp.strftime("%Y%m%d%H%M%S")}'
        self.created = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'chat_name': self.chat_name,
            'message_text': self.message_text,
            'timestamp': self.timestamp.isoformat(),
            'is_group': self.is_group,
            'sender': self.sender,
            'message_id': self.message_id,
            'created': self.created.isoformat()
        }


class WhatsAppWatcher(BaseWatcher):
    """
    Watches WhatsApp Web for new messages containing keywords.
    
    Uses Playwright to automate WhatsApp Web and extract messages.
    """
    
    def __init__(self, vault_path: str, session_path: Optional[str] = None,
                 check_interval: int = 60, keywords: Optional[List[str]] = None):
        """
        Initialize the WhatsApp watcher.
        
        Args:
            vault_path: Path to the Obsidian vault root
            session_path: Path to store browser session data
            check_interval: Seconds between checks (default: 60)
            keywords: List of keywords to trigger action (default: urgent, asap, invoice, payment)
        """
        super().__init__(vault_path, check_interval)
        
        # Set up session path
        if session_path:
            self.session_path = Path(session_path)
        else:
            self.session_path = os.getenv('WHATSAPP_SESSION_PATH', str(self.logs_dir / 'whatsapp_session'))
        
        self.session_path = Path(self.session_path)
        self.session_path.mkdir(parents=True, exist_ok=True)
        
        # Keywords to watch for
        self.keywords = keywords or ['urgent', 'asap', 'invoice', 'payment', 'help', 'important']
        
        # Track processed messages
        self.load_processed_ids()
        
        self.logger.info(f'Session path: {self.session_path}')
        self.logger.info(f'Keywords: {self.keywords}')
    
    def check_for_updates(self) -> List[WhatsAppMessage]:
        """
        Check WhatsApp Web for new messages with keywords.
        
        Returns:
            List of new WhatsAppMessage objects
        """
        new_messages = []
        
        try:
            with sync_playwright() as p:
                # Launch browser with persistent context
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=str(self.session_path),
                    headless=True,
                    args=[
                        '--disable-gpu',
                        '--disable-dev-shm-usage',
                        '--no-sandbox'
                    ]
                )
                
                page = browser.pages[0] if browser.pages else browser.new_page()
                
                # Navigate to WhatsApp Web
                self.logger.info('Navigating to WhatsApp Web...')
                page.goto('https://web.whatsapp.com', wait_until='networkidle')
                
                # Wait for chat list (indicates login)
                try:
                    page.wait_for_selector('[data-testid="chat-list"]', timeout=30000)
                    self.logger.info('WhatsApp Web loaded')
                except Exception:
                    self.logger.error('WhatsApp Web not loaded. Please scan QR code manually.')
                    browser.close()
                    return []
                
                # Give page time to load messages
                page.wait_for_timeout(5000)
                
                # Find unread chats
                unread_chats = self._get_unread_chats(page)
                self.logger.info(f'Found {len(unread_chats)} unread chat(s)')
                
                for chat_data in unread_chats:
                    messages = self._extract_messages(chat_data)
                    for msg in messages:
                        if self._contains_keywords(msg.message_text):
                            if msg.message_id not in self.processed_ids:
                                new_messages.append(msg)
                                self.logger.info(f'New keyword message from {msg.chat_name}')
                
                browser.close()
                
        except Exception as e:
            self.logger.error(f'Error checking WhatsApp: {e}', exc_info=True)
        
        return new_messages
    
    def _get_unread_chats(self, page: Page) -> List[Dict[str, Any]]:
        """
        Get list of unread chats from WhatsApp Web.
        
        Args:
            page: Playwright page object
            
        Returns:
            List of chat data dictionaries
        """
        chats = []
        
        try:
            # Find all chat elements with unread indicator
            chat_elements = page.query_selector_all('[data-testid="chat-list"] > div[role="row"]')
            
            for chat in chat_elements:
                try:
                    # Check if chat has unread messages
                    unread_badge = chat.query_selector('[data-testid="unread-chat-msg-count"]')
                    if unread_badge:
                        # Extract chat info
                        chat_name_elem = chat.query_selector('[dir="auto"]')
                        chat_name = chat_name_elem.inner_text() if chat_name_elem else 'Unknown'
                        
                        # Extract last message
                        message_elem = chat.query_selector('[dir="auto"]:last-child')
                        last_message = message_elem.inner_text() if message_elem else ''
                        
                        chats.append({
                            'name': chat_name,
                            'last_message': last_message,
                            'element': chat
                        })
                except Exception as e:
                    self.logger.debug(f'Error extracting chat: {e}')
            
        except Exception as e:
            self.logger.error(f'Error getting unread chats: {e}')
        
        return chats
    
    def _extract_messages(self, chat_data: Dict[str, Any]) -> List[WhatsAppMessage]:
        """
        Extract messages from chat data.
        
        Args:
            chat_data: Chat data dictionary
            
        Returns:
            List of WhatsAppMessage objects
        """
        messages = []
        
        try:
            # For now, use the last message from the chat
            # In production, you would click the chat and extract all messages
            last_message = chat_data.get('last_message', '')
            
            if last_message:
                msg = WhatsAppMessage(
                    chat_name=chat_data['name'],
                    message_text=last_message,
                    timestamp=datetime.now()
                )
                messages.append(msg)
                
        except Exception as e:
            self.logger.error(f'Error extracting messages: {e}')
        
        return messages
    
    def _contains_keywords(self, text: str) -> bool:
        """Check if text contains any watched keywords."""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.keywords)
    
    def create_action_file(self, message: WhatsAppMessage) -> Optional[Path]:
        """
        Create action file for WhatsApp message.
        
        Args:
            message: WhatsAppMessage to process
            
        Returns:
            Path to created action file
        """
        try:
            # Create action file
            safe_chat_name = self._sanitize_filename(message.chat_name)
            action_path = self.needs_action / f'WHATSAPP_{safe_chat_name}_{message.timestamp.strftime("%Y%m%d%H%M%S")}.md'
            
            # Determine priority
            priority = self._determine_priority(message.message_text)
            
            content = f'''---
type: whatsapp
from: {message.sender}
chat: {message.chat_name}
received: {datetime.now().isoformat()}
message_time: {message.timestamp.isoformat()}
priority: {priority}
status: pending
is_group: {message.is_group}
---

# WhatsApp Message Received

## Message Information
- **From:** {message.sender}
- **Chat:** {message.chat_name}
- **Received:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Is Group:** {'Yes' if message.is_group else 'No'}

---

## Message Content

{message.message_text}

---

## Suggested Actions

- [ ] Read and understand message
- [ ] Draft reply (if needed)
- [ ] Take required action
- [ ] Reply via WhatsApp
- [ ] Move to Done when complete

---

## Reply Draft

*Draft your reply here*

---

## Processing Notes

*Add notes about how this message was processed*

'''
            action_path.write_text(content)
            
            # Mark as processed
            self.save_processed_id(message.message_id)
            
            # Update dashboard
            self.update_dashboard(f'WhatsApp message: {message.chat_name} - {message.message_text[:30]}...')
            
            return action_path
            
        except Exception as e:
            self.logger.error(f'Error creating action file: {e}', exc_info=True)
            return None
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize string for use in filename."""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename.strip().replace(' ', '_')[:50]
    
    def _determine_priority(self, text: str) -> str:
        """Determine message priority based on content."""
        text_lower = text.lower()
        
        # High priority keywords
        high_priority = ['urgent', 'asap', 'emergency', 'help', 'important']
        if any(kw in text_lower for kw in high_priority):
            return 'high'
        
        # Medium priority (business related)
        medium_priority = ['invoice', 'payment', 'meeting', 'deadline', 'project']
        if any(kw in text_lower for kw in medium_priority):
            return 'medium'
        
        return 'low'
    
    def send_message(self, chat_name: str, message: str) -> bool:
        """
        Send a WhatsApp message.
        
        Args:
            chat_name: Name of chat/contact
            message: Message to send
            
        Returns:
            True if successful
        """
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=str(self.session_path),
                    headless=False  # Show browser for this operation
                )
                
                page = browser.pages[0] if browser.pages else browser.new_page()
                page.goto('https://web.whatsapp.com', wait_until='networkidle')
                
                # Wait for chat list
                page.wait_for_selector('[data-testid="chat-list"]', timeout=30000)
                
                # Search for chat
                search_box = page.query_selector('[data-testid="search"]')
                if search_box:
                    search_box.click()
                    page.keyboard.type(chat_name)
                    page.wait_for_timeout(2000)
                    
                    # Click on first result
                    first_chat = page.query_selector('[data-testid="chat-list"] > div[role="row"]')
                    if first_chat:
                        first_chat.click()
                        page.wait_for_timeout(1000)
                        
                        # Type and send message
                        message_box = page.query_selector('[data-testid="compose-input"]')
                        if message_box:
                            message_box.click()
                            page.keyboard.type(message)
                            page.keyboard.press('Enter')
                            
                            self.logger.info(f'Message sent to {chat_name}')
                            browser.close()
                            return True
                
                browser.close()
                self.logger.warning(f'Could not send message to {chat_name}')
                return False
                
        except Exception as e:
            self.logger.error(f'Error sending WhatsApp message: {e}')
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='WhatsApp Watcher for AI Employee')
    parser.add_argument('vault_path', type=str, help='Path to Obsidian vault')
    parser.add_argument('--session-path', type=str, default=None,
                        help='Path to store browser session')
    parser.add_argument('--interval', type=int, default=60,
                        help='Check interval in seconds (default: 60)')
    parser.add_argument('--keywords', type=str, nargs='+', default=None,
                        help='Keywords to watch for')
    
    args = parser.parse_args()
    
    watcher = WhatsAppWatcher(
        vault_path=args.vault_path,
        session_path=args.session_path,
        check_interval=args.interval,
        keywords=args.keywords
    )
    watcher.run()


if __name__ == '__main__':
    main()
