# path_utils.py
# Centralized path normalization utilities for cross-platform compatibility

import os
import logging
from typing import Union, Optional

def normalize_path(path: Union[str, os.PathLike]) -> str:
    """
    Normalize a file path for consistent cross-platform handling.
    
    Args:
        path: File path to normalize
        
    Returns:
        Normalized path string
    """
    if not path:
        return ""
    
    # Convert to string and normalize
    path_str = str(path)
    
    # Use normpath to resolve .. and . components
    normalized = os.path.normpath(path_str)
    
    # Use normcase for case-insensitive filesystems (Windows)
    return os.path.normcase(normalized)

def normalize_for_cache(path: Union[str, os.PathLike]) -> str:
    """
    Normalize a path specifically for cache keys.
    Uses normcase for consistent cache lookups across platforms.
    
    Args:
        path: File path to normalize for caching
        
    Returns:
        Normalized path string for cache keys
    """
    if not path:
        return ""
    
    return os.path.normcase(str(path))

def safe_join(base_path: Union[str, os.PathLike], *paths: Union[str, os.PathLike]) -> str:
    """
    Safely join paths with proper normalization.
    
    Args:
        base_path: Base directory path
        *paths: Additional path components
        
    Returns:
        Normalized joined path
    """
    if not base_path:
        return ""
    
    # Start with normalized base path
    result = normalize_path(base_path)
    
    # Join additional paths
    for path in paths:
        if path:
            result = os.path.join(result, str(path))
    
    return normalize_path(result)

def get_relative_path(file_path: Union[str, os.PathLike], base_path: Union[str, os.PathLike]) -> Optional[str]:
    """
    Get relative path from base to file, with proper error handling.
    
    Args:
        file_path: Target file path
        base_path: Base directory path
        
    Returns:
        Relative path string or None if error
    """
    try:
        file_norm = normalize_path(file_path)
        base_norm = normalize_path(base_path)
        return os.path.relpath(file_norm, base_norm)
    except ValueError as e:
        logging.warning(f"Could not get relative path from {base_path} to {file_path}: {e}")
        return None

def is_path_within_base(file_path: Union[str, os.PathLike], base_path: Union[str, os.PathLike]) -> bool:
    """
    Check if a file path is within a base directory (security check).
    
    Args:
        file_path: File path to check
        base_path: Base directory path
        
    Returns:
        True if file is within base directory
    """
    try:
        file_norm = normalize_path(file_path)
        base_norm = normalize_path(base_path)
        
        # Get common path
        common_path = os.path.commonpath([file_norm, base_norm])
        return common_path == base_norm
    except (ValueError, OSError):
        return False

def ensure_absolute_path(path: Union[str, os.PathLike], base_path: Optional[Union[str, os.PathLike]] = None) -> str:
    """
    Ensure a path is absolute, using base_path if provided for relative paths.
    
    Args:
        path: Path to make absolute
        base_path: Base directory for relative paths (optional)
        
    Returns:
        Absolute normalized path
    """
    if not path:
        return ""
    
    path_str = str(path)
    
    if os.path.isabs(path_str):
        return normalize_path(path_str)
    elif base_path:
        return normalize_path(os.path.join(base_path, path_str))
    else:
        return normalize_path(os.path.abspath(path_str))

def get_path_components(path: Union[str, os.PathLike]) -> list:
    """
    Get path components as a list, normalized for cross-platform use.
    
    Args:
        path: File path
        
    Returns:
        List of path components
    """
    if not path:
        return []
    
    normalized = normalize_path(path)
    return normalized.replace('\\', '/').split('/')

def is_same_path(path1: Union[str, os.PathLike], path2: Union[str, os.PathLike]) -> bool:
    """
    Check if two paths refer to the same file/directory.
    
    Args:
        path1: First path
        path2: Second path
        
    Returns:
        True if paths are the same
    """
    if not path1 or not path2:
        return path1 == path2
    
    return normalize_path(path1) == normalize_path(path2)
