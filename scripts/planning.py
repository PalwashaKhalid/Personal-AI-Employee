"""
Planning Module for AI Employee

Generates structured Plan.md files for tasks requiring multiple steps.
Used by the orchestrator to track task progress.
"""

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import re


class TaskPlan:
    """Represents a task plan with steps."""
    
    def __init__(self, title: str, objective: str, task_type: str = 'general'):
        self.title = title
        self.objective = objective
        self.task_type = task_type
        self.created = datetime.now()
        self.steps: List[Dict[str, Any]] = []
        self.status = 'pending'
        self.metadata: Dict[str, Any] = {}
    
    def add_step(self, description: str, action_type: str = 'task', 
                 requires_approval: bool = False) -> None:
        """Add a step to the plan."""
        self.steps.append({
            'description': description,
            'action_type': action_type,
            'requires_approval': requires_approval,
            'completed': False
        })
    
    def to_markdown(self) -> str:
        """Convert plan to Markdown format."""
        steps_markdown = ''
        for i, step in enumerate(self.steps, 1):
            checkbox = '[ ]'
            approval_tag = ' 🔒' if step['requires_approval'] else ''
            steps_markdown += f'- {checkbox} {step["description"]}{approval_tag}\n'
        
        metadata_yaml = ''
        for key, value in self.metadata.items():
            metadata_yaml += f'{key}: {value}\n'
        
        return f'''---
type: task_plan
created: {self.created.isoformat()}
status: {self.status}
task_type: {self.task_type}
{metadata_yaml}---

# Task Plan: {self.title}

## Objective

{self.objective}

---

## Steps

{steps_markdown}
---

## Notes

*Add notes and observations here*

---

## Completion Summary

*To be filled when task is complete*

---

*Created by AI Employee Orchestrator at {self.created.strftime("%Y-%m-%d %H:%M:%S")}*
'''


class PlanGenerator:
    """Generates task plans based on action file content."""
    
    # Common task patterns and their typical steps
    TASK_PATTERNS = {
        'email_reply': {
            'steps': [
                ('Read and understand email', 'read', False),
                ('Draft reply based on Company Handbook', 'draft', False),
                ('Review draft for tone and accuracy', 'review', False),
                ('Send email (requires approval)', 'send', True),
                ('Mark email as processed in Gmail', 'cleanup', False),
            ]
        },
        'whatsapp_reply': {
            'steps': [
                ('Read and understand message', 'read', False),
                ('Draft reply based on Company Handbook', 'draft', False),
                ('Review draft for tone and accuracy', 'review', False),
                ('Send message via WhatsApp (requires approval)', 'send', True),
            ]
        },
        'file_processing': {
            'steps': [
                ('Review file content', 'read', False),
                ('Categorize file type and purpose', 'categorize', False),
                ('Determine required action', 'decide', False),
                ('Execute action or create approval request', 'execute', False),
                ('Archive file appropriately', 'archive', False),
            ]
        },
        'payment': {
            'steps': [
                ('Verify payment details and amount', 'verify', False),
                ('Check against Company Handbook thresholds', 'verify', False),
                ('Create approval request file', 'approval', False),
                ('Wait for human approval', 'wait', False),
                ('Execute payment via MCP (after approval)', 'execute', True),
                ('Log transaction in Accounting', 'log', False),
            ]
        },
        'invoice_generation': {
            'steps': [
                ('Identify client and service details', 'gather', False),
                ('Calculate amount based on rates', 'calculate', False),
                ('Generate invoice PDF', 'create', False),
                ('Create email approval request', 'approval', False),
                ('Send invoice (after approval)', 'send', True),
                ('Log in Accounting folder', 'log', False),
            ]
        },
        'ceo_briefing': {
            'steps': [
                ('Review Business_Goals.md for targets', 'gather', False),
                ('Analyze completed tasks in Done folder', 'analyze', False),
                ('Review Accounting transactions', 'analyze', False),
                ('Calculate revenue and metrics', 'calculate', False),
                ('Identify bottlenecks and patterns', 'analyze', False),
                ('Generate briefing document', 'create', False),
                ('Update Dashboard with summary', 'update', False),
            ]
        }
    }
    
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.plans_dir = vault_path / 'Plans'
        self.plans_dir.mkdir(parents=True, exist_ok=True)
    
    def detect_task_type(self, action_file_path: Path) -> str:
        """Detect task type from action file name and content."""
        filename = action_file_path.name.lower()
        
        if filename.startswith('email_') or 'email' in filename:
            return 'email_reply'
        elif filename.startswith('whatsapp_') or 'whatsapp' in filename:
            return 'whatsapp_reply'
        elif filename.startswith('file_') or 'file_drop' in filename:
            return 'file_processing'
        elif 'payment' in filename or 'pay' in filename:
            return 'payment'
        elif 'invoice' in filename:
            return 'invoice_generation'
        elif 'briefing' in filename or 'audit' in filename:
            return 'ceo_briefing'
        
        # Try to detect from content
        try:
            content = action_file_path.read_text().lower()
            if 'type: email' in content:
                return 'email_reply'
            elif 'type: whatsapp' in content:
                return 'whatsapp_reply'
            elif 'type: file_drop' in content:
                return 'file_processing'
            elif 'type: payment' in content or 'payment' in content:
                return 'payment'
            elif 'type: approval' in content:
                return 'approval_required'
        except Exception:
            pass
        
        return 'general'
    
    def generate_plan(self, action_file_path: Path, 
                      custom_objective: Optional[str] = None) -> Optional[Path]:
        """
        Generate a task plan for an action file.
        
        Args:
            action_file_path: Path to the action file
            custom_objective: Optional custom objective text
            
        Returns:
            Path to created plan file
        """
        try:
            # Detect task type
            task_type = self.detect_task_type(action_file_path)
            
            # Create plan
            plan = TaskPlan(
                title=f'Process {action_file_path.stem}',
                objective=custom_objective or f'Process action file {action_file_path.name} according to Company Handbook rules',
                task_type=task_type
            )
            
            # Add steps based on pattern
            if task_type in self.TASK_PATTERNS:
                pattern = self.TASK_PATTERNS[task_type]
                for step_desc, step_type, requires_approval in pattern['steps']:
                    plan.add_step(step_desc, step_type, requires_approval)
            else:
                # Generic steps for unknown task types
                plan.add_step('Read and understand the task', 'read', False)
                plan.add_step('Determine required actions', 'analyze', False)
                plan.add_step('Execute actions or create approval requests', 'execute', False)
                plan.add_step('Move to Done when complete', 'cleanup', False)
            
            # Add metadata
            plan.metadata['source_file'] = action_file_path.name
            plan.metadata['source_path'] = str(action_file_path)
            
            # Save plan
            plan_filename = f'PLAN_{action_file_path.stem}_{datetime.now().strftime("%Y%m%d%H%M%S")}.md'
            plan_path = self.plans_dir / plan_filename
            plan_path.write_text(plan.to_markdown())
            
            return plan_path
            
        except Exception as e:
            print(f'Error generating plan: {e}')
            return None
    
    def generate_custom_plan(self, title: str, objective: str, 
                             steps: List[tuple]) -> Path:
        """
        Generate a custom plan with specified steps.
        
        Args:
            title: Plan title
            objective: Plan objective
            steps: List of (description, action_type, requires_approval) tuples
            
        Returns:
            Path to created plan file
        """
        plan = TaskPlan(title=title, objective=objective, task_type='custom')
        
        for step_desc, step_type, requires_approval in steps:
            plan.add_step(step_desc, step_type, requires_approval)
        
        plan_filename = f'PLAN_{self._sanitize_filename(title)}_{datetime.now().strftime("%Y%m%d%H%M%S")}.md'
        plan_path = self.plans_dir / plan_filename
        plan_path.write_text(plan.to_markdown())
        
        return plan_path
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize string for use in filename."""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename.strip().replace(' ', '_')[:50]
