"""
Structured logging implementation using Zap.
"""
import json
import logging
import os
import sys
from typing import Any, Dict, Optional, Union

class ZapLogger:
    """
    Structured logger implementation using Zap-inspired format.
    This is a simplified version that outputs structured logs in JSON format.
    """
    
    def __init__(
        self,
        service_name: str,
        log_level: str = "INFO",
        development_mode: bool = False,
        include_caller: bool = True,
    ):
        """
        Initialize the Zap logger.
        
        Args:
            service_name: Name of the service
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            development_mode: Whether to use development mode (pretty-printed logs)
            include_caller: Whether to include caller information in logs
        """
        self.service_name = service_name
        self.development_mode = development_mode
        self.include_caller = include_caller
        
        # Set up Python's built-in logging
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(getattr(logging, log_level))
        
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Create console handler
        handler = logging.StreamHandler(sys.stdout)
        
        # Create formatter
        if development_mode:
            # Simple format for development
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            )
        else:
            # JSON formatter for production
            formatter = self._json_formatter
        
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def _json_formatter(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON-formatted log string
        """
        log_data = {
            "timestamp": self._format_time(record.created),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
        }
        
        # Include exception info if available
        if record.exc_info:
            log_data["exception"] = self._format_exception(record.exc_info)
        
        # Include caller info if enabled
        if self.include_caller:
            log_data["caller"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }
        
        # Include extra fields
        if hasattr(record, "extra") and record.extra:
            log_data.update(record.extra)
        
        return json.dumps(log_data)
    
    def _format_time(self, timestamp: float) -> str:
        """
        Format timestamp as ISO 8601.
        
        Args:
            timestamp: UNIX timestamp
            
        Returns:
            ISO 8601 formatted timestamp
        """
        from datetime import datetime
        return datetime.fromtimestamp(timestamp).isoformat()
    
    def _format_exception(self, exc_info) -> Dict[str, str]:
        """
        Format exception info.
        
        Args:
            exc_info: Exception info tuple
            
        Returns:
            Formatted exception info
        """
        import traceback
        exc_type, exc_value, exc_traceback = exc_info
        return {
            "type": exc_type.__name__,
            "message": str(exc_value),
            "traceback": "".join(traceback.format_exception(*exc_info)),
        }
    
    def _log(
        self,
        level: int,
        msg: str,
        *args,
        extra: Optional[Dict[str, Any]] = None,
        exc_info=None,
        **kwargs
    ):
        """
        Log a message.
        
        Args:
            level: Log level
            msg: Log message
            args: Message format args
            extra: Extra fields to include in the log
            exc_info: Exception info
            kwargs: Extra fields to include in the log
        """
        # Combine extra and kwargs
        combined_extra = {}
        if extra:
            combined_extra.update(extra)
        if kwargs:
            combined_extra.update(kwargs)
        
        # Create LogRecord with extra fields
        record = logging.LogRecord(
            name=self.logger.name,
            level=level,
            pathname=sys._getframe(2).f_code.co_filename,
            lineno=sys._getframe(2).f_lineno,
            msg=msg,
            args=args,
            exc_info=exc_info,
            func=sys._getframe(2).f_code.co_name,
        )
        
        # Add extra fields
        record.extra = combined_extra
        
        # Process the record
        self.logger.handle(record)
    
    def debug(self, msg: str, *args, **kwargs):
        """Log a debug message."""
        self._log(logging.DEBUG, msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        """Log an info message."""
        self._log(logging.INFO, msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        """Log a warning message."""
        self._log(logging.WARNING, msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        """Log an error message."""
        self._log(logging.ERROR, msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        """Log a critical message."""
        self._log(logging.CRITICAL, msg, *args, **kwargs)

def get_logger(
    service_name: str = "orbithost",
    log_level: str = None,
    development_mode: bool = None,
) -> ZapLogger:
    """
    Get a configured logger instance.
    
    Args:
        service_name: Name of the service
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        development_mode: Whether to use development mode
        
    Returns:
        Configured logger instance
    """
    # Get settings from environment variables if not provided
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO")
    
    if development_mode is None:
        development_mode = os.getenv("ENVIRONMENT", "development") == "development"
    
    return ZapLogger(
        service_name=service_name,
        log_level=log_level,
        development_mode=development_mode,
    )
