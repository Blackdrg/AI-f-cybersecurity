"""Database monitoring package.

Exports:
- DatabaseMonitor: Main monitoring class
- Alert: Alert dataclass
- AlertSeverity: Alert severity enumeration
- get_monitor: Get global monitor instance
- init_monitor: Initialize global monitor
"""

from .db_monitor import (
    DatabaseMonitor,
    Alert,
    AlertSeverity,
    QueryMetrics,
    get_monitor,
    init_monitor,
)

__all__ = [
    'DatabaseMonitor',
    'Alert',
    'AlertSeverity',
    'QueryMetrics',
    'get_monitor',
    'init_monitor',
]
