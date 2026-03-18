"""
Error Recovery and Graceful Degradation System

Provides robust error handling, retry logic, and graceful degradation
for the AI Employee system.

Gold tier requirement for production reliability.
"""

import time
import random
import logging
from typing import Callable, Any, Optional, Tuple, List
from functools import wraps
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import json


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: Tuple = (Exception,)


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout: float = 30.0  # seconds
    half_open_attempts: int = 3


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    Prevents cascading failures by stopping requests to failing services.
    """
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = 'closed'  # closed, open, half-open
        self.half_open_attempts = 0
    
    def record_success(self) -> None:
        """Record a successful call."""
        self.failures = 0
        self.state = 'closed'
        self.half_open_attempts = 0
    
    def record_failure(self) -> None:
        """Record a failed call."""
        self.failures += 1
        self.last_failure_time = datetime.now()
        
        if self.failures >= self.config.failure_threshold:
            self.state = 'open'
    
    def can_execute(self) -> bool:
        """Check if call can be executed."""
        if self.state == 'closed':
            return True
        
        if self.state == 'open':
            if self.last_failure_time is None:
                return True
            
            elapsed = datetime.now() - self.last_failure_time
            if elapsed.total_seconds() >= self.config.recovery_timeout:
                self.state = 'half-open'
                self.half_open_attempts = 0
                return True
            return False
        
        if self.state == 'half-open':
            if self.half_open_attempts < self.config.half_open_attempts:
                self.half_open_attempts += 1
                return True
            return False
        
        return False
    
    def get_state(self) -> dict:
        """Get circuit breaker state."""
        return {
            'state': self.state,
            'failures': self.failures,
            'last_failure': self.last_failure_time.isoformat() if self.last_failure_time else None
        }


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator for adding retry logic to functions.
    
    Usage:
        @with_retry(RetryConfig(max_attempts=5, base_delay=2.0))
        def my_function():
            pass
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(1, config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts:
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.exponential_base ** (attempt - 1)),
                        config.max_delay
                    )
                    
                    # Add jitter
                    if config.jitter:
                        delay = delay * (0.5 + random.random())
                    
                    logging.warning(
                        f'{func.__name__} attempt {attempt} failed: {e}. '
                        f'Retrying in {delay:.2f}s'
                    )
                    time.sleep(delay)
            
            # Should never reach here, but just in case
            raise last_exception
        
        return wrapper
    return decorator


class GracefulDegradation:
    """
    Manages graceful degradation when services fail.
    
    Provides fallback behavior when primary services are unavailable.
    """
    
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.logs_dir = vault_path / 'Logs'
        self.degradation_state_file = self.logs_dir / 'degradation_state.json'
        
        # Service states
        self.services = {
            'gmail': {'enabled': True, 'fallback': 'queue_email'},
            'whatsapp': {'enabled': True, 'fallback': 'queue_message'},
            'linkedin': {'enabled': True, 'fallback': 'queue_post'},
            'qwen': {'enabled': True, 'fallback': 'log_only'},
            'database': {'enabled': True, 'fallback': 'memory_only'}
        }
        
        # Load existing state
        self._load_state()
    
    def _load_state(self) -> None:
        """Load degradation state from file."""
        if self.degradation_state_file.exists():
            try:
                state = json.loads(self.degradation_state_file.read_text())
                self.services.update(state.get('services', {}))
            except Exception as e:
                logging.warning(f'Could not load degradation state: {e}')
    
    def _save_state(self) -> None:
        """Save degradation state to file."""
        try:
            state = {
                'last_updated': datetime.now().isoformat(),
                'services': self.services
            }
            self.degradation_state_file.write_text(json.dumps(state, indent=2))
        except Exception as e:
            logging.warning(f'Could not save degradation state: {e}')
    
    def disable_service(self, service_name: str, reason: str = '') -> None:
        """Disable a service and switch to fallback."""
        if service_name in self.services:
            self.services[service_name]['enabled'] = False
            self.services[service_name]['disabled_reason'] = reason
            self.services[service_name]['disabled_at'] = datetime.now().isoformat()
            self._save_state()
            logging.warning(f'Service {service_name} disabled: {reason}')
    
    def enable_service(self, service_name: str) -> None:
        """Re-enable a service."""
        if service_name in self.services:
            self.services[service_name]['enabled'] = True
            self.services[service_name].pop('disabled_reason', None)
            self.services[service_name].pop('disabled_at', None)
            self._save_state()
            logging.info(f'Service {service_name} re-enabled')
    
    def is_service_enabled(self, service_name: str) -> bool:
        """Check if a service is enabled."""
        return self.services.get(service_name, {}).get('enabled', False)
    
    def get_fallback(self, service_name: str) -> str:
        """Get fallback action for a service."""
        return self.services.get(service_name, {}).get('fallback', 'log_only')
    
    def execute_with_fallback(self, service_name: str, 
                              primary_func: Callable,
                              fallback_func: Optional[Callable] = None,
                              *args, **kwargs) -> Any:
        """
        Execute primary function with fallback on failure.
        
        Args:
            service_name: Name of the service
            primary_func: Primary function to execute
            fallback_func: Optional fallback function
            *args, **kwargs: Arguments for functions
            
        Returns:
            Result of primary or fallback function
        """
        if not self.is_service_enabled(service_name):
            logging.info(f'Service {service_name} disabled, using fallback')
            if fallback_func:
                return fallback_func(*args, **kwargs)
            return None
        
        try:
            return primary_func(*args, **kwargs)
        except Exception as e:
            logging.error(f'Service {service_name} failed: {e}')
            self.disable_service(service_name, str(e))
            
            if fallback_func:
                logging.info(f'Executing fallback for {service_name}')
                return fallback_func(*args, **kwargs)
            
            logging.warning(f'No fallback available for {service_name}')
            return None
    
    def get_status(self) -> dict:
        """Get current degradation status."""
        return {
            'services': self.services,
            'degraded': any(not s['enabled'] for s in self.services.values())
        }


class HealthMonitor:
    """
    Monitors health of all system components.
    
    Performs periodic health checks and triggers degradation when needed.
    """
    
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.logs_dir = vault_path / 'Logs'
        self.health_log = self.logs_dir / 'health_log.json'
        
        self.degradation = GracefulDegradation(vault_path)
        self.circuit_breakers = {
            'gmail': CircuitBreaker(CircuitBreakerConfig()),
            'whatsapp': CircuitBreaker(CircuitBreakerConfig()),
            'linkedin': CircuitBreaker(CircuitBreakerConfig()),
            'qwen': CircuitBreaker(CircuitBreakerConfig())
        }
        
        self.health_history: List[dict] = []
    
    def record_health(self, component: str, healthy: bool, 
                      details: Optional[dict] = None) -> None:
        """Record health check result."""
        record = {
            'timestamp': datetime.now().isoformat(),
            'component': component,
            'healthy': healthy,
            'details': details or {}
        }
        
        self.health_history.append(record)
        
        # Keep only last 1000 records
        if len(self.health_history) > 1000:
            self.health_history = self.health_history[-1000:]
        
        # Update circuit breaker
        if component in self.circuit_breakers:
            cb = self.circuit_breakers[component]
            if healthy:
                cb.record_success()
            else:
                cb.record_failure()
                
                # Trigger degradation if circuit is open
                if cb.state == 'open':
                    self.degradation.disable_service(
                        component, 
                        f'Circuit breaker open after {cb.failures} failures'
                    )
        
        # Save health log
        self._save_health_log()
    
    def _save_health_log(self) -> None:
        """Save health log to file."""
        try:
            log_data = {
                'last_updated': datetime.now().isoformat(),
                'history': self.health_history[-100:]  # Last 100 entries
            }
            self.health_log.write_text(json.dumps(log_data, indent=2))
        except Exception as e:
            logging.warning(f'Could not save health log: {e}')
    
    def can_execute(self, component: str) -> bool:
        """Check if a component can execute."""
        if not self.degradation.is_service_enabled(component):
            return False
        
        if component in self.circuit_breakers:
            return self.circuit_breakers[component].can_execute()
        
        return True
    
    def get_system_health(self) -> dict:
        """Get overall system health status."""
        return {
            'timestamp': datetime.now().isoformat(),
            'degradation_status': self.degradation.get_status(),
            'circuit_breakers': {
                name: cb.get_state() 
                for name, cb in self.circuit_breakers.items()
            },
            'recent_failures': [
                r for r in self.health_history[-50:] 
                if not r['healthy']
            ]
        }
    
    def run_health_check(self) -> dict:
        """
        Run health checks on all components.
        
        Returns:
            Health status dictionary
        """
        results = {}
        
        # Check file system
        try:
            test_file = self.logs_dir / '.health_check'
            test_file.write_text('ok')
            test_file.unlink()
            results['filesystem'] = True
        except:
            results['filesystem'] = False
        
        # Check Qwen Code
        try:
            import subprocess
            result = subprocess.run(
                ['qwen', '--version'],
                capture_output=True,
                timeout=10
            )
            results['qwen'] = result.returncode == 0
        except:
            results['qwen'] = False
        
        # Record results
        for component, healthy in results.items():
            self.record_health(component, healthy)
        
        return results


# Global health monitor instance
_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor(vault_path: Path) -> HealthMonitor:
    """Get or create global health monitor instance."""
    global _health_monitor
    
    if _health_monitor is None:
        _health_monitor = HealthMonitor(vault_path)
    
    return _health_monitor
