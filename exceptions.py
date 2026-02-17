# exceptions.py
# Custom exceptions for CodeBase application
from __future__ import annotations

from typing import Any, Optional


class CodeBaseError(Exception):
    """Base exception for all CodeBase-specific errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message: str = message
        self.error_code: str = error_code or "UNKNOWN_ERROR"
        self.details: dict[str, Any] = details or {}

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"


class FileOperationError(CodeBaseError):
    """Errors related to file operations."""

    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, "FILE_OPERATION_ERROR", details)
        self.file_path: Optional[str] = file_path
        self.operation: Optional[str] = operation


class RepositoryError(CodeBaseError):
    """Errors related to repository operations."""

    def __init__(
        self,
        message: str,
        repo_path: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, "REPOSITORY_ERROR", details)
        self.repo_path: Optional[str] = repo_path
        self.operation: Optional[str] = operation


class CacheError(CodeBaseError):
    """Errors related to cache operations."""

    def __init__(
        self,
        message: str,
        cache_key: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, "CACHE_ERROR", details)
        self.cache_key: Optional[str] = cache_key
        self.operation: Optional[str] = operation


class UIError(CodeBaseError):
    """Errors related to UI operations."""

    def __init__(
        self,
        message: str,
        component: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, "UI_ERROR", details)
        self.component: Optional[str] = component
        self.operation: Optional[str] = operation


class SecurityError(CodeBaseError):
    """Security-related errors."""

    def __init__(
        self,
        message: str,
        attempted_path: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, "SECURITY_ERROR", details)
        self.attempted_path: Optional[str] = attempted_path


class ConfigurationError(CodeBaseError):
    """Errors related to configuration."""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, "CONFIGURATION_ERROR", details)
        self.config_key: Optional[str] = config_key


class ThreadingError(CodeBaseError):
    """Errors related to threading operations."""

    def __init__(
        self,
        message: str,
        thread_name: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, "THREADING_ERROR", details)
        self.thread_name: Optional[str] = thread_name
        self.operation: Optional[str] = operation
