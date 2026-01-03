"""
Logging utilities for Portfolio Agent.

Provides comprehensive logging with:
- Custom TRACE level for very detailed output
- Timestamp-based log filenames
- Dual output: console (formatted) + file (full details)
- Smart preview handling for long content
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


# Custom TRACE level (below DEBUG)
TRACE_LEVEL = 5
logging.addLevelName(TRACE_LEVEL, "TRACE")


class PortfolioLogger:
    """Custom logger for Portfolio Agent with dual output and smart previews."""

    _instance = None
    _log_file_path = None

    def __new__(cls):
        """Singleton pattern to ensure one logger instance per run."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize logger with dual output (console + file)."""
        if self._initialized:
            return

        # Get configuration from environment
        log_level = os.getenv("LOG_LEVEL", "TRACE").upper()
        log_to_console = os.getenv("LOG_TO_CONSOLE", "true").lower() == "true"
        log_dir = os.getenv("LOG_DIR", "logs")

        # Create logs directory
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)

        # Generate timestamp-based log filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"portfolio_agent_{timestamp}.log"
        self._log_file_path = log_path / log_filename

        # Create root logger
        self.logger = logging.getLogger("portfolio_agent")
        self.logger.setLevel(TRACE_LEVEL)  # Capture all levels

        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # File handler - full details with TRACE level
        file_handler = logging.FileHandler(self._log_file_path, encoding='utf-8')
        file_handler.setLevel(TRACE_LEVEL)
        file_formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s:%(funcName)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # Console handler - cleaner format, configurable level
        if log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_level = getattr(logging, log_level, logging.INFO)
            console_handler.setLevel(console_level)
            console_formatter = logging.Formatter(
                '[%(levelname)s] %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

        self._initialized = True

        # Log initialization
        self.info(f"Logging initialized: {self._log_file_path}")
        self.info(f"Log level: {log_level} | Console output: {log_to_console}")

    def trace(self, message: str, *args, **kwargs):
        """Log TRACE level message (very detailed output)."""
        self.logger.log(TRACE_LEVEL, message, *args, **kwargs)

    def debug(self, message: str, *args, **kwargs):
        """Log DEBUG level message."""
        self.logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        """Log INFO level message."""
        self.logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        """Log WARNING level message."""
        self.logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        """Log ERROR level message."""
        self.logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        """Log CRITICAL level message."""
        self.logger.critical(message, *args, **kwargs)

    def info_preview(self, label: str, full_text: str, preview_len: int = 300, level: str = "info"):
        """
        Log with smart preview handling.

        Console: Shows truncated preview
        File: Contains full text

        Args:
            label: Description of the content
            full_text: Complete text to log
            preview_len: Characters to show in console preview
            level: Log level (trace, debug, info, warning, error)
        """
        # Log full text to file
        log_method = getattr(self, level.lower(), self.info)
        log_method(f"{label}: {full_text}")

        # If text is longer than preview, log a note about truncation
        if len(full_text) > preview_len:
            preview = full_text[:preview_len] + "..."
            # This will show in console but full text is already in file
            log_method(f"{label} (preview): {preview}")

    def separator(self, char: str = "=", length: int = 80, level: str = "info"):
        """
        Log a separator line.

        Args:
            char: Character to use for separator
            length: Length of separator line
            level: Log level
        """
        log_method = getattr(self, level.lower(), self.info)
        log_method(char * length)

    def section(self, title: str, char: str = "=", length: int = 80, level: str = "info"):
        """
        Log a section header with separators.

        Args:
            title: Section title
            char: Character for separator
            length: Length of separator
            level: Log level
        """
        log_method = getattr(self, level.lower(), self.info)
        log_method(char * length)
        log_method(title)
        log_method(char * length)

    def get_log_file_path(self) -> Path:
        """Get the current log file path."""
        return self._log_file_path

    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a child logger with a specific name.

        Args:
            name: Logger name (e.g., 'agents.portfolio_builder')

        Returns:
            Logger instance
        """
        return logging.getLogger(f"portfolio_agent.{name}")


# Global logger instance
_logger_instance = None


def get_logger(name: Optional[str] = None) -> PortfolioLogger:
    """
    Get the global logger instance.

    Args:
        name: Optional logger name for child logger

    Returns:
        PortfolioLogger instance or child logger
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = PortfolioLogger()

    if name:
        # Return a wrapper that uses the child logger
        child_logger = _logger_instance.get_logger(name)

        class ChildLoggerWrapper:
            def __init__(self, child):
                self._child = child
                self._parent = _logger_instance

            def trace(self, message, *args, **kwargs):
                self._child.log(TRACE_LEVEL, message, *args, **kwargs)

            def debug(self, message, *args, **kwargs):
                self._child.debug(message, *args, **kwargs)

            def info(self, message, *args, **kwargs):
                self._child.info(message, *args, **kwargs)

            def warning(self, message, *args, **kwargs):
                self._child.warning(message, *args, **kwargs)

            def error(self, message, *args, **kwargs):
                self._child.error(message, *args, **kwargs)

            def critical(self, message, *args, **kwargs):
                self._child.critical(message, *args, **kwargs)

            def info_preview(self, *args, **kwargs):
                return self._parent.info_preview(*args, **kwargs)

            def separator(self, *args, **kwargs):
                return self._parent.separator(*args, **kwargs)

            def section(self, *args, **kwargs):
                return self._parent.section(*args, **kwargs)

            def get_log_file_path(self):
                return self._parent.get_log_file_path()

        return ChildLoggerWrapper(child_logger)

    return _logger_instance


# Convenience function for quick access
def init_logger() -> PortfolioLogger:
    """Initialize and return the global logger."""
    return get_logger()


if __name__ == "__main__":
    # Test the logger
    logger = get_logger()

    logger.section("Logger Test")
    logger.trace("This is a TRACE message (very detailed)")
    logger.debug("This is a DEBUG message")
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")
    logger.separator()

    # Test preview functionality
    long_text = "x" * 500
    logger.info_preview("Long text test", long_text, preview_len=50)

    # Test child logger
    child = get_logger("test_module")
    child.info("Message from child logger")

    print(f"\nLog file created at: {logger.get_log_file_path()}")
