# security.py
# Comprehensive security utilities for CodeBase application

import os
import re
import hashlib
import mimetypes
from typing import Union, List, Optional, Tuple
from path_utils import normalize_path, is_path_within_base
from exceptions import SecurityError
from error_handler import handle_error
from constants import ERROR_HANDLING_ENABLED

class SecurityValidator:
    """Comprehensive security validation for file operations and content."""
    
    # Security constants
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB max file size
    MAX_TEMPLATE_SIZE = 1024 * 1024   # 1MB max template size
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max content length
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # JavaScript
        r'<?php.*?>',                   # PHP
        r'eval\s*\(',                  # eval() calls
        r'subprocess\s*\.',             # subprocess calls
        r'os\s*\.\s*system',           # os.system calls
        r'exec\s*\(',                  # exec() calls
        r'__import__\s*\(',            # __import__ calls
        r'compile\s*\(',               # compile() calls
        r'open\s*\([^)]*[\'"]w[\'"]',  # File write operations
        r'pickle\s*\.',                # pickle operations
        r'shelve\s*\.',                # shelve operations
        r'import\s+subprocess',        # subprocess imports
        r'import\s+os',                # os imports
        r'import\s+sys',               # sys imports
        r'from\s+subprocess',          # subprocess imports
        r'from\s+os',                  # os imports
        r'from\s+sys',                 # sys imports
    ]
    
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.scr', '.pif', '.vbs', '.js', '.jar',
        '.app', '.deb', '.rpm', '.dmg', '.pkg', '.msi', '.run', '.sh', '.ps1'
    }
    
    ALLOWED_TEMPLATE_EXTENSIONS = {'.txt', '.md', '.rst', '.py', '.js', '.html', '.css', '.json', '.yaml', '.yml'}
    
    def __init__(self):
        self.logger = None
    
    def set_logger(self, logger):
        """Set logger for security events."""
        self.logger = logger
    
    def validate_file_path(self, file_path: Union[str, os.PathLike], base_path: Union[str, os.PathLike] = None) -> Tuple[bool, str]:
        """
        Validate file path for security issues.
        
        Args:
            file_path: Path to validate
            base_path: Base directory for relative path validation
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            normalized_path = normalize_path(file_path)
            
            # Check for directory traversal attempts
            if '..' in normalized_path or normalized_path.startswith('/'):
                if base_path:
                    base_normalized = normalize_path(base_path)
                    if not is_path_within_base(normalized_path, base_normalized):
                        return False, f"Path traversal attempt detected: {file_path}"
                else:
                    return False, f"Absolute path not allowed: {file_path}"
            
            # Check for dangerous characters
            dangerous_chars = ['<', '>', '|', '&', ';', '`', '$', '(', ')', '{', '}']
            if any(char in normalized_path for char in dangerous_chars):
                return False, f"Dangerous characters in path: {file_path}"
            
            # Check file extension
            _, ext = os.path.splitext(normalized_path)
            if ext.lower() in self.DANGEROUS_EXTENSIONS:
                return False, f"Dangerous file extension: {ext}"
            
            return True, ""
            
        except Exception as e:
            return False, f"Path validation error: {str(e)}"
    
    def validate_file_size(self, file_path: Union[str, os.PathLike], max_size: int = None) -> Tuple[bool, str]:
        """
        Validate file size.
        
        Args:
            file_path: Path to file
            max_size: Maximum allowed size (default: MAX_FILE_SIZE)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not os.path.exists(file_path):
                return False, "File does not exist"
            
            file_size = os.path.getsize(file_path)
            max_allowed = max_size or self.MAX_FILE_SIZE
            
            if file_size > max_allowed:
                return False, f"File too large: {file_size} bytes (max: {max_allowed})"
            
            return True, ""
            
        except Exception as e:
            return False, f"Size validation error: {str(e)}"
    
    def validate_content_security(self, content: str, content_type: str = "file") -> Tuple[bool, str]:
        """
        Validate content for security issues.
        
        Args:
            content: Content to validate
            content_type: Type of content ("file", "template", "prompt")
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check content length
            max_length = self.MAX_TEMPLATE_SIZE if content_type == "template" else self.MAX_CONTENT_LENGTH
            if len(content) > max_length:
                return False, f"Content too long: {len(content)} characters (max: {max_length})"
            
            # Check for dangerous patterns
            for pattern in self.DANGEROUS_PATTERNS:
                if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                    return False, f"Dangerous pattern detected: {pattern}"
            
            # Check for suspicious imports
            suspicious_imports = ['subprocess', 'os.system', 'eval', 'exec', 'compile', '__import__']
            for suspicious in suspicious_imports:
                if suspicious in content:
                    return False, f"Suspicious import/function detected: {suspicious}"
            
            # Check for file system operations
            fs_operations = ['open(', 'file(', 'with open(']
            for operation in fs_operations:
                if operation in content:
                    return False, f"File system operation detected: {operation}"
            
            return True, ""
            
        except Exception as e:
            return False, f"Content validation error: {str(e)}"
    
    def validate_template_file(self, file_path: Union[str, os.PathLike]) -> Tuple[bool, str]:
        """
        Validate template file for security.
        
        Args:
            file_path: Path to template file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check file extension
            _, ext = os.path.splitext(file_path)
            if ext.lower() not in self.ALLOWED_TEMPLATE_EXTENSIONS:
                return False, f"Unsupported template extension: {ext}"
            
            # Validate path
            is_valid, error = self.validate_file_path(file_path)
            if not is_valid:
                return False, error
            
            # Validate file size
            is_valid, error = self.validate_file_size(file_path, self.MAX_TEMPLATE_SIZE)
            if not is_valid:
                return False, error
            
            # Read and validate content
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                is_valid, error = self.validate_content_security(content, "template")
                if not is_valid:
                    return False, error
                
            except Exception as e:
                return False, f"Template content validation error: {str(e)}"
            
            return True, ""
            
        except Exception as e:
            return False, f"Template validation error: {str(e)}"
    
    def sanitize_content(self, content: str) -> str:
        """
        Sanitize content by removing dangerous patterns.
        
        Args:
            content: Content to sanitize
            
        Returns:
            Sanitized content
        """
        try:
            # Remove dangerous patterns
            sanitized = content
            for pattern in self.DANGEROUS_PATTERNS:
                sanitized = re.sub(pattern, '[REMOVED]', sanitized, flags=re.IGNORECASE | re.DOTALL)
            
            # Remove suspicious imports
            suspicious_lines = []
            for line in sanitized.split('\n'):
                if any(suspicious in line for suspicious in ['subprocess', 'os.system', 'eval', 'exec']):
                    suspicious_lines.append(line)
                    sanitized = sanitized.replace(line, '[REMOVED SUSPICIOUS LINE]')
            
            if suspicious_lines and self.logger:
                self.logger.warning(f"Removed {len(suspicious_lines)} suspicious lines from content")
            
            return sanitized
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Content sanitization error: {e}")
            return content
    
    def validate_repository_access(self, repo_path: Union[str, os.PathLike]) -> Tuple[bool, str]:
        """
        Validate repository access for security.
        
        Args:
            repo_path: Path to repository
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            normalized_path = normalize_path(repo_path)
            user_home = normalize_path(os.path.expanduser("~"))
            
            # Ensure repository is within user's home directory
            if not is_path_within_base(normalized_path, user_home):
                return False, f"Repository outside user directory: {repo_path}"
            
            # Check for dangerous repository names
            dangerous_names = ['.git', '.svn', '.hg', 'node_modules', '__pycache__']
            repo_name = os.path.basename(normalized_path)
            if repo_name.lower() in dangerous_names:
                return False, f"Dangerous repository name: {repo_name}"
            
            # Check if path exists and is a directory
            if not os.path.exists(normalized_path):
                return False, f"Repository does not exist: {repo_path}"
            
            if not os.path.isdir(normalized_path):
                return False, f"Repository is not a directory: {repo_path}"
            
            return True, ""
            
        except Exception as e:
            return False, f"Repository validation error: {str(e)}"
    
    def validate_file_list(self, file_paths: List[str], base_path: Union[str, os.PathLike] = None) -> Tuple[List[str], List[str]]:
        """
        Validate a list of file paths for security.
        
        Args:
            file_paths: List of file paths to validate
            base_path: Base directory for validation
            
        Returns:
            Tuple of (valid_paths, invalid_paths_with_errors)
        """
        valid_paths = []
        invalid_paths = []
        
        for file_path in file_paths:
            is_valid, error = self.validate_file_path(file_path, base_path)
            if is_valid:
                valid_paths.append(file_path)
            else:
                invalid_paths.append(f"{file_path}: {error}")
        
        return valid_paths, invalid_paths

# Global security validator instance
_security_validator = None

def get_security_validator() -> SecurityValidator:
    """Get the global security validator instance."""
    global _security_validator
    if _security_validator is None:
        _security_validator = SecurityValidator()
    return _security_validator

def validate_file_path(file_path: Union[str, os.PathLike], base_path: Union[str, os.PathLike] = None) -> Tuple[bool, str]:
    """Convenience function to validate file path."""
    return get_security_validator().validate_file_path(file_path, base_path)

def validate_content_security(content: str, content_type: str = "file") -> Tuple[bool, str]:
    """Convenience function to validate content security."""
    return get_security_validator().validate_content_security(content, content_type)

def validate_template_file(file_path: Union[str, os.PathLike]) -> Tuple[bool, str]:
    """Convenience function to validate template file."""
    return get_security_validator().validate_template_file(file_path)

def validate_file_size(file_path: Union[str, os.PathLike], max_size: int = None) -> Tuple[bool, str]:
    """Convenience function to validate file size."""
    return get_security_validator().validate_file_size(file_path, max_size)

def sanitize_content(content: str) -> str:
    """Convenience function to sanitize content."""
    return get_security_validator().sanitize_content(content)
