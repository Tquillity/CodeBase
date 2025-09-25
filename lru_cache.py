# lru_cache.py
# Thread-safe LRU cache implementation for content storage

import threading
from collections import OrderedDict
import logging

class ThreadSafeLRUCache:
    """
    Thread-safe LRU cache with size limits and automatic eviction.
    """
    
    def __init__(self, max_size=1000, max_memory_mb=100):
        """
        Initialize the cache.
        
        Args:
            max_size: Maximum number of items to store
            max_memory_mb: Maximum memory usage in MB (approximate)
        """
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache = OrderedDict()
        self.lock = threading.RLock()  # Reentrant lock for nested calls
        self.current_memory_bytes = 0
        
    def get(self, key):
        """
        Get an item from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                value = self.cache.pop(key)
                self.cache[key] = value
                return value
            return None
    
    def put(self, key, value):
        """
        Add or update an item in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        with self.lock:
            # Calculate memory usage of the new item
            item_memory = self._estimate_memory_usage(key, value)
            
            # Remove existing item if present
            if key in self.cache:
                old_value = self.cache.pop(key)
                self.current_memory_bytes -= self._estimate_memory_usage(key, old_value)
            
            # Add new item
            self.cache[key] = value
            self.current_memory_bytes += item_memory
            
            # Evict items if necessary
            self._evict_if_needed()
    
    def _estimate_memory_usage(self, key, value):
        """
        Estimate memory usage of a cache item.
        
        Args:
            key: Cache key
            value: Cached value
            
        Returns:
            Estimated memory usage in bytes
        """
        try:
            # Rough estimation: key size + value size + overhead
            key_size = len(str(key).encode('utf-8'))
            value_size = len(str(value).encode('utf-8'))
            return key_size + value_size + 100  # 100 bytes overhead
        except:
            # Fallback estimation
            return 1000
    
    def _evict_if_needed(self):
        """
        Evict items if cache exceeds size or memory limits.
        """
        # Evict by size limit
        while len(self.cache) > self.max_size:
            self._evict_oldest()
        
        # Evict by memory limit
        while (self.current_memory_bytes > self.max_memory_bytes and 
               len(self.cache) > 0):
            self._evict_oldest()
    
    def _evict_oldest(self):
        """
        Remove the least recently used item.
        """
        if self.cache:
            key, value = self.cache.popitem(last=False)  # Remove first (oldest)
            self.current_memory_bytes -= self._estimate_memory_usage(key, value)
            logging.debug(f"Evicted cache item: {key}")
    
    def clear(self):
        """
        Clear all items from the cache.
        """
        with self.lock:
            self.cache.clear()
            self.current_memory_bytes = 0
    
    def size(self):
        """
        Get current cache size.
        
        Returns:
            Number of items in cache
        """
        with self.lock:
            return len(self.cache)
    
    def memory_usage_mb(self):
        """
        Get current memory usage.
        
        Returns:
            Memory usage in MB
        """
        with self.lock:
            return self.current_memory_bytes / (1024 * 1024)
    
    def stats(self):
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self.lock:
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'memory_mb': self.memory_usage_mb(),
                'max_memory_mb': self.max_memory_bytes / (1024 * 1024)
            }
