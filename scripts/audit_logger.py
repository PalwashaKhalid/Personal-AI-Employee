"""
Comprehensive Audit Logging System

Provides detailed, searchable audit trails for all AI Employee actions.
Gold tier requirement for compliance and debugging.

Features:
- JSON structured logging
- Searchable audit trail
- Daily log rotation
- Compliance-ready format
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import hashlib


@dataclass
class AuditEntry:
    """Represents a single audit log entry."""
    timestamp: str
    event_id: str
    actor: str
    action_type: str
    target: str
    status: str
    details: Dict[str, Any]
    approval_status: str = 'not_required'
    approved_by: str = ''
    error_message: str = ''
    session_id: str = ''
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AuditLogger:
    """
    Comprehensive audit logging system.
    
    Logs all actions in structured JSON format for compliance and debugging.
    """
    
    def __init__(self, vault_path: Path, session_id: str = ''):
        self.vault_path = vault_path
        self.logs_dir = vault_path / 'Logs' / 'Audit'
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        self.session_id = session_id or datetime.now().strftime('%Y%m%d_%H%M%S')
        self.actor = 'ai_employee'
        
        # Set up logging
        self._setup_logging()
        
    def _setup_logging(self) -> None:
        """Configure structured JSON logging."""
        log_file = self.logs_dir / f'audit_{datetime.now().strftime("%Y-%m-%d")}.json'
        
        # Create custom handler
        self.audit_handler = logging.FileHandler(log_file)
        self.audit_handler.setFormatter(logging.Formatter('%(message)s'))
        
        self.audit_logger = logging.getLogger('audit')
        self.audit_logger.setLevel(logging.INFO)
        self.audit_logger.addHandler(self.audit_handler)
    
    def _generate_event_id(self, data: str) -> str:
        """Generate unique event ID."""
        timestamp = datetime.now().isoformat()
        unique_str = f'{timestamp}:{data}'
        return hashlib.sha256(unique_str.encode()).hexdigest()[:16]
    
    def log_action(self, action_type: str, target: str, status: str,
                   details: Optional[Dict[str, Any]] = None,
                   approval_status: str = 'not_required',
                   approved_by: str = '',
                   error_message: str = '') -> AuditEntry:
        """
        Log an action to the audit trail.
        
        Args:
            action_type: Type of action (email_send, file_process, etc.)
            target: Target of the action (email address, file path, etc.)
            status: Action status (success, failed, pending)
            details: Additional details dictionary
            approval_status: Approval status (not_required, pending, approved, rejected)
            approved_by: Who approved the action (if applicable)
            error_message: Error message if failed
            
        Returns:
            AuditEntry object
        """
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            event_id=self._generate_event_id(f'{action_type}:{target}'),
            actor=self.actor,
            action_type=action_type,
            target=target,
            status=status,
            details=details or {},
            approval_status=approval_status,
            approved_by=approved_by,
            error_message=error_message,
            session_id=self.session_id
        )
        
        # Log as JSON
        self.audit_logger.info(json.dumps(entry.to_dict(), indent=None))
        
        return entry
    
    def log_email_send(self, to: str, subject: str, status: str,
                       message_id: str = '', error: str = '') -> AuditEntry:
        """Log email send action."""
        return self.log_action(
            action_type='email_send',
            target=to,
            status=status,
            details={
                'to': to,
                'subject': subject,
                'message_id': message_id
            },
            error_message=error
        )
    
    def log_whatsapp_send(self, contact: str, message: str, status: str,
                          error: str = '') -> AuditEntry:
        """Log WhatsApp message action."""
        return self.log_action(
            action_type='whatsapp_send',
            target=contact,
            status=status,
            details={
                'contact': contact,
                'message_preview': message[:100]
            },
            error_message=error
        )
    
    def log_linkedin_post(self, content: str, status: str,
                          post_id: str = '', error: str = '') -> AuditEntry:
        """Log LinkedIn post action."""
        return self.log_action(
            action_type='linkedin_post',
            target='linkedin.com',
            status=status,
            details={
                'content_preview': content[:100],
                'post_id': post_id
            },
            error_message=error
        )
    
    def log_payment(self, amount: float, recipient: str, status: str,
                    approval_status: str = 'pending',
                    approved_by: str = '',
                    error: str = '') -> AuditEntry:
        """Log payment action."""
        return self.log_action(
            action_type='payment',
            target=recipient,
            status=status,
            details={
                'amount': amount,
                'recipient': recipient,
                'currency': 'USD'
            },
            approval_status=approval_status,
            approved_by=approved_by,
            error_message=error
        )
    
    def log_file_process(self, filename: str, action: str, status: str,
                         error: str = '') -> AuditEntry:
        """Log file processing action."""
        return self.log_action(
            action_type='file_process',
            target=filename,
            status=status,
            details={
                'filename': filename,
                'action': action
            },
            error_message=error
        )
    
    def log_task_plan(self, task_name: str, plan_id: str, status: str) -> AuditEntry:
        """Log task planning action."""
        return self.log_action(
            action_type='task_plan',
            target=task_name,
            status=status,
            details={
                'task_name': task_name,
                'plan_id': plan_id
            }
        )
    
    def log_approval_request(self, action_type: str, target: str,
                             approval_status: str,
                             approved_by: str = '') -> AuditEntry:
        """Log approval request action."""
        return self.log_action(
            action_type='approval_request',
            target=target,
            status='logged',
            details={'request_type': action_type},
            approval_status=approval_status,
            approved_by=approved_by
        )
    
    def log_error(self, error_type: str, target: str, error_message: str,
                  details: Optional[Dict[str, Any]] = None) -> AuditEntry:
        """Log error event."""
        return self.log_action(
            action_type=f'error_{error_type}',
            target=target,
            status='error',
            details=details or {},
            error_message=error_message
        )
    
    def search_logs(self, query: Dict[str, Any], 
                    date_from: Optional[datetime] = None,
                    date_to: Optional[datetime] = None) -> List[AuditEntry]:
        """
        Search audit logs by criteria.
        
        Args:
            query: Search criteria (action_type, actor, status, etc.)
            date_from: Start date
            date_to: End date
            
        Returns:
            List of matching AuditEntry objects
        """
        results = []
        
        # Determine which log files to search
        if date_from:
            start_date = date_from.strftime('%Y-%m-%d')
        else:
            start_date = datetime.now().strftime('%Y-%m-%d')
        
        if date_to:
            end_date = date_to.strftime('%Y-%m-%d')
        else:
            end_date = start_date
        
        # Search log files
        log_files = sorted(self.logs_dir.glob('audit_*.json'))
        
        for log_file in log_files:
            file_date = log_file.stem.split('_')[1]
            if start_date <= file_date <= end_date:
                try:
                    content = log_file.read_text()
                    for line in content.strip().split('\n'):
                        if line.strip():
                            entry_dict = json.loads(line)
                            
                            # Check if entry matches query
                            matches = True
                            for key, value in query.items():
                                if entry_dict.get(key) != value:
                                    matches = False
                                    break
                            
                            if matches:
                                results.append(AuditEntry(**entry_dict))
                                
                except Exception as e:
                    print(f'Error reading log file {log_file}: {e}')
        
        return results
    
    def get_daily_summary(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get summary of actions for a specific date.
        
        Args:
            date: Date to summarize (default: today)
            
        Returns:
            Summary dictionary
        """
        if date is None:
            date = datetime.now()
        
        entries = self.search_logs({}, date_from=date, date_to=date)
        
        summary = {
            'date': date.strftime('%Y-%m-%d'),
            'total_actions': len(entries),
            'by_action_type': {},
            'by_status': {},
            'errors': [],
            'approvals_pending': 0,
            'approvals_approved': 0,
            'approvals_rejected': 0
        }
        
        for entry in entries:
            # Count by action type
            action = entry.action_type
            summary['by_action_type'][action] = summary['by_action_type'].get(action, 0) + 1
            
            # Count by status
            status = entry.status
            summary['by_status'][status] = summary['by_status'].get(status, 0) + 1
            
            # Track errors
            if entry.status == 'error':
                summary['errors'].append({
                    'action': entry.action_type,
                    'target': entry.target,
                    'error': entry.error_message
                })
            
            # Track approvals
            if entry.approval_status == 'pending':
                summary['approvals_pending'] += 1
            elif entry.approval_status == 'approved':
                summary['approvals_approved'] += 1
            elif entry.approval_status == 'rejected':
                summary['approvals_rejected'] += 1
        
        return summary
    
    def export_logs(self, output_path: Path, 
                    date_from: Optional[datetime] = None,
                    date_to: Optional[datetime] = None) -> bool:
        """
        Export logs to a file for compliance/archival.
        
        Args:
            output_path: Output file path
            date_from: Start date
            date_to: End date
            
        Returns:
            True if successful
        """
        try:
            entries = self.search_logs({}, date_from=date_from, date_to=date_to)
            
            export_data = {
                'export_date': datetime.now().isoformat(),
                'date_range': {
                    'from': date_from.isoformat() if date_from else 'all',
                    'to': date_to.isoformat() if date_to else 'all'
                },
                'total_entries': len(entries),
                'entries': [e.to_dict() for e in entries]
            }
            
            output_path.write_text(json.dumps(export_data, indent=2))
            return True
            
        except Exception as e:
            print(f'Error exporting logs: {e}')
            return False


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger(vault_path: Optional[Path] = None, 
                     session_id: str = '') -> AuditLogger:
    """Get or create global audit logger instance."""
    global _audit_logger
    
    if _audit_logger is None and vault_path:
        _audit_logger = AuditLogger(vault_path, session_id)
    elif _audit_logger is None:
        raise ValueError("Vault path required for first audit logger creation")
    
    return _audit_logger
