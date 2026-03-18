"""
Orchestrator Module - Silver Tier

Main orchestration script that:
1. Monitors the Needs_Action folder for pending items
2. Triggers Qwen Code to process items
3. Generates task plans for multi-step tasks
4. Manages Human-in-the-Loop approval workflow
5. Executes approved actions
6. Generates CEO briefings on schedule

Usage:
    python orchestrator.py /path/to/vault

Silver Tier Features:
- Plan generation for tasks
- HITL approval workflow
- Briefing generation
- Multiple watcher support
"""

import argparse
import subprocess
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging
import time
import json

from planning import PlanGenerator
from approval_workflow import ApprovalManager


class Orchestrator:
    """
    Orchestrates the AI Employee workflow.
    
    Monitors folders, triggers Qwen Code, and manages task lifecycle.
    """
    
    def __init__(self, vault_path: str, check_interval: int = 60):
        """
        Initialize the orchestrator.
        
        Args:
            vault_path: Path to the Obsidian vault root
            check_interval: Seconds between checks (default: 60)
        """
        self.vault_path = Path(vault_path)
        self.check_interval = check_interval
        
        # Define folders
        self.needs_action = self.vault_path / 'Needs_Action'
        self.plans = self.vault_path / 'Plans'
        self.done = self.vault_path / 'Done'
        self.pending_approval = self.vault_path / 'Pending_Approval'
        self.approved = self.vault_path / 'Approved'
        self.rejected = self.vault_path / 'Rejected'
        self.logs_dir = self.vault_path / 'Logs'
        self.briefings = self.vault_path / 'Briefings'
        self.dashboard = self.vault_path / 'Dashboard.md'
        
        # Ensure directories exist
        for folder in [self.needs_action, self.plans, self.done,
                       self.pending_approval, self.approved, self.rejected, 
                       self.logs_dir, self.briefings]:
            folder.mkdir(parents=True, exist_ok=True)
        
        # Set up logging
        self._setup_logging()
        
        # Initialize components
        self.plan_generator = PlanGenerator(self.vault_path)
        self.approval_manager = ApprovalManager(self.vault_path, self.logger)
        
        # Track processed files
        self.processed_files: set = set()
        
        # Briefing schedule
        self.last_briefing = None
        self.briefing_interval = timedelta(days=1)  # Daily briefing
        
        self.logger.info(f'Orchestrator initialized (Silver Tier)')
        self.logger.info(f'Vault path: {self.vault_path}')
    
    def _setup_logging(self) -> None:
        """Configure logging."""
        log_file = self.logs_dir / f'Orchestrator_{datetime.now().strftime("%Y-%m-%d")}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('Orchestrator')
    
    def get_pending_items(self) -> List[Path]:
        """Get list of pending action files."""
        if not self.needs_action.exists():
            return []
        
        pending = []
        for filepath in self.needs_action.iterdir():
            if filepath.suffix == '.md' and filepath not in self.processed_files:
                pending.append(filepath)
        
        return sorted(pending, key=lambda x: x.stat().st_mtime)
    
    def get_approved_items(self) -> List[Path]:
        """Get list of approved action files ready for execution."""
        if not self.approved.exists():
            return []
        
        return [f for f in self.approved.iterdir() if f.suffix == '.md']
    
    def trigger_qwen(self, prompt: str, plan_path: Optional[Path] = None) -> bool:
        """
        Trigger Qwen Code to process items.
        
        Args:
            prompt: Prompt to give Qwen Code
            plan_path: Optional path to plan file
            
        Returns:
            True if Qwen was triggered successfully
        """
        self.logger.info('Triggering Qwen Code...')
        
        try:
            # Check if qwen command is available
            result = subprocess.run(
                ['qwen', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                self.logger.error('Qwen Code not found or not responding')
                self.logger.info('Ensure Qwen Code is installed and in PATH')
                return False
            
            self.logger.info(f'Qwen Code available: {result.stdout.strip()}')
            self.logger.info(f'Prompt: {prompt[:100]}...')
            
            # Create a state file for Qwen to process
            state_file = self.plans / f'ORCHESTRATOR_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
            plan_ref = f'\n**Related Plan:** [[{plan_path.name}]]' if plan_path else ''
            
            state_content = f'''---
type: orchestrator_prompt
created: {datetime.now().isoformat()}
status: pending
---

# Qwen Code Task

## Instructions

{prompt}

## Files to Process

*Qwen Code should check /Needs_Action folder and process pending items*
{plan_ref}

## Completion Criteria

- [ ] All pending items reviewed
- [ ] Task plans created/updated
- [ ] Approval requests created for sensitive actions
- [ ] Dashboard updated
- [ ] Files moved to /Done when complete

---

*Created by Orchestrator at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
'''
            state_file.write_text(state_content)
            self.logger.info(f'Created state file: {state_file}')
            
            return True
            
        except FileNotFoundError:
            self.logger.error('Qwen Code not installed')
            return False
        except subprocess.TimeoutExpired:
            self.logger.error('Qwen Code version check timed out')
            return False
        except Exception as e:
            self.logger.error(f'Error triggering Qwen Code: {e}', exc_info=True)
            return False
    
    def process_pending_items(self) -> Dict[str, int]:
        """
        Process pending items with plan generation.
        
        Returns:
            Dict with processing results
        """
        pending = self.get_pending_items()
        results = {'processed': 0, 'plans_created': 0, 'approvals_created': 0}
        
        if not pending:
            return results
        
        self.logger.info(f'Found {len(pending)} pending item(s)')
        
        for filepath in pending:
            try:
                # Generate plan for this item
                plan_path = self.plan_generator.generate_plan(filepath)
                if plan_path:
                    results['plans_created'] += 1
                    self.logger.info(f'Created plan: {plan_path.name}')
                
                # Check if this requires approval
                content = filepath.read_text()
                if self._requires_approval(content):
                    approval_path = self._create_approval_from_file(filepath)
                    if approval_path:
                        results['approvals_created'] += 1
                        self.logger.info(f'Created approval request: {approval_path.name}')
                        # Move to pending approval
                        dest = self.pending_approval / filepath.name
                        shutil.move(str(filepath), str(dest))
                        self.processed_files.add(filepath)
                        continue
                
                results['processed'] += 1
                
            except Exception as e:
                self.logger.error(f'Error processing {filepath.name}: {e}', exc_info=True)
        
        # Trigger Qwen to process
        if pending:
            prompt = f'''Process {len(pending)} pending item(s) in /Needs_Action folder.

For each item:
1. Read the action file and understand the task
2. Review Company_Handbook.md for rules and guidelines
3. Check if a plan exists in /Plans folder
4. Execute the task or create approval requests for sensitive actions
5. Update Dashboard.md with progress
6. Move completed items to /Done

Files to process:
{chr(10).join(f'- {p.name}' for p in pending)}

Remember:
- Payments over $500 require approval
- All emails need approval before sending
- WhatsApp messages need approval before sending
- Log all actions taken
'''
            self.trigger_qwen(prompt, plan_path)
        
        return results
    
    def _requires_approval(self, content: str) -> bool:
        """Check if content requires approval."""
        content_lower = content.lower()
        
        # Check for payment
        if 'type: payment' in content_lower:
            return True
        
        # Check for email send
        if 'type: email' in content_lower and 'send' in content_lower:
            return True
        
        # Check for large amounts
        if 'amount:' in content_lower:
            try:
                for line in content_lower.split('\n'):
                    if 'amount:' in line:
                        amount = float(line.split(':')[1].strip().replace('$', ''))
                        if amount >= 500:
                            return True
            except:
                pass
        
        return False
    
    def _create_approval_from_file(self, filepath: Path) -> Optional[Path]:
        """Create approval request from action file."""
        try:
            content = filepath.read_text()
            
            # Parse frontmatter
            details = {}
            action_type = 'general'
            
            if '---' in content:
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter = parts[1].strip()
                    for line in frontmatter.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            details[key.strip()] = value.strip()
            
            action_type = details.get('type', 'general')
            
            # Create approval request
            approval_path = self.approval_manager.create_approval_request(
                action_type=action_type,
                details=details,
                reason=f'Action requires approval per Company Handbook'
            )
            
            return approval_path
            
        except Exception as e:
            self.logger.error(f'Error creating approval: {e}', exc_info=True)
            return None
    
    def process_approved_items(self) -> int:
        """Process items in the Approved folder."""
        approved_items = self.get_approved_items()
        
        if not approved_items:
            return 0
        
        self.logger.info(f'Found {len(approved_items)} approved item(s)')
        
        for item in approved_items:
            try:
                self.logger.info(f'Processing approved item: {item.name}')
                
                # Execute the action
                success = self.approval_manager.execute_approved_action(item)
                
                if success:
                    self.update_dashboard(f'Approved action completed: {item.stem}')
                
            except Exception as e:
                self.logger.error(f'Error processing approved item: {e}', exc_info=True)
        
        return len(approved_items)
    
    def generate_briefing(self) -> Optional[Path]:
        """Generate CEO briefing if due."""
        # Check if briefing is due
        if self.last_briefing:
            if datetime.now() - self.last_briefing < self.briefing_interval:
                return None
        
        try:
            from briefing_generator import CEOBriefingGenerator
            
            generator = CEOBriefingGenerator(self.vault_path, self.logger)
            briefing_path = generator.generate_briefing(period_days=1, briefing_type='daily')
            
            if briefing_path:
                self.last_briefing = datetime.now()
                self.logger.info(f'Briefing generated: {briefing_path}')
                return briefing_path
            
        except ImportError:
            self.logger.debug('Briefing generator not available')
        except Exception as e:
            self.logger.error(f'Error generating briefing: {e}', exc_info=True)
        
        return None
    
    def update_dashboard(self, message: str) -> None:
        """Update Dashboard.md with new activity."""
        if not self.dashboard.exists():
            self.logger.warning('Dashboard.md not found')
            return
        
        try:
            content = self.dashboard.read_text()
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            activity_line = f'- [{timestamp}] {message}'
            
            # Find Recent Activity section
            if '## ✅ Recent Activity' in content:
                lines = content.split('\n')
                new_lines = []
                skip_next_empty = False
                
                for i, line in enumerate(lines):
                    if line == '## ✅ Recent Activity':
                        new_lines.append(line)
                        new_lines.append('')
                        new_lines.append(activity_line)
                        skip_next_empty = True
                    elif skip_next_empty and line.strip() == '':
                        skip_next_empty = False
                        if i + 1 < len(lines) and '*No recent activity*' in lines[i + 1]:
                            continue
                        new_lines.append(line)
                    elif '*No recent activity*' in line:
                        continue
                    else:
                        new_lines.append(line)
                
                content = '\n'.join(new_lines)
            
            self.dashboard.write_text(content)
            self.logger.debug('Dashboard updated')
            
        except Exception as e:
            self.logger.error(f'Could not update dashboard: {e}')
    
    def update_dashboard_counts(self) -> None:
        """Update the counts in Dashboard.md quick status."""
        if not self.dashboard.exists():
            return
        
        try:
            pending_count = len(self.get_pending_items())
            approval_count = len(self.approval_manager.get_pending_requests())
            approved_count = len(self.get_approved_items())
            
            content = self.dashboard.read_text()
            
            # Update counts
            if '| Pending Actions |' in content:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if '| Pending Actions |' in line:
                        status = '✅ Clear' if pending_count == 0 else f'⚠️ {pending_count} pending'
                        lines[i] = f'| Pending Actions | {pending_count} | {status} |'
                    elif '| Awaiting Approval |' in line:
                        status = '✅ Clear' if approval_count == 0 else f'⚠️ {approval_count} awaiting'
                        lines[i] = f'| Awaiting Approval | {approval_count} | {status} |'
                
                content = '\n'.join(lines)
                self.dashboard.write_text(content)
                
        except Exception as e:
            self.logger.error(f'Could not update dashboard counts: {e}')
    
    def run_once(self) -> Dict[str, Any]:
        """Run one orchestration cycle."""
        results = {
            'pending_processed': 0,
            'plans_created': 0,
            'approvals_created': 0,
            'approved_executed': 0,
            'briefing_generated': False
        }
        
        # Process pending items
        pending_results = self.process_pending_items()
        results['pending_processed'] = pending_results.get('processed', 0)
        results['plans_created'] = pending_results.get('plans_created', 0)
        results['approvals_created'] = pending_results.get('approvals_created', 0)
        
        # Process approved items
        results['approved_executed'] = self.process_approved_items()
        
        # Generate briefing if due
        briefing = self.generate_briefing()
        results['briefing_generated'] = briefing is not None
        
        # Update dashboard counts
        self.update_dashboard_counts()
        
        return results
    
    def run(self) -> None:
        """Main run loop."""
        self.logger.info('Starting Orchestrator (Silver Tier)')
        self.logger.info(f'Check interval: {self.check_interval}s')
        
        try:
            while True:
                try:
                    results = self.run_once()
                    
                    if any(v and v != 0 for v in results.values()):
                        self.logger.info(f'Cycle complete: {results}')
                    else:
                        self.logger.debug(f'Cycle complete: No items to process')
                    
                except Exception as e:
                    self.logger.error(f'Error in orchestration cycle: {e}', exc_info=True)
                
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            self.logger.info('Orchestrator stopped by user')
        except Exception as e:
            self.logger.error(f'Fatal error: {e}', exc_info=True)
            raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='AI Employee Orchestrator (Silver Tier)')
    parser.add_argument('vault_path', type=str, help='Path to Obsidian vault')
    parser.add_argument('--interval', type=int, default=60,
                        help='Check interval in seconds (default: 60)')
    parser.add_argument('--once', action='store_true',
                        help='Run once and exit')
    
    args = parser.parse_args()
    
    orchestrator = Orchestrator(
        vault_path=args.vault_path,
        check_interval=args.interval
    )
    
    if args.once:
        results = orchestrator.run_once()
        print(f'Orchestration cycle complete: {results}')
    else:
        orchestrator.run()


if __name__ == '__main__':
    main()
