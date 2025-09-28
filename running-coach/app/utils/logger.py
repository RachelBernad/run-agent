"""Structured logger for the NiceGUI frontend application."""

import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from app.constants import LOG_FORMAT


class StructuredLogger:
    """Simple structured logger with timestamp and metadata support."""
    
    def __init__(self, name: str = "running_coach_ui"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Avoid adding multiple handlers
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(LOG_FORMAT)
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _log_with_meta(self, level: str, message: str, **meta: Any) -> None:
        """Log message with metadata."""
        timestamp = datetime.now().isoformat()
        meta_str = " | ".join([f"{k}={v}" for k, v in meta.items()]) if meta else ""
        
        if meta_str:
            full_message = f"[{timestamp}] {message} | {meta_str}"
        else:
            full_message = f"[{timestamp}] {message}"
        
        getattr(self.logger, level)(full_message)
    
    def info(self, message: str, **meta: Any) -> None:
        """Log info message with optional metadata."""
        self._log_with_meta("info", message, **meta)
    
    def warn(self, message: str, **meta: Any) -> None:
        """Log warning message with optional metadata."""
        self._log_with_meta("warning", message, **meta)
    
    def error(self, message: str, **meta: Any) -> None:
        """Log error message with optional metadata."""
        self._log_with_meta("error", message, **meta)


# Global logger instance
logger = StructuredLogger()
