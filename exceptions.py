# exceptions.py
# Custom exceptions for CodeBase application

class CodeBaseError(Exception):
    """Base exception for all CodeBase-specific errors."""
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "UNKNOWN_ERROR"
        self.details = details or {}
    
    def __str__(self):
        return f"[{self.error_code}] {self.message}"

class FileOperationError(CodeBaseError):
    """Errors related to file operations."""
    def __init__(self, message: str, file_path: str = None, operation: str = None, details: dict = None):
        super().__init__(message, "FILE_OPERATION_ERROR", details)
        self.file_path = file_path
        self.operation = operation

class RepositoryError(CodeBaseError):
    """Errors related to repository operations."""
    def __init__(self, message: str, repo_path: str = None, operation: str = None, details: dict = None):
        super().__init__(message, "REPOSITORY_ERROR", details)
        self.repo_path = repo_path
        self.operation = operation

class CacheError(CodeBaseError):
    """Errors related to cache operations."""
    def __init__(self, message: str, cache_key: str = None, operation: str = None, details: dict = None):
        super().__init__(message, "CACHE_ERROR", details)
        self.cache_key = cache_key
        self.operation = operation

class UIError(CodeBaseError):
    """Errors related to UI operations."""
    def __init__(self, message: str, component: str = None, operation: str = None, details: dict = None):
        super().__init__(message, "UI_ERROR", details)
        self.component = component
        self.operation = operation

class SecurityError(CodeBaseError):
    """Security-related errors."""
    def __init__(self, message: str, attempted_path: str = None, details: dict = None):
        super().__init__(message, "SECURITY_ERROR", details)
        self.attempted_path = attempted_path

class ConfigurationError(CodeBaseError):
    """Errors related to configuration."""
    def __init__(self, message: str, config_key: str = None, details: dict = None):
        super().__init__(message, "CONFIGURATION_ERROR", details)
        self.config_key = config_key

class ThreadingError(CodeBaseError):
    """Errors related to threading operations."""
    def __init__(self, message: str, thread_name: str = None, operation: str = None, details: dict = None):
        super().__init__(message, "THREADING_ERROR", details)
        self.thread_name = thread_name
        self.operation = operation
