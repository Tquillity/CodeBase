# lru_cache.py
# Thread-safe LRU cache implementation for content storage
from __future__ import annotations

import logging
import sys
import threading
from collections import OrderedDict
from typing import Any, Optional

from constants import CACHE_OVERHEAD_BYTES


class ThreadSafeLRUCache:
    """
    Thread-safe LRU cache with size limits and automatic eviction.
    """

    def __init__(
        self, max_size: int = 1000, max_memory_mb: int = 100
    ) -> None:
        """
        Initialize the cache.

        Args:
            max_size: Maximum number of items to store
            max_memory_mb: Maximum memory usage in MB (approximate)
        """
        self.max_size: int = max_size
        self.max_memory_bytes: int = max_memory_mb * 1024 * 1024
        self.cache: OrderedDict[str, Any] = OrderedDict()
        self.lock: threading.RLock = threading.RLock()
        self.current_memory_bytes: int = 0

    def get(self, key: str) -> Optional[Any]:
        """
        Get an item from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        with self.lock:
            if key in self.cache:
                value = self.cache.pop(key)
                self.cache[key] = value
                return value
            return None

    def put(self, key: str, value: Any) -> None:
        """
        Add or update an item in the cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        with self.lock:
            item_memory = self._estimate_memory_usage(key, value)
            if key in self.cache:
                old_value = self.cache.pop(key)
                self.current_memory_bytes -= self._estimate_memory_usage(
                    key, old_value
                )
            self.cache[key] = value
            self.current_memory_bytes += item_memory
            self._evict_if_needed()

    def _estimate_memory_usage(self, key: str, value: Any) -> int:
        """Estimate memory usage of a cache item in bytes."""
        return (
            sys.getsizeof(key)
            + sys.getsizeof(value)
            + CACHE_OVERHEAD_BYTES
        )

    def _evict_if_needed(self) -> None:
        """Evict items if cache exceeds size or memory limits."""
        while len(self.cache) > self.max_size:
            self._evict_oldest()
        while (
            self.current_memory_bytes > self.max_memory_bytes
            and len(self.cache) > 0
        ):
            self._evict_oldest()

    def _evict_oldest(self) -> None:
        """Remove the least recently used item."""
        if self.cache:
            key, value = self.cache.popitem(last=False)
            self.current_memory_bytes -= self._estimate_memory_usage(
                key, value
            )
            logging.debug(f"Evicted cache item: {key}")

    def clear(self) -> None:
        """Clear all items from the cache."""
        with self.lock:
            self.cache.clear()
            self.current_memory_bytes = 0

    def size(self) -> int:
        """Get current cache size (number of items)."""
        with self.lock:
            return len(self.cache)

    def memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        with self.lock:
            return self.current_memory_bytes / (1024 * 1024)

    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "memory_mb": self.memory_usage_mb(),
                "max_memory_mb": self.max_memory_bytes / (1024 * 1024),
            }
