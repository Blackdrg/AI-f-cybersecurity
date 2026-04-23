"""
Structured JSON logging configuration for production.
"""
import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict

try:
    from pythonjsonlogger import jsonlogger
    JSONLOGGER_AVAILABLE = True
except ImportError:
    JSONLOGGER_AVAILABLE = False


class StructuredLogger:
    """Wrapper to add structured context to log records."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._context = {}
    
    def set_context(self, **kwargs):
        """Set context fields that will be included in all subsequent logs."""
        self._context.update(kwargs)
    
    def clear_context(self):
        """Clear all context fields."""
        self._context.clear()
    
    def _log(self, level: int, msg: str, extra: Dict = None, **kwargs):
        """Internal log method that merges context with extra fields."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "logger": self.logger.name,
            "message": msg,
            "level": logging.getLevelName(level),
        }
        
        # Add context
        if self._context:
            log_data.update(self._context)
        
        # Add extra fields
        if extra:
            # Remove FastAPI internal keys that shouldn't be in JSON logs
            clean_extra = {k: v for k, v in extra.items() 
                          if not k.startswith('_') and k not in ['args', 'msg', 'levelname']}
            log_data.update(clean_extra)
        
        # Add kwargs as additional fields
        if kwargs:
            log_data.update(kwargs)
        
        # Remove None values
        log_data = {k: v for k, v in log_data.items() if v is not None}
        
        self.logger.log(level, msg, extra=log_data)
    
    def info(self, msg: str, **kwargs):
        self._log(logging.INFO, msg, **kwargs)
    
    def warning(self, msg: str, **kwargs):
        self._log(logging.WARNING, msg, **kwargs)
    
    def error(self, msg: str, **kwargs):
        self._log(logging.ERROR, msg, **kwargs)
    
    def debug(self, msg: str, **kwargs):
        self._log(logging.DEBUG, msg, **kwargs)
    
    def critical(self, msg: str, **kwargs):
        self._log(logging.CRITICAL, msg, **kwargs)


def setup_structured_logging():
    """
    Configure structured JSON logging for the application.
    Uses python-json-logger if available, falls back to standard logging.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    
    if JSONLOGGER_AVAILABLE:
        # Use JSON formatter for structured logs
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s',
            timestamp=True
        )
        handler.setFormatter(formatter)
    else:
        # Fallback to plain text but still include key fields
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
    
    root_logger.addHandler(handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)
    
    # Set our app logger
    app_logger = logging.getLogger("face-recognition")
    app_logger.setLevel(logging.INFO)
    
    return app_logger


def get_logger(name: str = None) -> StructuredLogger:
    """
    Get a structured logger instance.
    
    Usage:
        logger = get_logger(__name__)
        logger.info("User logged in", user_id="123", ip="1.2.3.4")
    """
    if name is None:
        # Get caller's module name
        import inspect
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get('__name__', 'face-recognition')
    
    return StructuredLogger(name)
