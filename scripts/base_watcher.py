"""
Base Watcher Module

Abstract base class for all watcher scripts in the AI Employee system.
Watchers monitor external inputs and create actionable .md files in the Needs_Action folder.
"""

import time
import logging
from pathlib import Path
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Any, Optional


class BaseWatcher(ABC):
    """
    Abstract base class for all watcher scripts.
    
    Watchers run continuously, monitoring various inputs and creating
    actionable files for Claude Code to process.
    """
    
    def __init__(self, vault_path: str, check_interval: int = 60):
        """
        Initialize the watcher.
        
        Args:
            vault_path: Path to the Obsidian vault root
            check_interval: Seconds between checks (default: 60)
        """
        self.vault_path = Path(vault_path)
        self.needs_action = self.vault_path / 'Needs_Action'
        self.inbox = self.vault_path / 'Inbox'
        self.logs_dir = self.vault_path / 'Logs'
        self.check_interval = check_interval
        
        # Ensure directories exist
        self.needs_action.mkdir(parents=True, exist_ok=True)
        self.inbox.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up logging
        self._setup_logging()
        
        # Track processed items to avoid duplicates
        self.processed_ids: set = set()
        
    def _setup_logging(self) -> None:
        """Configure logging to file and console."""
        log_file = self.logs_dir / f'{self.__class__.__name__}_{datetime.now().strftime("%Y-%m-%d")}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(self.__class__.__name__)
        
    @abstractmethod
    def check_for_updates(self) -> List[Any]:
        """
        Check for new items to process.
        
        Returns:
            List of new items that need action
            
        Raises:
            Exception: If check fails
        """
        pass
    
    @abstractmethod
    def create_action_file(self, item: Any) -> Optional[Path]:
        """
        Create a .md action file in the Needs_Action folder.
        
        Args:
            item: The item to create an action file for
            
        Returns:
            Path to created file, or None if creation failed
        """
        pass
    
    def run(self) -> None:
        """
        Main run loop. Continuously checks for updates and creates action files.
        
        This method runs indefinitely until interrupted (Ctrl+C).
        """
        self.logger.info(f'Starting {self.__class__.__name__}')
        self.logger.info(f'Vault path: {self.vault_path}')
        self.logger.info(f'Check interval: {self.check_interval}s')
        
        try:
            while True:
                try:
                    items = self.check_for_updates()
                    if items:
                        self.logger.info(f'Found {len(items)} new item(s)')
                        for item in items:
                            filepath = self.create_action_file(item)
                            if filepath:
                                self.logger.info(f'Created action file: {filepath.name}')
                    else:
                        self.logger.debug('No new items')
                except Exception as e:
                    self.logger.error(f'Error processing items: {e}', exc_info=True)
                
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            self.logger.info(f'{self.__class__.__name__} stopped by user')
        except Exception as e:
            self.logger.error(f'Fatal error: {e}', exc_info=True)
            raise
    
    def load_processed_ids(self) -> None:
        """Load previously processed IDs from log to avoid reprocessing on restart."""
        log_file = self.logs_dir / f'{self.__class__.__name__}_processed.log'
        if log_file.exists():
            try:
                self.processed_ids = set(log_file.read_text().strip().split('\n'))
                self.processed_ids.discard('')  # Remove empty string if file was empty
                self.logger.info(f'Loaded {len(self.processed_ids)} previously processed IDs')
            except Exception as e:
                self.logger.warning(f'Could not load processed IDs: {e}')
                self.processed_ids = set()
        else:
            self.processed_ids = set()
    
    def save_processed_id(self, item_id: str) -> None:
        """
        Save a processed ID to persistent storage.
        
        Args:
            item_id: Unique identifier of the processed item
        """
        self.processed_ids.add(item_id)
        log_file = self.logs_dir / f'{self.__class__.__name__}_processed.log'
        try:
            # Append to file
            with open(log_file, 'a') as f:
                f.write(f'{item_id}\n')
        except Exception as e:
            self.logger.warning(f'Could not save processed ID: {e}')
    
    def is_processed(self, item_id: str) -> bool:
        """Check if an item has already been processed."""
        return item_id in self.processed_ids
    
    def update_dashboard(self, message: str) -> None:
        """
        Update the Dashboard.md with a new activity entry.
        
        Args:
            message: Message to add to recent activity
        """
        dashboard = self.vault_path / 'Dashboard.md'
        if not dashboard.exists():
            self.logger.warning('Dashboard.md not found')
            return
        
        try:
            content = dashboard.read_text()
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            activity_line = f'- [{timestamp}] {message}'
            
            # Find the "Recent Activity" section and add entry
            if '## ✅ Recent Activity' in content:
                lines = content.split('\n')
                new_lines = []
                for i, line in enumerate(lines):
                    new_lines.append(line)
                    if line == '## ✅ Recent Activity':
                        # Check if next line is empty or a list item
                        if i + 1 < len(lines) and lines[i + 1].strip() == '':
                            new_lines.append('')  # Keep the empty line
                        new_lines.append(activity_line)
                        # Skip the "*No recent activity*" placeholder if present
                        if i + 1 < len(lines) and '*No recent activity*' in lines[i + 1]:
                            continue
                
                content = '\n'.join(new_lines)
            else:
                # Append recent activity section before Quick Links
                activity_section = f'''
## ✅ Recent Activity

{activity_line}

'''
                content = content.replace('## 🔔 Alerts', activity_section + '## 🔔 Alerts')
            
            dashboard.write_text(content)
            self.logger.debug('Dashboard updated')
        except Exception as e:
            self.logger.error(f'Could not update dashboard: {e}')
