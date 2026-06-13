# path_utils.py
# Centralized path normalization utilities (cross-platform: Linux + Windows).
#
# Canonical internal forms:
#   * normalize_path      -> forward-slash separators, ORIGINAL case
#                            (display, gitignore matching, path building).
#                            Forward slashes are accepted by all Win32 file APIs,
#                            so these paths remain valid for open()/exists().
#   * normalize_for_cache -> os.path.normcase(normpath): OS-native separators,
#                            case-folded on Windows (NTFS is case-insensitive),
#                            a no-op on POSIX. Use for cache keys and any
#                            case-insensitive path comparison.
from __future__ import annotations

import os
import logging
from typing import Optional, Union

def normalize_path(path: Union[str, os.PathLike[str]]) -> str:
    """
    Normalize a file path to the canonical internal form: resolved
    (``..``/``.`` collapsed) with forward-slash separators on every platform.

    Args:
        path: File path to normalize

    Returns:
        Normalized path string (forward-slash separators, original case)
    """
    if not path:
        return ""

    # Use normpath to resolve .. and . components, then canonicalize the
    # separator to '/' so internal paths are platform-independent. On POSIX
    # os.sep is already '/', so the replace is a no-op.
    return os.path.normpath(str(path)).replace(os.sep, "/")

def normalize_for_cache(path: Union[str, os.PathLike[str]]) -> str:
    """
    Normalize a path specifically for cache keys / case-insensitive comparison.

    Applies ``os.path.normcase`` so that on case-insensitive filesystems
    (Windows/NTFS) paths differing only in case map to the same key. On POSIX
    ``normcase`` is the identity function, so behaviour is unchanged there.

    Args:
        path: File path to normalize for caching

    Returns:
        Normalized cache-key string (OS-native separators, case-folded on Windows)
    """
    if not path:
        return ""

    return os.path.normcase(os.path.normpath(str(path)))

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
        # relpath re-introduces the OS separator; canonicalize back to '/'
        # so the result stays in the forward-slash internal form.
        return os.path.relpath(file_norm, base_norm).replace(os.sep, "/")
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
        # Compare in case-folded, OS-native form so the check is correct on
        # case-insensitive Windows filesystems and never raises across drives
        # (os.path.commonpath raises ValueError for paths on different drives).
        file_norm = os.path.normcase(os.path.normpath(str(file_path)))
        base_norm = os.path.normcase(os.path.normpath(str(base_path)))

        # Different drive/volume => never within base (no-op on POSIX, where
        # splitdrive returns an empty drive for every path).
        if os.path.splitdrive(file_norm)[0] != os.path.splitdrive(base_norm)[0]:
            return False

        if file_norm == base_norm:
            return True

        # Append the separator so '/base' does not match '/baseball'.
        return file_norm.startswith(base_norm.rstrip(os.sep) + os.sep)
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

    # Use the cache form so the comparison is case-insensitive on Windows
    # (no-op on POSIX) — two paths differing only in case are the same file.
    return normalize_for_cache(path1) == normalize_for_cache(path2)
