"""
Key Manager for LLM API services.
Handles loading, rotation, and tracking of API keys.
"""
from __future__ import annotations

import os
import time
import random
from typing import List, Dict
from dotenv import load_dotenv
from loguru import logger

class LLMKeyManager:
    """
    Manages API keys for a specific LLM provider with rotation capabilities.
    Each instance is tied to a single provider.
    """
    
    def __init__(self, env_prefix: str, load_env: bool = True):
        """
        Initialize the key manager for a specific provider.
        
        Args:
            env_prefix: The environment variable prefix for this provider's API keys
                        (e.g., "GEMINI_API_KEY" or "OPENAI_API_KEY")
            load_env: Whether to automatically load the .env file
        """
        if load_env:
            load_dotenv()
            
        self.env_prefix = env_prefix
        self.keys = self._load_keys_from_env()
        self.key_usage_count = {key: 0 for key in self.keys}
        self.last_used_time = {key: 0 for key in self.keys}
        self.rate_limited_until = {key: 0 for key in self.keys}  # Timestamp when rate limit expires
        
        if not self.keys:
            raise ValueError(f"No API keys found with prefix '{env_prefix}' in environment variables")
            
        logger.info(f"Loaded {len(self.keys)} API keys for prefix '{env_prefix}'")
    
    def _load_keys_from_env(self) -> List[str]:
        """Load all API keys from environment variables with the configured prefix."""
        keys = []
        i = 1
        
        # Try to load sequentially numbered keys (PREFIX_1, PREFIX_2, etc.)
        while True:
            key = os.getenv(f"{self.env_prefix}_{i}")
            if key:
                keys.append(key)
                i += 1
            else:
                break
        
        # Also check for a single key without a number
        single_key = os.getenv(self.env_prefix)
        if single_key and single_key not in keys:
            keys.append(single_key)
            
        return keys
    
    def get_random_key(self) -> str:
        """Get a random API key, avoiding recently rate-limited keys if possible."""
        if not self.keys:
            raise ValueError(f"No API keys available for {self.env_prefix}")
        
        # Filter out keys that are still rate-limited
        current_time = time.time()
        available_keys = [k for k in self.keys if current_time > self.rate_limited_until[k]]
        
        # If all keys are rate-limited, use the one that will become available soonest
        if not available_keys:
            logger.warning("All keys are currently rate-limited, selecting least-recently rate-limited key")
            key = min(self.rate_limited_until.items(), key=lambda x: x[1])[0]
        else:
            key = random.choice(available_keys)
            
        # Update usage tracking
        self.key_usage_count[key] += 1
        self.last_used_time[key] = current_time
        logger.info(f"Using key: {key[:10]}... (usage count: {self.key_usage_count[key]})")
        return key
    
    def get_least_used_key(self) -> str:
        """Get the least used API key, avoiding rate-limited keys if possible."""
        if not self.keys:
            raise ValueError(f"No API keys available for {self.env_prefix}")
        
        # Filter out keys that are still rate-limited
        current_time = time.time()
        available_keys = [k for k in self.keys if current_time > self.rate_limited_until[k]]
        
        if not available_keys:
            logger.warning("All keys are currently rate-limited, selecting least-recently rate-limited key")
            key = min(self.rate_limited_until.items(), key=lambda x: x[1])[0]
        else:
            # Sort by usage count (ascending)
            key = min(
                [(k, self.key_usage_count[k]) for k in available_keys],
                key=lambda x: x[1]
            )[0]
        
        # Update usage tracking
        self.key_usage_count[key] += 1
        self.last_used_time[key] = current_time
        
        return key
    
    def get_least_recently_used_key(self) -> str:
        """Get the least recently used API key, avoiding rate-limited keys if possible."""
        if not self.keys:
            raise ValueError(f"No API keys available for {self.env_prefix}")
        
        # Filter out keys that are still rate-limited
        current_time = time.time()
        available_keys = [k for k in self.keys if current_time > self.rate_limited_until[k]]
        
        if not available_keys:
            logger.warning("All keys are currently rate-limited, selecting least-recently rate-limited key")
            key = min(self.rate_limited_until.items(), key=lambda x: x[1])[0]
        else:
            # Sort by last used time (ascending)
            key = min(
                [(k, self.last_used_time[k]) for k in available_keys],
                key=lambda x: x[1]
            )[0]
        
        # Update usage tracking
        self.key_usage_count[key] += 1
        self.last_used_time[key] = current_time
        
        return key
    
    def mark_key_rate_limited(self, key: str, duration: int = 60) -> None:
        """
        Mark a key as rate limited to temporarily avoid using it.
        
        Args:
            key: The API key that encountered a rate limit
            duration: Duration in seconds to avoid this key (default: 60 seconds)
        """
        if key in self.keys:
            current_time = time.time()
            self.rate_limited_until[key] = current_time + duration
            logger.info(f"Key {key[:5]}... marked as rate-limited for {duration} seconds")
    
    def get_key_stats(self) -> Dict:
        """Get usage statistics for all keys."""
        current_time = time.time()
        return {
            "provider_prefix": self.env_prefix,
            "total_keys": len(self.keys),
            "available_keys": sum(1 for k in self.keys if current_time > self.rate_limited_until[k]),
            "usage_counts": self.key_usage_count,
            "rate_limited_keys": {k: v for k, v in self.rate_limited_until.items() if v > current_time}
        }
    
    def reset_usage_stats(self) -> None:
        """Reset usage statistics for all keys."""
        self.key_usage_count = {key: 0 for key in self.keys}
        # We don't reset last_used_time or rate_limited_until as those are operational data


# Factory function to easily get a key manager for a specific provider
_key_manager_instances = {}

def get_key_manager(provider_prefix: str) -> LLMKeyManager:
    """
    Get or create a key manager instance for a specific provider.
    
    Args:
        provider_prefix: The environment variable prefix for this provider's API keys
                        (e.g., "GEMINI_API_KEY" or "OPENAI_API_KEY")
    
    Returns:
        A key manager instance specific to the requested provider
    """
    global _key_manager_instances
    
    if provider_prefix not in _key_manager_instances:
        _key_manager_instances[provider_prefix] = LLMKeyManager(provider_prefix)
    
    return _key_manager_instances[provider_prefix]


if __name__ == "__main__":
    # Example usage
    gemini_key_manager = get_key_manager("GEMINI_API_KEY")
    
    # Get a random key
    key = gemini_key_manager.get_random_key()
    print(f"Using Gemini key: {key[:10]}...")
    
    # Check stats
    stats = gemini_key_manager.get_key_stats()
    print(f"Available keys: {stats['available_keys']}/{stats['total_keys']}")