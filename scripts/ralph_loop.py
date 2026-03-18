"""
Ralph Wiggum Loop - Autonomous Multi-Step Task Completion

Implements the "Ralph Wiggum" pattern: a Stop hook that intercepts 
task completion and re-injects prompts until tasks are fully complete.

Gold tier requirement for autonomous operation.

Usage:
    python ralph_loop.py ../Vault "Process all pending items"
"""

import argparse
import subprocess
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging


class RalphLoop:
    """
    Ralph Wiggum Loop for autonomous task completion.
    
    Keeps Qwen Code iterating until tasks are complete.
    """
    
    def __init__(self, vault_path: Path, max_iterations: int = 10,
                 completion_signal: str = 'TASK_COMPLETE'):
        self.vault_path = vault_path
        self.max_iterations = max_iterations
        self.completion_signal = completion_signal
        
        self.logs_dir = vault_path / 'Logs'
        self.plans_dir = vault_path / 'Plans'
        self.done_dir = vault_path / 'Done'
        self.needs_action_dir = vault_path / 'Needs_Action'
        
        # State file
        self.state_file = self.logs_dir / 'ralph_loop_state.json'
        
        # Set up logging
        self._setup_logging()
        
        # Load state
        self._load_state()
    
    def _setup_logging(self) -> None:
        """Configure logging."""
        log_file = self.logs_dir / f'ralph_loop_{datetime.now().strftime("%Y-%m-%d")}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('RalphLoop')
    
    def _load_state(self) -> None:
        """Load loop state from file."""
        if self.state_file.exists():
            try:
                self.state = json.loads(self.state_file.read_text())
            except:
                self.state = {}
        else:
            self.state = {}
    
    def _save_state(self) -> None:
        """Save loop state to file."""
        self.state_file.write_text(json.dumps(self.state, indent=2))
    
    def check_completion_file_based(self) -> bool:
        """
        Check if task is complete based on file movement.
        
        Task is complete when:
        - Needs_Action folder is empty, OR
        - All items have been moved to Done
        
        Returns:
            True if complete
        """
        # Check if Needs_Action is empty
        if self.needs_action_dir.exists():
            pending = list(self.needs_action_dir.glob('*.md'))
            if pending:
                self.logger.info(f'{len(pending)} items still in Needs_Action')
                return False
        
        self.logger.info('Needs_Action folder is empty - task complete')
        return True
    
    def check_completion_promise_based(self, output: str) -> bool:
        """
        Check if task is complete based on output promise.
        
        Looks for completion signal in output.
        
        Args:
            output: Qwen Code output
            
        Returns:
            True if complete
        """
        return self.completion_signal in output
    
    def run(self, prompt: str, completion_mode: str = 'file') -> bool:
        """
        Run Ralph Wiggum loop.
        
        Args:
            prompt: Initial prompt for Qwen Code
            completion_mode: 'file' or 'promise'
            
        Returns:
            True if task completed successfully
        """
        self.logger.info(f'Starting Ralph Wiggum Loop')
        self.logger.info(f'Prompt: {prompt[:100]}...')
        self.logger.info(f'Max iterations: {self.max_iterations}')
        self.logger.info(f'Completion mode: {completion_mode}')
        
        iteration = 0
        current_prompt = prompt
        last_output = ''
        
        while iteration < self.max_iterations:
            iteration += 1
            self.logger.info(f'=== Iteration {iteration}/{self.max_iterations} ===')
            
            # Save state
            self.state = {
                'iteration': iteration,
                'started': datetime.now().isoformat(),
                'prompt': prompt,
                'status': 'in_progress'
            }
            self._save_state()
            
            # Run Qwen Code
            try:
                result = subprocess.run(
                    ['qwen', current_prompt],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout per iteration
                )
                
                output = result.stdout + result.stderr
                last_output = output
                
                self.logger.info(f'Qwen exit code: {result.returncode}')
                
            except subprocess.TimeoutExpired:
                self.logger.error('Qwen Code timed out')
                output = 'ERROR: Timeout'
            except FileNotFoundError:
                self.logger.error('Qwen Code not found')
                return False
            except Exception as e:
                self.logger.error(f'Error running Qwen: {e}')
                output = f'ERROR: {e}'
            
            # Check completion
            if completion_mode == 'file':
                if self.check_completion_file_based():
                    self.logger.info('Task complete (file-based check)')
                    self._finalize(True, iteration)
                    return True
            elif completion_mode == 'promise':
                if self.check_completion_promise_based(output):
                    self.logger.info('Task complete (promise-based check)')
                    self._finalize(True, iteration)
                    return True
            
            # Check for errors that indicate we should stop
            if 'ERROR' in output and 'TASK_COMPLETE' not in output:
                self.logger.warning('Error detected in output')
            
            # Prepare next iteration
            current_prompt = self._prepare_next_prompt(prompt, output, iteration)
            
            # Small delay between iterations
            time.sleep(2)
        
        # Max iterations reached
        self.logger.warning(f'Max iterations ({self.max_iterations}) reached')
        self._finalize(False, iteration, 'Max iterations reached')
        return False
    
    def _prepare_next_prompt(self, original_prompt: str, last_output: str,
                            iteration: int) -> str:
        """
        Prepare prompt for next iteration.
        
        Includes previous output for context.
        """
        return f'''{original_prompt}

---
PREVIOUS ITERATION OUTPUT:
{last_output[-2000:]}  # Last 2000 chars for context

Continue working on the task. If the task is complete, output: {self.completion_signal}
'''
    
    def _finalize(self, success: bool, iterations: int, 
                  reason: str = '') -> None:
        """Finalize the loop."""
        self.state = {
            'status': 'completed' if success else 'failed',
            'completed': datetime.now().isoformat(),
            'iterations': iterations,
            'success': success,
            'reason': reason
        }
        self._save_state()
        
        if success:
            self.logger.info(f'Loop completed successfully in {iterations} iterations')
        else:
            self.logger.error(f'Loop failed after {iterations} iterations: {reason}')


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Ralph Wiggum Loop for autonomous task completion'
    )
    parser.add_argument('vault_path', type=str, help='Path to Obsidian vault')
    parser.add_argument('prompt', type=str, help='Task prompt')
    parser.add_argument('--max-iterations', type=int, default=10,
                        help='Maximum iterations (default: 10)')
    parser.add_argument('--mode', type=str, choices=['file', 'promise'],
                        default='file', help='Completion check mode')
    parser.add_argument('--signal', type=str, default='TASK_COMPLETE',
                        help='Completion signal for promise mode')
    
    args = parser.parse_args()
    
    vault = Path(args.vault_path)
    loop = RalphLoop(
        vault_path=vault,
        max_iterations=args.max_iterations,
        completion_signal=args.signal
    )
    
    success = loop.run(args.prompt, completion_mode=args.mode)
    
    exit(0 if success else 1)


if __name__ == '__main__':
    main()
