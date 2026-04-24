import logging
import json
import time
import uuid
from typing import Optional, Any, Dict
from pythonjsonlogger import jsonlogger

class EnterpriseLogger:
    """
    Structured JSON logger for enterprise observability.
    Includes request_id, org_id, and latency tracking.
    """
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Check if handler already exists
        if not self.logger.handlers:
            logHandler = logging.StreamHandler()
            formatter = jsonlogger.JsonFormatter(
                '%(asctime)s %(name)s %(levelname)s %(message)s %(request_id)s %(org_id)s %(latency_ms)s'
            )
            logHandler.setFormatter(formatter)
            self.logger.addHandler(logHandler)

    def _get_extra(self, request_id: Optional[str] = None, org_id: Optional[str] = None, latency_ms: Optional[float] = None) -> Dict:
        return {
            "request_id": request_id or "internal",
            "org_id": org_id or "system",
            "latency_ms": latency_ms or 0.0
        }

    def info(self, msg: str, request_id: Optional[str] = None, org_id: Optional[str] = None, latency_ms: Optional[float] = None, **kwargs):
        extra = self._get_extra(request_id, org_id, latency_ms)
        extra.update(kwargs)
        self.logger.info(msg, extra=extra)

    def error(self, msg: str, request_id: Optional[str] = None, org_id: Optional[str] = None, **kwargs):
        extra = self._get_extra(request_id, org_id)
        extra.update(kwargs)
        self.logger.error(msg, extra=extra)

    def warning(self, msg: str, request_id: Optional[str] = None, org_id: Optional[str] = None, **kwargs):
        extra = self._get_extra(request_id, org_id)
        extra.update(kwargs)
        self.logger.warning(msg, extra=extra)

def get_logger(name: str) -> EnterpriseLogger:
    return EnterpriseLogger(name)
