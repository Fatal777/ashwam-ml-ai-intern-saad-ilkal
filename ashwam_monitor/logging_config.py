"""
Logging configuration for ashwam_monitor.
Provides structured logging with file and console output.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logging(
    log_dir: Path = None,
    level: int = logging.INFO,
    verbose: bool = False
) -> logging.Logger:
    """
    Configure logging for the monitoring tool.
    
    Args:
        log_dir: Directory to store log files. If None, logs only to console.
        level: Logging level (default: INFO)
        verbose: If True, set to DEBUG level
        
    Returns:
        Configured logger instance
    """
    if verbose:
        level = logging.DEBUG
    
    logger = logging.getLogger("ashwam_monitor")
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler (if log_dir provided)
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"monitor_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # Always log everything to file
        file_format = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
        
        logger.info(f"Logging to file: {log_file}")
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a child logger for a specific module.
    
    Args:
        name: Module name (e.g., 'invariants', 'drift')
        
    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f"ashwam_monitor.{name}")
    return logging.getLogger("ashwam_monitor")
