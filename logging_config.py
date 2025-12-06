# logging_config.py
# Centralized logging configuration for CodeBase application

import logging
import os
import sys
from typing import Optional, Dict, Any
from constants import ERROR_LOGGING_LEVEL

class LoggingConfig:
    """Centralized logging configuration manager."""
    
    _initialized = False
    _loggers = {}
    
    @classmethod
    def setup_logging(cls, 
                     level: str = None, 
                     log_file: str = None, 
                     console_output: bool = True,
                     format_string: str = None,
                     force: bool = False) -> None:
        """
        Setup centralized logging configuration.
        
        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Path to log file (optional)
            console_output: Whether to output to console
            format_string: Custom format string (optional)
            force: Force reconfiguration even if already initialized
        """
        if cls._initialized and not force:
            return
        
        # Default configuration
        default_level = level or ERROR_LOGGING_LEVEL or "INFO"
        default_format = format_string or '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # Convert string level to logging constant
        numeric_level = getattr(logging, default_level.upper(), logging.INFO)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)
        
        # Clear existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Create formatter
        formatter = logging.Formatter(default_format)
        
        # Console handler
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(numeric_level)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        # File handler
        if log_file:
            try:
                # Ensure log directory exists
                log_dir = os.path.dirname(log_file)
                if log_dir and not os.path.exists(log_dir):
                    os.makedirs(log_dir, exist_ok=True)
                
                file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
                file_handler.setLevel(numeric_level)
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
            except Exception as e:
                print(f"Warning: Could not setup file logging: {e}")
        
        cls._initialized = True
        logging.info(f"Logging configured: level={default_level}, file={log_file}, console={console_output}")
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger instance with the specified name.
        
        Args:
            name: Logger name (usually __name__)
            
        Returns:
            Logger instance
        """
        if not cls._initialized:
            cls.setup_logging()
        
        if name not in cls._loggers:
            cls._loggers[name] = logging.getLogger(name)
        
        return cls._loggers[name]
    
    @classmethod
    def set_level(cls, level: str) -> None:
        """
        Change the logging level for all loggers.
        
        Args:
            level: New logging level
        """
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        
        # Update root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)
        
        # Update all handlers
        for handler in root_logger.handlers:
            handler.setLevel(numeric_level)
        
        # Update all registered loggers
        for logger in cls._loggers.values():
            logger.setLevel(numeric_level)
        
        logging.info(f"Logging level changed to: {level}")
    
    @classmethod
    def add_file_handler(cls, log_file: str, level: str = None) -> None:
        """
        Add a file handler to existing logging configuration.
        
        Args:
            log_file: Path to log file
            level: Logging level for this handler (optional)
        """
        if not cls._initialized:
            cls.setup_logging()
        
        try:
            # Ensure log directory exists
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            # Create file handler
            file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
            
            if level:
                numeric_level = getattr(logging, level.upper(), logging.INFO)
                file_handler.setLevel(numeric_level)
            
            # Create formatter
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            
            # Add to root logger
            root_logger = logging.getLogger()
            root_logger.addHandler(file_handler)
            
            logging.info(f"Added file handler: {log_file}")
            
        except Exception as e:
            logging.error(f"Could not add file handler {log_file}: {e}")
    
    @classmethod
    def get_effective_level(cls) -> str:
        """
        Get the current effective logging level.
        
        Returns:
            Current logging level as string
        """
        if not cls._initialized:
            return "NOT_SET"
        
        root_logger = logging.getLogger()
        level_name = logging.getLevelName(root_logger.getEffectiveLevel())
        return level_name
    
    @classmethod
    def is_debug_enabled(cls) -> bool:
        """
        Check if debug logging is enabled.
        
        Returns:
            True if debug level is enabled
        """
        if not cls._initialized:
            return False
        
        root_logger = logging.getLogger()
        return root_logger.isEnabledFor(logging.DEBUG)

# Convenience functions
def setup_logging(level: str = None, log_file: str = None, console_output: bool = True, format_string: str = None, force: bool = False) -> None:
    """Convenience function to setup logging."""
    LoggingConfig.setup_logging(level, log_file, console_output, format_string, force)

def get_logger(name: str) -> logging.Logger:
    """Convenience function to get a logger."""
    return LoggingConfig.get_logger(name)

def set_log_level(level: str) -> None:
    """Convenience function to set log level."""
    LoggingConfig.set_level(level)

def is_debug() -> bool:
    """Convenience function to check if debug is enabled."""
    return LoggingConfig.is_debug_enabled()
