"""
Human-in-the-Loop (HITL) Approval Workflow

Manages approval requests for sensitive actions like payments, sending emails, etc.
Files flow: Pending_Approval -> (human moves to) -> Approved -> Execute -> Done
"""

import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging


class ApprovalManager:
    """
    Manages human-in-the-loop approval workflow.
    
    Sensitive actions create approval request files in Pending_Approval.
    Human reviews and moves to Approved or Rejected.
    Orchestrator executes approved actions.
    """
    
    # Action types that always require approval
    ALWAYS_REQUIRE_APPROVAL = [
        'payment',
        'send_email',
        'send_whatsapp',
        'post_social',
        'delete_file',
        'bank_transfer'
    ]
    
    # Approval thresholds
    PAYMENT_THRESHOLD = 500.0  # All payments require approval
    
    def __init__(self, vault_path: Path, logger: Optional[logging.Logger] = None):
        self.vault_path = vault_path
        self.pending_approval = vault_path / 'Pending_Approval'
        self.approved = vault_path / 'Approved'
        self.rejected = vault_path / 'Rejected'
        self.done = vault_path / 'Done'
        self.logs_dir = vault_path / 'Logs'
        
        # Ensure directories exist
        for folder in [self.pending_approval, self.approved, self.rejected]:
            folder.mkdir(parents=True, exist_ok=True)
        
        # Set up logging
        self.logger = logger or logging.getLogger(self.__class__.__name__)
    
    def create_approval_request(self, action_type: str, details: Dict[str, Any],
                                reason: str = '') -> Optional[Path]:
        """
        Create an approval request file.
        
        Args:
            action_type: Type of action (payment, send_email, etc.)
            details: Action details (amount, recipient, etc.)
            reason: Reason for approval request
            
        Returns:
            Path to created approval file
        """
        try:
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_type = action_type.replace(' ', '_').upper()
            filename = f'APPROVAL_{safe_type}_{timestamp}.md'
            filepath = self.pending_approval / filename
            
            # Build content
            content = self._build_approval_content(action_type, details, reason, filename)
            filepath.write_text(content)
            
            self.logger.info(f'Created approval request: {filename}')
            return filepath
            
        except Exception as e:
            self.logger.error(f'Error creating approval request: {e}')
            return None
    
    def _build_approval_content(self, action_type: str, details: Dict[str, Any],
                                reason: str, filename: str) -> str:
        """Build approval request Markdown content."""
        
        # Common fields
        created = datetime.now().isoformat()
        expires = datetime.now().replace(hour=23, minute=59).isoformat()
        
        # Action-specific content
        action_details = ''
        if action_type == 'payment':
            action_details = f'''
| Field | Value |
|-------|-------|
| Amount | ${details.get('amount', 0):.2f} |
| Recipient | {details.get('recipient', 'Unknown')} |
| Bank Details | {details.get('bank_details', 'N/A')} |
| Reference | {details.get('reference', '')} |
| Invoice # | {details.get('invoice_number', '')} |
'''
        elif action_type == 'send_email':
            action_details = f'''
| Field | Value |
|-------|-------|
| To | {details.get('to', 'Unknown')} |
| Subject | {details.get('subject', '')} |
| Body Preview | {details.get('body_preview', '')[:200]}... |
| Attachment | {details.get('attachment', 'None')} |
'''
        elif action_type == 'send_whatsapp':
            action_details = f'''
| Field | Value |
|-------|-------|
| Contact | {details.get('contact', 'Unknown')} |
| Message Preview | {details.get('message_preview', '')[:200]}... |
'''
        elif action_type == 'post_social':
            action_details = f'''
| Field | Value |
|-------|-------|
| Platform | {details.get('platform', 'Unknown')} |
| Content Preview | {details.get('content_preview', '')[:200]}... |
| Scheduled Time | {details.get('scheduled_time', 'Immediate')} |
'''
        else:
            action_details = '\n'.join(f'- **{k.replace("_", " ").title()}:** {v}' 
                                       for k, v in details.items())
        
        return f'''---
type: approval_request
action: {action_type}
created: {created}
expires: {expires}
status: pending
---

# Approval Required

**Action Type:** {action_type.replace('_', ' ').title()}

**Reason:** {reason if reason else 'Sensitive action requires human approval'}

---

## Action Details
{action_details}

---

## Instructions

### To Approve
Move this file to the `/Approved` folder.

### To Reject
Move this file to the `/Rejected` folder and add a comment explaining why.

### To Request Changes
Add a comment below and move back to `/Pending_Approval`.

---

## Comments

*Add comments here*

---

## Audit Trail

- **Created:** {created}
- **File:** {filename}

---

*This approval request was generated by AI Employee. 
Move to /Approved to execute, /Rejected to decline.*
'''
    
    def get_pending_requests(self) -> List[Path]:
        """Get all pending approval requests."""
        if not self.pending_approval.exists():
            return []
        return [f for f in self.pending_approval.iterdir() if f.suffix == '.md']
    
    def get_approved_requests(self) -> List[Path]:
        """Get all approved requests ready for execution."""
        if not self.approved.exists():
            return []
        return [f for f in self.approved.iterdir() if f.suffix == '.md']
    
    def get_rejected_requests(self) -> List[Path]:
        """Get all rejected requests."""
        if not self.rejected.exists():
            return []
        return [f for f in self.rejected.iterdir() if f.suffix == '.md']
    
    def parse_approval_file(self, filepath: Path) -> Dict[str, Any]:
        """
        Parse an approval request file.
        
        Args:
            filepath: Path to approval file
            
        Returns:
            Dictionary with approval details
        """
        try:
            content = filepath.read_text()
            
            # Extract frontmatter
            details = {}
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter = parts[1].strip()
                    for line in frontmatter.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            details[key.strip()] = value.strip()
            
            # Extract action details from body
            if '## Action Details' in content:
                details_section = content.split('## Action Details', 1)[1]
                if '##' in details_section:
                    details_section = details_section.split('##', 1)[0]
                details['body'] = details_section.strip()
            
            details['filepath'] = str(filepath)
            details['filename'] = filepath.name
            
            return details
            
        except Exception as e:
            self.logger.error(f'Error parsing approval file: {e}')
            return {}
    
    def approve_request(self, filepath: Path) -> bool:
        """
        Move a request from Pending_Approval to Approved.
        
        In production, this would be done by human via file explorer.
        This method is for programmatic approval.
        
        Args:
            filepath: Path to approval file
            
        Returns:
            True if successful
        """
        try:
            if filepath.parent != self.pending_approval:
                self.logger.warning('File is not in Pending_Approval')
                return False
            
            dest = self.approved / filepath.name
            shutil.move(str(filepath), str(dest))
            
            self.logger.info(f'Approved request: {filepath.name}')
            return True
            
        except Exception as e:
            self.logger.error(f'Error approving request: {e}')
            return False
    
    def reject_request(self, filepath: Path, reason: str = '') -> bool:
        """
        Move a request from Pending_Approval to Rejected.
        
        Args:
            filepath: Path to approval file
            reason: Reason for rejection
            
        Returns:
            True if successful
        """
        try:
            if filepath.parent != self.pending_approval:
                self.logger.warning('File is not in Pending_Approval')
                return False
            
            # Add rejection reason to file
            content = filepath.read_text()
            content += f'\n\n---\n\n## Rejected\n\n**Reason:** {reason}\n\n**Date:** {datetime.now().isoformat()}\n'
            filepath.write_text(content)
            
            dest = self.rejected / filepath.name
            shutil.move(str(filepath), str(dest))
            
            self.logger.info(f'Rejected request: {filepath.name}')
            return True
            
        except Exception as e:
            self.logger.error(f'Error rejecting request: {e}')
            return False
    
    def execute_approved_action(self, filepath: Path) -> bool:
        """
        Execute an approved action and move to Done.
        
        In production, this would trigger MCP servers.
        For now, just log and move to Done.
        
        Args:
            filepath: Path to approved file
            
        Returns:
            True if successful
        """
        try:
            details = self.parse_approval_file(filepath)
            action_type = details.get('action', 'unknown')
            
            self.logger.info(f'Executing approved action: {action_type}')
            
            # Log the execution
            self._log_execution(filepath, details)
            
            # Move to Done
            dest = self.done / filepath.name
            shutil.move(str(filepath), str(dest))
            
            self.logger.info(f'Action completed: {filepath.name}')
            return True
            
        except Exception as e:
            self.logger.error(f'Error executing action: {e}')
            return False
    
    def _log_execution(self, filepath: Path, details: Dict[str, Any]) -> None:
        """Log action execution for audit trail."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action_type': details.get('action', 'unknown'),
            'file': filepath.name,
            'status': 'executed'
        }
        
        log_file = self.logs_dir / f'approval_log_{datetime.now().strftime("%Y-%m-%d")}.json'
        
        # Append to log file
        import json
        logs = []
        if log_file.exists():
            try:
                logs = json.loads(log_file.read_text())
            except:
                pass
        
        logs.append(log_entry)
        log_file.write_text(json.dumps(logs, indent=2))
    
    def requires_approval(self, action_type: str, amount: float = 0) -> bool:
        """
        Check if an action requires approval.
        
        Args:
            action_type: Type of action
            amount: Amount involved (for payments)
            
        Returns:
            True if approval required
        """
        # Check action type
        if action_type in self.ALWAYS_REQUIRE_APPROVAL:
            return True
        
        # Check payment threshold
        if action_type == 'payment' and amount >= self.PAYMENT_THRESHOLD:
            return True
        
        return False
