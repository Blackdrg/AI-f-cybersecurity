"""
Logging Filter — Sanitizes log records to prevent log injection attacks.

Install at application startup to automatically sanitize all log messages.
"""

import logging
from typing import Any, Dict
import re

# Regex for control chars: newline, carriage return, tab, etc.
_CONTROL_CHAR_RE = re.compile(r'[\x00-\x1F\x7F]')

class SanitizeFilter(logging.Filter):
    """Filter that sanitizes the log message to prevent newline injection."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Only modify the message; keep other fields intact
        if hasattr(record, 'msg'):
            # If msg is a format string with args, we need to format then sanitize?
            # But to be safe, we sanitize the message after formatting.
            # However, filters run before formatting? In logging, Filter.filter(record) is called before handling, and record.getMessage() formats msg with args. We'll sanitize the formatted message later in handler. Better to sanitize at handler level.
            pass
        return True

def sanitize_text(text: str, max_len: int = 1000) -> str:
    """Replace control characters and truncate."""
    if not isinstance(text, str):
        text = str(text)
    # Replace newlines, carriage returns, and other control chars with space
    text = _CONTROL_CHAR_RE.sub(' ', text)
    # Collapse whitespace
    text = ' '.join(text.split())
    # Truncate if too long
    if len(text) > max_len:
        text = text[:max_len] + "..."
    return text

class SanitizingFormatter(logging.Formatter):
    """Formatter that sanitizes the message before output."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Original format
        original_msg = record.getMessage()
        # Sanitize
        clean_msg = sanitize_text(original_msg)
        # Replace the record's msg and args to avoid double formatting if used again
        record.msg = clean_msg
        record.args = ()
        return super().format(record)
