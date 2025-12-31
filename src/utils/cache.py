"""Caching utilities for domain check results."""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from pathlib import Path


class ResultCache:
    """Simple file-based cache for domain availability results."""
    
    def __init__(self, cache_file: str = "data/results/checked_cache.json", ttl_hours: int = 24):
        self.cache_file = Path(cache_file)
        self.ttl = timedelta(hours=ttl_hours)
        self._cache: Dict[str, Any] = {}
        self._load()
    
    def _load(self):
        """Load cache from file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    self._cache = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._cache = {}
    
    def _save(self):
        """Save cache to file."""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, 'w') as f:
            json.dump(self._cache, f, indent=2)
    
    def get(self, domain: str) -> Optional[Dict]:
        """Get cached result if not expired."""
        if domain not in self._cache:
            return None
        
        entry = self._cache[domain]
        cached_time = datetime.fromisoformat(entry['checked_at'])
        
        if datetime.now() - cached_time > self.ttl:
            del self._cache[domain]
            return None
        
        return entry
    
    def set(self, domain: str, available: bool, method: str = "dns"):
        """Cache a domain check result."""
        self._cache[domain] = {
            'available': available,
            'method': method,
            'checked_at': datetime.now().isoformat()
        }
        self._save()
    
    def set_batch(self, results: Dict[str, bool], method: str = "dns"):
        """Cache multiple results at once."""
        now = datetime.now().isoformat()
        for domain, available in results.items():
            self._cache[domain] = {
                'available': available,
                'method': method,
                'checked_at': now
            }
        self._save()
    
    def clear_expired(self):
        """Remove expired entries."""
        now = datetime.now()
        expired = []
        
        for domain, entry in self._cache.items():
            cached_time = datetime.fromisoformat(entry['checked_at'])
            if now - cached_time > self.ttl:
                expired.append(domain)
        
        for domain in expired:
            del self._cache[domain]
        
        if expired:
            self._save()
        
        return len(expired)
    
    def stats(self) -> Dict:
        """Get cache statistics."""
        available = sum(1 for e in self._cache.values() if e['available'])
        return {
            'total_entries': len(self._cache),
            'available_domains': available,
            'unavailable_domains': len(self._cache) - available
        }
