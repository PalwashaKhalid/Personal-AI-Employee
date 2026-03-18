"""
File System Watcher Module

Monitors a drop folder for new files and creates action files in the Needs_Action folder.
This is the simplest watcher to set up and test for the Bronze tier.

Usage:
    python filesystem_watcher.py /path/to/vault

Or with custom drop folder:
    python filesystem_watcher.py /path/to/vault --drop-folder /path/to/drop
"""

import argparse
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from base_watcher import BaseWatcher


class FileDropItem:
    """Represents a file dropped for processing."""
    
    def __init__(self, source_path: Path, file_id: str):
        self.source_path = source_path
        self.file_id = file_id
        self.name = source_path.name
        self.size = source_path.stat().st_size
        self.created = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'source_path': str(self.source_path),
            'file_id': self.file_id,
            'name': self.name,
            'size': self.size,
            'created': self.created.isoformat()
        }


class FilesystemWatcher(BaseWatcher):
    """
    Watches a drop folder for new files.
    
    When a file is detected, it:
    1. Copies the file to the vault
    2. Creates a metadata .md file in Needs_Action
    3. Logs the action
    """
    
    def __init__(self, vault_path: str, drop_folder: Optional[str] = None, check_interval: int = 30):
        """
        Initialize the filesystem watcher.
        
        Args:
            vault_path: Path to the Obsidian vault root
            drop_folder: Path to the drop folder (default: vault/Drop)
            check_interval: Seconds between checks (default: 30)
        """
        super().__init__(vault_path, check_interval)
        
        # Set up drop folder
        if drop_folder:
            self.drop_folder = Path(drop_folder)
        else:
            self.drop_folder = self.vault_path / 'Drop'
        
        self.drop_folder.mkdir(parents=True, exist_ok=True)
        self.files_folder = self.vault_path / 'Files'
        self.files_folder.mkdir(parents=True, exist_ok=True)
        
        # Track file hashes to detect new files
        self.known_files: Dict[str, str] = {}
        self._load_known_files()
        
        self.logger.info(f'Drop folder: {self.drop_folder}')
    
    def _load_known_files(self) -> None:
        """Load hashes of known files to avoid reprocessing."""
        hash_file = self.logs_dir / 'filesystem_hashes.log'
        if hash_file.exists():
            try:
                for line in hash_file.read_text().strip().split('\n'):
                    if ':' in line:
                        filepath, filehash = line.split(':', 1)
                        self.known_files[filepath] = filehash
                self.logger.info(f'Loaded {len(self.known_files)} known file hashes')
            except Exception as e:
                self.logger.warning(f'Could not load known files: {e}')
    
    def _calculate_hash(self, filepath: Path) -> str:
        """Calculate MD5 hash of a file."""
        hash_md5 = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _save_hash(self, filepath: Path, filehash: str) -> None:
        """Save file hash to persistent storage."""
        hash_file = self.logs_dir / 'filesystem_hashes.log'
        with open(hash_file, 'a') as f:
            f.write(f'{filepath}:{filehash}\n')
    
    def check_for_updates(self) -> List[FileDropItem]:
        """
        Check drop folder for new files.
        
        Returns:
            List of new FileDropItem objects
        """
        new_items = []
        
        if not self.drop_folder.exists():
            self.logger.warning(f'Drop folder does not exist: {self.drop_folder}')
            return []
        
        for filepath in self.drop_folder.iterdir():
            if filepath.is_file() and not filepath.name.startswith('.'):
                filehash = self._calculate_hash(filepath)
                
                # Check if this is a new file (by hash)
                if str(filepath) not in self.known_files or self.known_files[str(filepath)] != filehash:
                    file_id = f'{filepath.stem}_{datetime.now().strftime("%Y%m%d%H%M%S")}'
                    item = FileDropItem(filepath, file_id)
                    new_items.append(item)
                    self.logger.info(f'New file detected: {filepath.name} ({item.size} bytes)')
        
        return new_items
    
    def create_action_file(self, item: FileDropItem) -> Optional[Path]:
        """
        Create action file for dropped file.
        
        Args:
            item: FileDropItem to process
            
        Returns:
            Path to created action file
        """
        try:
            # Copy file to vault/Files
            dest_path = self.files_folder / f'{item.file_id}_{item.name}'
            shutil.copy2(item.source_path, dest_path)
            self.logger.info(f'Copied file to: {dest_path}')
            
            # Remove from drop folder
            item.source_path.unlink()
            self.logger.info(f'Removed from drop folder: {item.source_path}')
            
            # Save hash
            self._save_hash(dest_path, self._calculate_hash(dest_path))
            
            # Create metadata action file
            action_path = self.needs_action / f'FILE_{item.file_id}.md'
            content = f'''---
type: file_drop
original_name: {item.name}
file_id: {item.file_id}
size: {item.size}
received: {datetime.now().isoformat()}
status: pending
priority: medium
---

# File Drop for Processing

## File Details
- **Original Name:** {item.name}
- **Size:** {self._format_size(item.size)}
- **Received:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Location:** [[../Files/{action_path.stem}_{item.name}]]

## Content Preview

*Add content preview or description here*

---

## Suggested Actions

- [ ] Review file content
- [ ] Categorize file
- [ ] Take required action
- [ ] Move to Done when complete

---

## Processing Notes

*Add notes about how this file was processed*

'''
            action_path.write_text(content)
            
            # Update dashboard
            self.update_dashboard(f'File dropped: {item.name}')
            
            return action_path
            
        except Exception as e:
            self.logger.error(f'Error creating action file: {e}', exc_info=True)
            return None
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f'{size_bytes:.1f} {unit}'
            size_bytes /= 1024
        return f'{size_bytes:.1f} TB'


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='File System Watcher for AI Employee')
    parser.add_argument('vault_path', type=str, help='Path to Obsidian vault')
    parser.add_argument('--drop-folder', type=str, default=None, 
                        help='Custom drop folder path (default: vault/Drop)')
    parser.add_argument('--interval', type=int, default=30,
                        help='Check interval in seconds (default: 30)')
    
    args = parser.parse_args()
    
    watcher = FilesystemWatcher(
        vault_path=args.vault_path,
        drop_folder=args.drop_folder,
        check_interval=args.interval
    )
    watcher.run()


if __name__ == '__main__':
    main()
