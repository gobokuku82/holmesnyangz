"""
Caching system for supervisor and agents
Provides both simple and advanced caching capabilities
"""

from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import hashlib
import json
import logging
from enum import Enum
import asyncio
from functools import wraps

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Cache eviction strategies"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live only
    FIFO = "fifo"  # First In First Out


@dataclass
class CacheEntry:
    """Individual cache entry with metadata"""
    key: str
    data: Any
    timestamp: datetime
    ttl: timedelta
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    size_bytes: int = 0
    
    def is_expired(self) -> bool:
        """Check if entry has expired"""
        return datetime.now() - self.timestamp > self.ttl
    
    def access(self):
        """Update access metadata"""
        self.access_count += 1
        self.last_accessed = datetime.now()


class CacheManager:
    """
    Advanced caching system with multiple strategies
    Supports TTL, size limits, and different eviction policies
    """
    
    def __init__(
        self,
        ttl_seconds: int = 1800,
        max_size: int = 1000,
        max_memory_mb: float = 100,
        strategy: CacheStrategy = CacheStrategy.LRU
    ):
        """
        Initialize cache manager
        
        Args:
            ttl_seconds: Default time-to-live in seconds
            max_size: Maximum number of entries
            max_memory_mb: Maximum memory usage in MB
            strategy: Cache eviction strategy
        """
        self._cache: Dict[str, CacheEntry] = {}
        self.default_ttl = timedelta(seconds=ttl_seconds)
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.strategy = strategy
        self.hits = 0
        self.misses = 0
        self._lock = asyncio.Lock()
        
        logger.info(
            f"CacheManager initialized: "
            f"ttl={ttl_seconds}s, max_size={max_size}, "
            f"max_memory={max_memory_mb}MB, strategy={strategy.value}"
        )
    
    def _generate_key(self, identifier: str, **params) -> str:
        """
        Generate cache key from identifier and parameters
        
        Args:
            identifier: Main identifier (e.g., query)
            **params: Additional parameters
        
        Returns:
            Cache key hash
        """
        # Sort params for consistent key generation
        param_str = json.dumps(params, sort_keys=True, ensure_ascii=False)
        combined = f"{identifier}:{param_str}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def _estimate_size(self, data: Any) -> int:
        """Estimate size of data in bytes"""
        try:
            return len(json.dumps(data).encode())
        except:
            # Fallback for non-JSON serializable objects
            return len(str(data).encode())
    
    def _evict_if_needed(self):
        """Evict entries based on strategy if cache is full"""
        # Check size limit
        if len(self._cache) >= self.max_size:
            self._evict_by_strategy()
        
        # Check memory limit
        total_memory = sum(entry.size_bytes for entry in self._cache.values())
        while total_memory > self.max_memory_bytes and self._cache:
            self._evict_by_strategy()
            total_memory = sum(entry.size_bytes for entry in self._cache.values())
    
    def _evict_by_strategy(self):
        """Evict one entry based on configured strategy"""
        if not self._cache:
            return
        
        if self.strategy == CacheStrategy.LRU:
            # Remove least recently used
            victim = min(self._cache.values(), key=lambda e: e.last_accessed)
        elif self.strategy == CacheStrategy.LFU:
            # Remove least frequently used
            victim = min(self._cache.values(), key=lambda e: e.access_count)
        elif self.strategy == CacheStrategy.FIFO:
            # Remove oldest entry
            victim = min(self._cache.values(), key=lambda e: e.timestamp)
        else:  # TTL only
            # Remove expired or oldest
            expired = [e for e in self._cache.values() if e.is_expired()]
            victim = expired[0] if expired else min(self._cache.values(), key=lambda e: e.timestamp)
        
        del self._cache[victim.key]
        logger.debug(f"Evicted cache entry: {victim.key[:8]}...")
    
    async def get(
        self,
        identifier: str,
        **params
    ) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            identifier: Main identifier
            **params: Additional parameters
        
        Returns:
            Cached value or None
        """
        key = self._generate_key(identifier, **params)
        
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                
                # Check expiration
                if entry.is_expired():
                    del self._cache[key]
                    self.misses += 1
                    logger.debug(f"Cache miss (expired): {key[:8]}...")
                    return None
                
                # Update access metadata
                entry.access()
                self.hits += 1
                
                logger.debug(
                    f"Cache hit: {key[:8]}... "
                    f"(access_count={entry.access_count})"
                )
                return entry.data
            
            self.misses += 1
            logger.debug(f"Cache miss: {key[:8]}...")
            return None
    
    async def set(
        self,
        identifier: str,
        data: Any,
        ttl_seconds: Optional[int] = None,
        **params
    ):
        """
        Store value in cache
        
        Args:
            identifier: Main identifier
            data: Data to cache
            ttl_seconds: Optional TTL override
            **params: Additional parameters
        """
        key = self._generate_key(identifier, **params)
        ttl = timedelta(seconds=ttl_seconds) if ttl_seconds else self.default_ttl
        
        async with self._lock:
            # Check if we need to evict
            self._evict_if_needed()
            
            # Create and store entry
            entry = CacheEntry(
                key=key,
                data=data,
                timestamp=datetime.now(),
                ttl=ttl,
                size_bytes=self._estimate_size(data)
            )
            
            self._cache[key] = entry
            logger.debug(f"Cached: {key[:8]}... (size={entry.size_bytes} bytes)")
    
    async def invalidate(self, identifier: str, **params):
        """
        Invalidate specific cache entry
        
        Args:
            identifier: Main identifier
            **params: Additional parameters
        """
        key = self._generate_key(identifier, **params)
        
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Invalidated: {key[:8]}...")
    
    async def invalidate_pattern(self, pattern: str):
        """
        Invalidate all entries matching a pattern
        
        Args:
            pattern: Pattern to match in identifiers
        """
        async with self._lock:
            keys_to_remove = [
                key for key, entry in self._cache.items()
                if pattern in str(entry.data)
            ]
            
            for key in keys_to_remove:
                del self._cache[key]
            
            if keys_to_remove:
                logger.info(f"Invalidated {len(keys_to_remove)} entries matching pattern: {pattern}")
    
    async def clear(self):
        """Clear all cache entries"""
        async with self._lock:
            size = len(self._cache)
            self._cache.clear()
            logger.info(f"Cleared {size} cache entries")
    
    async def cleanup_expired(self) -> int:
        """
        Remove all expired entries
        
        Returns:
            Number of entries removed
        """
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired entries")
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache stats
        """
        total_entries = len(self._cache)
        total_memory = sum(entry.size_bytes for entry in self._cache.values())
        hit_rate = self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0
        
        # Get age distribution
        now = datetime.now()
        ages = [(now - entry.timestamp).total_seconds() for entry in self._cache.values()]
        
        stats = {
            "total_entries": total_entries,
            "total_memory_mb": total_memory / (1024 * 1024),
            "max_memory_mb": self.max_memory_bytes / (1024 * 1024),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "strategy": self.strategy.value,
            "oldest_entry_seconds": max(ages) if ages else 0,
            "newest_entry_seconds": min(ages) if ages else 0,
            "average_age_seconds": sum(ages) / len(ages) if ages else 0
        }
        
        return stats
    
    async def get_or_compute(
        self,
        identifier: str,
        compute_func: Callable,
        ttl_seconds: Optional[int] = None,
        **params
    ) -> Any:
        """
        Get from cache or compute if not present
        
        Args:
            identifier: Main identifier
            compute_func: Async function to compute value if not cached
            ttl_seconds: Optional TTL override
            **params: Additional parameters
        
        Returns:
            Cached or computed value
        """
        # Try to get from cache
        result = await self.get(identifier, **params)
        if result is not None:
            return result
        
        # Compute value
        result = await compute_func()
        
        # Store in cache
        await self.set(identifier, result, ttl_seconds, **params)
        
        return result


class QueryCache:
    """
    Specialized cache for query results
    Handles query normalization and similarity matching
    """
    
    def __init__(self, cache_manager: Optional[CacheManager] = None):
        """
        Initialize query cache
        
        Args:
            cache_manager: Optional CacheManager instance
        """
        self.cache = cache_manager or CacheManager(
            ttl_seconds=1800,  # 30 minutes
            max_size=500,
            strategy=CacheStrategy.LRU
        )
        self.query_variations: Dict[str, List[str]] = {}
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for better matching"""
        # Remove extra whitespace
        normalized = " ".join(query.split())
        # Convert to lowercase for comparison
        normalized = normalized.lower()
        # Remove common punctuation at the end
        normalized = normalized.rstrip("?!.")
        return normalized
    
    async def get_cached_result(
        self,
        query: str,
        user_id: str,
        **context
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached result for a query
        
        Args:
            query: User query
            user_id: User identifier
            **context: Additional context
        
        Returns:
            Cached result or None
        """
        normalized_query = self._normalize_query(query)
        return await self.cache.get(
            normalized_query,
            user_id=user_id,
            **context
        )
    
    async def cache_result(
        self,
        query: str,
        result: Dict[str, Any],
        user_id: str,
        ttl_seconds: Optional[int] = None,
        **context
    ):
        """
        Cache a query result
        
        Args:
            query: User query
            result: Result to cache
            user_id: User identifier
            ttl_seconds: Optional TTL override
            **context: Additional context
        """
        normalized_query = self._normalize_query(query)
        await self.cache.set(
            normalized_query,
            result,
            ttl_seconds,
            user_id=user_id,
            **context
        )
    
    async def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a user"""
        await self.cache.invalidate_pattern(f"user_id:{user_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache.get_stats()


def cached_result(
    ttl_seconds: Optional[int] = None,
    key_params: Optional[List[str]] = None
):
    """
    Decorator for caching async function results
    
    Args:
        ttl_seconds: TTL for cached results
        key_params: List of parameter names to include in cache key
    
    Usage:
        @cached_result(ttl_seconds=300, key_params=["region", "property_type"])
        async def search_properties(region, property_type, **kwargs):
            # ... expensive search operation ...
            return results
    """
    def decorator(func: Callable) -> Callable:
        # Create a cache instance for this function
        cache = CacheManager(ttl_seconds=ttl_seconds or 1800, max_size=100)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            cache_params = {}
            if key_params:
                cache_params = {k: kwargs.get(k) for k in key_params if k in kwargs}
            
            # Try to get from cache
            identifier = f"{func.__module__}.{func.__name__}"
            result = await cache.get(identifier, **cache_params)
            
            if result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return result
            
            # Compute result
            result = await func(*args, **kwargs)
            
            # Store in cache
            await cache.set(identifier, result, ttl_seconds, **cache_params)
            
            return result
        
        # Attach cache instance for management
        wrapper.cache = cache
        return wrapper
    
    return decorator
