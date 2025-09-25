# error_handler.py
# Centralized error handling utilities for CodeBase application

import logging
import traceback
import tkinter as tk
from tkinter import messagebox
from typing import Optional, Callable, Any, Dict
from exceptions import (
    CodeBaseError, FileOperationError, RepositoryError, CacheError, 
    UIError, SecurityError, ConfigurationError, ThreadingError
)

class ErrorHandler:
    """Centralized error handling for the CodeBase application."""
    
    def __init__(self, gui=None):
        self.gui = gui
        self.error_callbacks = {}
        self.setup_default_callbacks()
    
    def setup_default_callbacks(self):
        """Setup default error handling callbacks."""
        self.error_callbacks = {
            FileOperationError: self._handle_file_error,
            RepositoryError: self._handle_repository_error,
            CacheError: self._handle_cache_error,
            UIError: self._handle_ui_error,
            SecurityError: self._handle_security_error,
            ConfigurationError: self._handle_configuration_error,
            ThreadingError: self._handle_threading_error,
            CodeBaseError: self._handle_generic_error,
            Exception: self._handle_unexpected_error
        }
    
    def handle_error(self, error: Exception, context: str = None, show_ui: bool = True) -> bool:
        """
        Handle an error with appropriate logging and UI feedback.
        
        Args:
            error: The exception to handle
            context: Additional context about where the error occurred
            show_ui: Whether to show UI error messages
            
        Returns:
            True if error was handled successfully, False otherwise
        """
        try:
            # Log the error with context
            self._log_error(error, context)
            
            # Get appropriate handler
            handler = self._get_error_handler(error)
            
            # Handle the error
            handled = handler(error, context, show_ui)
            
            return handled
            
        except Exception as handler_error:
            # Fallback if error handling itself fails
            logging.critical(f"Error in error handler: {handler_error}", exc_info=True)
            return False
    
    def _get_error_handler(self, error: Exception) -> Callable:
        """Get the appropriate error handler for the exception type."""
        error_type = type(error)
        
        # Check for exact match first
        if error_type in self.error_callbacks:
            return self.error_callbacks[error_type]
        
        # Check for base class matches
        for exception_type, handler in self.error_callbacks.items():
            if isinstance(error, exception_type):
                return handler
        
        # Default to generic handler
        return self.error_callbacks[Exception]
    
    def _log_error(self, error: Exception, context: str = None):
        """Log error with appropriate level and details."""
        if isinstance(error, CodeBaseError):
            log_level = logging.WARNING if error.error_code in ["FILE_OPERATION_ERROR", "CACHE_ERROR"] else logging.ERROR
            log_message = f"[{error.error_code}] {error.message}"
            if context:
                log_message = f"{context}: {log_message}"
            logging.log(log_level, log_message, exc_info=True)
        else:
            log_message = str(error)
            if context:
                log_message = f"{context}: {log_message}"
            logging.error(log_message, exc_info=True)
    
    def _handle_file_error(self, error: FileOperationError, context: str = None, show_ui: bool = True) -> bool:
        """Handle file operation errors."""
        if show_ui and self.gui:
            message = f"File operation failed: {error.message}"
            if error.file_path:
                message += f"\nFile: {error.file_path}"
            if error.operation:
                message += f"\nOperation: {error.operation}"
            
            self.gui.show_status_message(message, error=True)
            messagebox.showerror("File Error", message)
        
        return True
    
    def _handle_repository_error(self, error: RepositoryError, context: str = None, show_ui: bool = True) -> bool:
        """Handle repository errors."""
        if show_ui and self.gui:
            message = f"Repository operation failed: {error.message}"
            if error.repo_path:
                message += f"\nRepository: {error.repo_path}"
            if error.operation:
                message += f"\nOperation: {error.operation}"
            
            self.gui.show_status_message(message, error=True)
            messagebox.showerror("Repository Error", message)
        
        return True
    
    def _handle_cache_error(self, error: CacheError, context: str = None, show_ui: bool = True) -> bool:
        """Handle cache errors."""
        if show_ui and self.gui:
            message = f"Cache operation failed: {error.message}"
            if error.cache_key:
                message += f"\nCache key: {error.cache_key}"
            
            self.gui.show_status_message(message, error=True)
        
        return True
    
    def _handle_ui_error(self, error: UIError, context: str = None, show_ui: bool = True) -> bool:
        """Handle UI errors."""
        if show_ui and self.gui:
            message = f"UI operation failed: {error.message}"
            if error.component:
                message += f"\nComponent: {error.component}"
            
            self.gui.show_status_message(message, error=True)
            messagebox.showerror("UI Error", message)
        
        return True
    
    def _handle_security_error(self, error: SecurityError, context: str = None, show_ui: bool = True) -> bool:
        """Handle security errors."""
        if show_ui and self.gui:
            message = f"Security violation: {error.message}"
            if error.attempted_path:
                message += f"\nAttempted path: {error.attempted_path}"
            
            self.gui.show_status_message(message, error=True)
            messagebox.showerror("Security Error", message)
        
        return True
    
    def _handle_configuration_error(self, error: ConfigurationError, context: str = None, show_ui: bool = True) -> bool:
        """Handle configuration errors."""
        if show_ui and self.gui:
            message = f"Configuration error: {error.message}"
            if error.config_key:
                message += f"\nConfiguration key: {error.config_key}"
            
            self.gui.show_status_message(message, error=True)
            messagebox.showerror("Configuration Error", message)
        
        return True
    
    def _handle_threading_error(self, error: ThreadingError, context: str = None, show_ui: bool = True) -> bool:
        """Handle threading errors."""
        if show_ui and self.gui:
            message = f"Threading error: {error.message}"
            if error.thread_name:
                message += f"\nThread: {error.thread_name}"
            
            self.gui.show_status_message(message, error=True)
            messagebox.showerror("Threading Error", message)
        
        return True
    
    def _handle_generic_error(self, error: CodeBaseError, context: str = None, show_ui: bool = True) -> bool:
        """Handle generic CodeBase errors."""
        if show_ui and self.gui:
            message = f"Application error: {error.message}"
            self.gui.show_status_message(message, error=True)
            messagebox.showerror("Application Error", message)
        
        return True
    
    def _handle_unexpected_error(self, error: Exception, context: str = None, show_ui: bool = True) -> bool:
        """Handle unexpected errors."""
        if show_ui and self.gui:
            message = f"Unexpected error: {str(error)}"
            self.gui.show_status_message(message, error=True)
            messagebox.showerror("Unexpected Error", message)
        
        return True
    
    def register_callback(self, exception_type: type, callback: Callable):
        """Register a custom error handling callback."""
        self.error_callbacks[exception_type] = callback
    
    def safe_execute(self, func: Callable, *args, context: str = None, show_ui: bool = True, **kwargs) -> Any:
        """
        Safely execute a function with error handling.
        
        Args:
            func: Function to execute
            *args: Function arguments
            context: Context for error reporting
            show_ui: Whether to show UI error messages
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or None if error occurred
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.handle_error(e, context, show_ui)
            return None

# Global error handler instance
_global_error_handler = None

def get_error_handler(gui=None) -> ErrorHandler:
    """Get the global error handler instance."""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler(gui)
    return _global_error_handler

def handle_error(error: Exception, context: str = None, show_ui: bool = True) -> bool:
    """Convenience function to handle errors."""
    return get_error_handler().handle_error(error, context, show_ui)

def safe_execute(func: Callable, *args, context: str = None, show_ui: bool = True, **kwargs) -> Any:
    """Convenience function to safely execute functions."""
    return get_error_handler().safe_execute(func, *args, context=context, show_ui=show_ui, **kwargs)
