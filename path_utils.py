# path_utils.py
# Centralized path normalization utilities for Linux-exclusive environment
from __future__ import annotations

import os
import logging
from typing import Optional, Union

def normalize_path(path: Union[str, os.PathLike[str]]) -> str:
    """
    Normalize a file path for Linux.
    
    Args:
        path: File path to normalize
        
    Returns:
        Normalized path string
    """
    if not path:
        return ""
    
    # Use normpath to resolve .. and . components
    return os.path.normpath(str(path))

def normalize_for_cache(path: Union[str, os.PathLike[str]]) -> str:
    """
    Normalize a path specifically for cache keys.
    
    Args:
        path: File path to normalize for caching
        
    Returns:
        Normalized path string for cache keys
    """
    if not path:
        return ""
    
    return os.path.normpath(str(path))

def safe_join(
    base_path: Union[str, os.PathLike[str]],
    *paths: Union[str, os.PathLike[str]],
) -> str:
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
    
    # Start with base path
    result = str(base_path)
    
    # Join additional paths
    for path in paths:
        if path:
            result = os.path.join(result, str(path))
    
    return normalize_path(result)

def get_relative_path(
    file_path: Union[str, os.PathLike[str]],
    base_path: Union[str, os.PathLike[str]],
) -> Optional[str]:
    """
    Get relative path from base to file.
    
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
    except (ValueError, OSError) as e:
        logging.warning(f"Could not get relative path from {base_path} to {file_path}: {e}")
        return None

def is_path_within_base(
    file_path: Union[str, os.PathLike[str]],
    base_path: Union[str, os.PathLike[str]],
) -> bool:
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

def ensure_absolute_path(
    path: Union[str, os.PathLike[str]],
    base_path: Optional[Union[str, os.PathLike[str]]] = None,
) -> str:
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

def get_path_components(path: Union[str, os.PathLike[str]]) -> list[str]:
    """
    Get path components as a list.
    
    Args:
        path: File path
        
    Returns:
        List of path components
    """
    if not path:
        return []
    
    normalized = normalize_path(path)
    return normalized.split('/')

def is_same_path(
    path1: Union[str, os.PathLike[str]],
    path2: Union[str, os.PathLike[str]],
) -> bool:
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
