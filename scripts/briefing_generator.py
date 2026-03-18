"""
CEO Briefing Generator

Generates weekly/daily CEO briefings by analyzing:
- Business goals and targets
- Completed tasks
- Financial transactions
- Pending items and bottlenecks

Usage:
    python briefing_generator.py ../Vault --output Monday_Briefing.md
"""

import argparse
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import logging


class CEOBriefingGenerator:
    """
    Generates CEO briefings from vault data.
    
    Analyzes completed work, revenue, bottlenecks, and provides
    proactive suggestions.
    """
    
    def __init__(self, vault_path: Path, logger: Optional[logging.Logger] = None):
        self.vault_path = vault_path
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        
        # Key folders
        self.done_folder = vault_path / 'Done'
        self.plans_folder = vault_path / 'Plans'
        self.needs_action = vault_path / 'Needs_Action'
        self.accounting = vault_path / 'Accounting'
        self.briefings = vault_path / 'Briefings'
        self.logs_dir = vault_path / 'Logs'
        
        # Key files
        self.business_goals = vault_path / 'Business_Goals.md'
        self.company_handbook = vault_path / 'Company_Handbook.md'
        self.dashboard = vault_path / 'Dashboard.md'
        
        # Ensure briefings folder exists
        self.briefings.mkdir(parents=True, exist_ok=True)
    
    def generate_briefing(self, period_days: int = 7, 
                          briefing_type: str = 'weekly') -> Optional[Path]:
        """
        Generate a CEO briefing.
        
        Args:
            period_days: Number of days to analyze
            briefing_type: Type of briefing (daily, weekly, monthly)
            
        Returns:
            Path to generated briefing file
        """
        self.logger.info(f'Generating {briefing_type} briefing for last {period_days} days')
        
        # Gather data
        completed_tasks = self._analyze_completed_tasks(period_days)
        revenue_data = self._analyze_revenue(period_days)
        bottlenecks = self._identify_bottlenecks(period_days)
        pending_items = self._count_pending_items()
        subscriptions = self._analyze_subscriptions(period_days)
        
        # Load business goals
        goals = self._load_business_goals()
        
        # Generate content
        briefing_date = datetime.now()
        period_start = briefing_date - timedelta(days=period_days)
        
        content = self._build_briefing_content(
            briefing_type=briefing_type,
            period_start=period_start,
            period_end=briefing_date,
            completed_tasks=completed_tasks,
            revenue_data=revenue_data,
            bottlenecks=bottlenecks,
            pending_items=pending_items,
            subscriptions=subscriptions,
            goals=goals
        )
        
        # Save briefing
        filename = f'{briefing_date.strftime("%Y-%m-%d")}_{briefing_type.title()}_Briefing.md'
        briefing_path = self.briefings / filename
        briefing_path.write_text(content)
        
        self.logger.info(f'Briefing saved to: {briefing_path}')
        
        # Update dashboard
        self._update_dashboard(briefing_path, revenue_data, completed_tasks)
        
        return briefing_path
    
    def _analyze_completed_tasks(self, days: int) -> Dict[str, Any]:
        """Analyze completed tasks from the Done folder."""
        completed = {
            'total': 0,
            'by_type': {},
            'files': [],
            'avg_completion_time': 'N/A'
        }
        
        if not self.done_folder.exists():
            return completed
        
        cutoff = datetime.now() - timedelta(days=days)
        
        for filepath in self.done_folder.iterdir():
            if filepath.suffix != '.md':
                continue
            
            try:
                # Check file modification time
                mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                if mtime < cutoff:
                    continue
                
                # Parse frontmatter
                content = filepath.read_text()
                task_type = 'general'
                
                if 'type:' in content:
                    for line in content.split('\n')[:20]:
                        if 'type:' in line:
                            task_type = line.split(':')[1].strip()
                            break
                
                completed['total'] += 1
                completed['by_type'][task_type] = completed['by_type'].get(task_type, 0) + 1
                completed['files'].append({
                    'name': filepath.name,
                    'type': task_type,
                    'completed': mtime.isoformat()
                })
                
            except Exception as e:
                self.logger.debug(f'Error analyzing file {filepath}: {e}')
        
        return completed
    
    def _analyze_revenue(self, days: int) -> Dict[str, Any]:
        """Analyze revenue from accounting folder."""
        revenue = {
            'total': 0.0,
            'transactions': [],
            'by_category': {},
            'expenses': 0.0,
            'net': 0.0
        }
        
        if not self.accounting.exists():
            return revenue
        
        cutoff = datetime.now() - timedelta(days=days)
        
        for filepath in self.accounting.iterdir():
            if filepath.suffix != '.md':
                continue
            
            try:
                content = filepath.read_text()
                
                # Look for amount in content
                amount = 0.0
                category = 'uncategorized'
                is_income = True
                
                for line in content.split('\n')[:30]:
                    line_lower = line.lower()
                    if 'amount:' in line_lower or 'total:' in line_lower:
                        try:
                            amount = float(line.split(':')[1].strip().replace('$', ''))
                        except:
                            pass
                    
                    if 'type:' in line_lower:
                        if 'expense' in line_lower or 'payment' in line_lower:
                            is_income = False
                        category = line.split(':')[1].strip()
                    
                    if 'category:' in line_lower:
                        category = line.split(':')[1].strip()
                
                if amount != 0:
                    if is_income:
                        revenue['total'] += amount
                    else:
                        revenue['expenses'] += amount
                    
                    revenue['by_category'][category] = revenue['by_category'].get(category, 0) + amount
                    
            except Exception as e:
                self.logger.debug(f'Error analyzing revenue file {filepath}: {e}')
        
        revenue['net'] = revenue['total'] - revenue['expenses']
        return revenue
    
    def _identify_bottlenecks(self, days: int) -> List[Dict[str, Any]]:
        """Identify bottlenecks from plans and pending items."""
        bottlenecks = []
        
        # Check for old pending items
        if self.needs_action.exists():
            cutoff = datetime.now() - timedelta(days=3)  # Items older than 3 days
            for filepath in self.needs_action.iterdir():
                try:
                    mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                    if mtime < cutoff:
                        bottlenecks.append({
                            'type': 'pending_item',
                            'item': filepath.name,
                            'age_days': (datetime.now() - mtime).days,
                            'suggestion': 'Review and process or delegate'
                        })
                except:
                    pass
        
        # Check for incomplete plans
        if self.plans_folder.exists():
            cutoff = datetime.now() - timedelta(days=7)
            for filepath in self.plans_folder.iterdir():
                try:
                    mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                    if mtime < cutoff:
                        content = filepath.read_text()
                        if '[ ]' in content and '[x]' not in content:
                            bottlenecks.append({
                                'type': 'stalled_plan',
                                'item': filepath.name,
                                'age_days': (datetime.now() - mtime).days,
                                'suggestion': 'Review plan progress and remove blockers'
                            })
                except:
                    pass
        
        return bottlenecks
    
    def _count_pending_items(self) -> Dict[str, int]:
        """Count pending items by status."""
        counts = {
            'needs_action': 0,
            'pending_approval': 0,
            'approved': 0,
            'in_progress': 0
        }
        
        if self.needs_action.exists():
            counts['needs_action'] = len([f for f in self.needs_action.iterdir() if f.suffix == '.md'])
        
        pending_approval = self.vault_path / 'Pending_Approval'
        if pending_approval.exists():
            counts['pending_approval'] = len([f for f in pending_approval.iterdir() if f.suffix == '.md'])
        
        approved = self.vault_path / 'Approved'
        if approved.exists():
            counts['approved'] = len([f for f in approved.iterdir() if f.suffix == '.md'])
        
        return counts
    
    def _analyze_subscriptions(self, days: int) -> List[Dict[str, Any]]:
        """Analyze subscription spending."""
        subscriptions = []
        
        # This would integrate with accounting data
        # For now, return placeholder
        return subscriptions
    
    def _load_business_goals(self) -> Dict[str, Any]:
        """Load business goals from file."""
        goals = {
            'revenue_target': 0,
            'current_revenue': 0,
            'metrics': {}
        }
        
        if not self.business_goals.exists():
            return goals
        
        try:
            content = self.business_goals.read_text()
            
            # Parse goals (simplified parsing)
            if 'Monthly goal:' in content:
                for line in content.split('\n'):
                    if 'Monthly goal:' in line:
                        try:
                            goals['revenue_target'] = float(line.split('$')[1].replace(',', ''))
                        except:
                            pass
                            
        except Exception as e:
            self.logger.debug(f'Error loading business goals: {e}')
        
        return goals
    
    def _build_briefing_content(self, **kwargs) -> str:
        """Build the briefing Markdown content."""
        period_start = kwargs['period_start'].strftime('%Y-%m-%d')
        period_end = kwargs['period_end'].strftime('%Y-%m-%d')
        briefing_type = kwargs['briefing_type']
        
        completed = kwargs['completed_tasks']
        revenue = kwargs['revenue_data']
        bottlenecks = kwargs['bottlenecks']
        pending = kwargs['pending_items']
        goals = kwargs['goals']
        
        # Executive summary
        summary = self._generate_executive_summary(completed, revenue, bottlenecks, goals)
        
        # Completed tasks section
        completed_section = ''
        if completed['total'] > 0:
            completed_section = f'''
## Completed Tasks

**Total:** {completed['total']} tasks

'''
            if completed['by_type']:
                completed_section += '| Type | Count |\n|------|-------|\n'
                for task_type, count in completed['by_type'].items():
                    completed_section += f'| {task_type.replace("_", " ").title()} | {count} |\n'
            completed_section += '\n'
        else:
            completed_section = '\n## Completed Tasks\n\n*No tasks completed this period*\n\n'
        
        # Revenue section
        revenue_section = f'''
## Revenue

| Metric | Amount |
|--------|--------|
| Total Revenue | ${revenue["total"]:.2f} |
| Expenses | ${revenue["expenses"]:.2f} |
| **Net** | **${revenue["net"]:.2f}** |

'''
        
        # Goals progress
        if goals['revenue_target'] > 0:
            progress = (revenue['total'] / goals['revenue_target']) * 100
            revenue_section += f'''
### Goals Progress
- **Monthly Target:** ${goals["revenue_target"]:,.2f}
- **Current:** ${revenue["total"]:,.2f}
- **Progress:** {progress:.1f}%

'''
        
        # Bottlenecks section
        bottlenecks_section = '\n## Bottlenecks\n\n'
        if bottlenecks:
            bottlenecks_section += '| Item | Type | Age | Suggestion |\n|------|------|-----|------------|\n'
            for b in bottlenecks[:5]:  # Top 5
                bottlenecks_section += f'| {b["item"][:30]} | {b["type"]} | {b["age_days"]} days | {b["suggestion"][:30]} |\n'
        else:
            bottlenecks_section += '*No bottlenecks identified*\n'
        
        # Pending items
        pending_section = f'''
## Pending Items

| Status | Count |
|--------|-------|
| Needs Action | {pending.get('needs_action', 0)} |
| Pending Approval | {pending.get('pending_approval', 0)} |
| Approved (Ready) | {pending.get('approved', 0)} |

'''
        
        # Proactive suggestions
        suggestions = self._generate_suggestions(completed, revenue, bottlenecks, pending, goals)
        suggestions_section = '\n## Proactive Suggestions\n\n'
        if suggestions:
            for i, suggestion in enumerate(suggestions, 1):
                suggestions_section += f'{i}. {suggestion}\n'
        else:
            suggestions_section += '*No suggestions at this time*\n'
        
        return f'''---
generated: {kwargs["period_end"].isoformat()}
period: {period_start} to {period_end}
type: {briefing_type}_briefing
---

# {briefing_type.title()} Morning CEO Briefing

**Generated:** {kwargs["period_end"].strftime("%Y-%m-%d %H:%M")}

**Period:** {period_start} to {period_end}

---

{summary}
{revenue_section}
{completed_section}
{bottlenecks_section}
{pending_section}
{suggestions_section}
---

## Upcoming Deadlines

*Deadlines will be listed here based on task analysis*

---

*Generated by AI Employee v0.2 (Silver Tier)*
'''
    
    def _generate_executive_summary(self, completed: Dict, revenue: Dict, 
                                    bottlenecks: List, goals: Dict) -> str:
        """Generate executive summary."""
        summary_parts = []
        
        # Revenue status
        if goals['revenue_target'] > 0:
            progress = (revenue['total'] / goals['revenue_target']) * 100
            if progress >= 80:
                summary_parts.append('Revenue is on track.')
            elif progress >= 50:
                summary_parts.append('Revenue progress is moderate.')
            else:
                summary_parts.append('Revenue needs attention.')
        else:
            summary_parts.append('Revenue tracking not configured.')
        
        # Task completion
        if completed['total'] > 0:
            summary_parts.append(f'{completed["total"]} tasks completed.')
        else:
            summary_parts.append('No tasks completed this period.')
        
        # Bottlenecks
        if bottlenecks:
            summary_parts.append(f'{len(bottlenecks)} bottleneck(s) identified.')
        
        return f'## Executive Summary\n\n{" ".join(summary_parts)}\n\n'
    
    def _generate_suggestions(self, completed: Dict, revenue: Dict, 
                              bottlenecks: List, pending: Dict, goals: Dict) -> List[str]:
        """Generate proactive suggestions."""
        suggestions = []
        
        # Revenue suggestions
        if goals['revenue_target'] > 0:
            progress = (revenue['total'] / goals['revenue_target']) * 100
            if progress < 50:
                suggestions.append('Consider reaching out to pending clients to boost revenue.')
        
        # Bottleneck suggestions
        if bottlenecks:
            suggestions.append(f'Review {len(bottlenecks)} stalled item(s) to remove blockers.')
        
        # Pending approval suggestions
        if pending.get('pending_approval', 0) > 0:
            suggestions.append(f'{pending["pending_approval"]} item(s) awaiting your approval.')
        
        # Task suggestions
        if completed['total'] == 0:
            suggestions.append('Start by processing items in Needs_Action folder.')
        
        return suggestions
    
    def _update_dashboard(self, briefing_path: Path, revenue: Dict, 
                          completed: Dict) -> None:
        """Update dashboard with briefing summary."""
        if not self.dashboard.exists():
            return
        
        try:
            content = self.dashboard.read_text()
            
            # Update revenue
            if '| Bank Balance |' in content:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if '| Bank Balance |' in line:
                        lines[i] = f'| Bank Balance | ${revenue["net"]:.2f} | {"✅ Positive" if revenue["net"] >= 0 else "⚠️ Negative"} |'
                content = '\n'.join(lines)
            
            self.dashboard.write_text(content)
            
        except Exception as e:
            self.logger.debug(f'Error updating dashboard: {e}')


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='CEO Briefing Generator')
    parser.add_argument('vault_path', type=str, help='Path to Obsidian vault')
    parser.add_argument('--type', type=str, default='weekly',
                        choices=['daily', 'weekly', 'monthly'],
                        help='Type of briefing')
    parser.add_argument('--days', type=int, default=7,
                        help='Number of days to analyze')
    parser.add_argument('--output', type=str, default=None,
                        help='Output filename (optional)')
    
    args = parser.parse_args()
    
    vault = Path(args.vault_path)
    generator = CEOBriefingGenerator(vault)
    
    days = args.days
    if args.type == 'daily':
        days = 1
    elif args.type == 'monthly':
        days = 30
    
    briefing_path = generator.generate_briefing(period_days=days, briefing_type=args.type)
    
    if briefing_path:
        print(f'Briefing generated: {briefing_path}')
    else:
        print('Failed to generate briefing')


if __name__ == '__main__':
    main()
