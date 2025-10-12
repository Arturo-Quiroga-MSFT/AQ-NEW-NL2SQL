"""
conversation_store.py - Redis-based Conversation History Storage
==================================================================

Provides persistent, multi-instance conversation memory for the Teams bot.

Features:
- Persistent storage (survives container restarts)
- Multi-instance support (works across multiple container replicas)
- Automatic expiration (TTL for conversation history)
- Connection pooling for performance
- Fallback to in-memory if Redis unavailable
"""

import os
import json
import redis
from typing import Dict, Any, Optional
from datetime import timedelta


class RedisConversationStore:
    """
    Redis-based conversation history store with fallback to in-memory dict.
    """
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 6380,
        password: Optional[str] = None,
        ssl: bool = True,
        ttl_days: int = 7,
        use_fallback: bool = True
    ):
        """
        Initialize Redis conversation store.
        
        Args:
            host: Redis hostname (reads from REDIS_HOST env if not provided)
            port: Redis port (default: 6380 for Azure Cache)
            password: Redis password (reads from REDIS_PASSWORD env if not provided)
            ssl: Use SSL connection (default: True for Azure)
            ttl_days: Days to keep conversation history (default: 7)
            use_fallback: Use in-memory dict if Redis unavailable (default: True)
        """
        self.host = host or os.getenv("REDIS_HOST")
        self.port = port
        self.password = password or os.getenv("REDIS_PASSWORD")
        self.ssl = ssl
        self.ttl = timedelta(days=ttl_days)
        self.use_fallback = use_fallback
        
        # In-memory fallback
        self._fallback_store: Dict[str, Dict[str, Any]] = {}
        self._using_fallback = False
        
        # Redis connection pool
        self._redis_client: Optional[redis.Redis] = None
        
        # Initialize connection
        self._init_connection()
    
    def _init_connection(self):
        """Initialize Redis connection with error handling."""
        if not self.host:
            print("[WARN] Redis host not configured. Using in-memory fallback.")
            self._using_fallback = True
            return
        
        try:
            # Create connection pool
            pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                password=self.password,
                ssl=self.ssl,
                ssl_cert_reqs=None if self.ssl else 'none',
                decode_responses=True,  # Auto-decode to strings
                max_connections=10,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Create Redis client
            self._redis_client = redis.Redis(connection_pool=pool)
            
            # Test connection
            self._redis_client.ping()
            print(f"[INFO] Connected to Redis at {self.host}:{self.port}")
            self._using_fallback = False
            
        except Exception as e:
            print(f"[ERROR] Failed to connect to Redis: {e}")
            if self.use_fallback:
                print("[WARN] Using in-memory fallback store.")
                self._using_fallback = True
            else:
                raise
    
    def _get_key(self, conversation_id: str) -> str:
        """Generate Redis key for conversation ID."""
        return f"conversation:{conversation_id}"
    
    def get_history(self, conversation_id: str) -> Dict[str, Any]:
        """
        Get conversation history for a conversation ID.
        
        Args:
            conversation_id: Teams conversation ID
            
        Returns:
            Dict with 'last_query', 'last_sql', 'last_results' or empty dict
        """
        # Fallback mode
        if self._using_fallback:
            return self._fallback_store.get(conversation_id, {})
        
        # Redis mode
        try:
            key = self._get_key(conversation_id)
            data = self._redis_client.get(key)
            
            if data:
                return json.loads(data)
            return {}
            
        except Exception as e:
            print(f"[ERROR] Failed to get history from Redis: {e}")
            if self.use_fallback:
                return self._fallback_store.get(conversation_id, {})
            return {}
    
    def save_history(
        self,
        conversation_id: str,
        last_query: str,
        last_sql: str,
        last_results: Dict[str, Any]
    ) -> bool:
        """
        Save conversation history.
        
        Args:
            conversation_id: Teams conversation ID
            last_query: User's last question
            last_sql: Generated SQL query
            last_results: Query execution results
            
        Returns:
            True if saved successfully, False otherwise
        """
        data = {
            "last_query": last_query,
            "last_sql": last_sql,
            "last_results": last_results
        }
        
        # Fallback mode
        if self._using_fallback:
            self._fallback_store[conversation_id] = data
            return True
        
        # Redis mode
        try:
            key = self._get_key(conversation_id)
            json_data = json.dumps(data)
            
            # Save with TTL (expires after N days)
            self._redis_client.setex(
                name=key,
                time=self.ttl,
                value=json_data
            )
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to save history to Redis: {e}")
            if self.use_fallback:
                self._fallback_store[conversation_id] = data
            return False
    
    def clear_history(self, conversation_id: str) -> bool:
        """
        Clear conversation history for a conversation ID.
        
        Args:
            conversation_id: Teams conversation ID
            
        Returns:
            True if cleared successfully, False otherwise
        """
        # Fallback mode
        if self._using_fallback:
            self._fallback_store.pop(conversation_id, None)
            return True
        
        # Redis mode
        try:
            key = self._get_key(conversation_id)
            self._redis_client.delete(key)
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to clear history from Redis: {e}")
            if self.use_fallback:
                self._fallback_store.pop(conversation_id, None)
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check Redis connection health.
        
        Returns:
            Dict with 'connected', 'using_fallback', 'host', 'port'
        """
        if self._using_fallback:
            return {
                "connected": False,
                "using_fallback": True,
                "host": self.host or "not configured",
                "port": self.port
            }
        
        try:
            self._redis_client.ping()
            return {
                "connected": True,
                "using_fallback": False,
                "host": self.host,
                "port": self.port
            }
        except Exception as e:
            return {
                "connected": False,
                "using_fallback": self.use_fallback,
                "host": self.host,
                "port": self.port,
                "error": str(e)
            }
    
    def close(self):
        """Close Redis connection."""
        if self._redis_client:
            try:
                self._redis_client.close()
                print("[INFO] Closed Redis connection.")
            except Exception as e:
                print(f"[ERROR] Error closing Redis connection: {e}")
