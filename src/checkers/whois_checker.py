"""WHOIS-based domain availability checker."""

import time
from typing import List, Dict, Optional
import whois
from whois.exceptions import WhoisDomainNotFoundError


class WhoisChecker:
    """WHOIS-based domain availability verification."""
    
    RATE_LIMIT_PATTERNS = ['rate limit', 'too many requests', 'quota exceeded', 'try again later', 'blocked']
    
    def __init__(self, timeout: float = 10.0, rate_limit_delay: float = 1.5, backoff_delay: float = 5.0):
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay
        self.backoff_delay = backoff_delay
        self._last_request_time = 0
        self._consecutive_errors = 0
    
    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits."""
        # Add extra delay if we've been hitting errors
        extra_delay = min(self._consecutive_errors * 2, 30)
        total_delay = self.rate_limit_delay + extra_delay
        
        elapsed = time.time() - self._last_request_time
        if elapsed < total_delay:
            time.sleep(total_delay - elapsed)
        self._last_request_time = time.time()
    
    def check_single(self, domain: str, retry: bool = True) -> Optional[bool]:
        """Check if a single domain is available via WHOIS.
        
        Returns:
            True: Domain is available
            False: Domain is registered
            None: Check failed/unknown
        """
        self._wait_for_rate_limit()
        
        try:
            w = whois.whois(domain)
            
            # Success - reset error counter
            self._consecutive_errors = 0
            
            # If domain_name is None or empty, domain is likely available
            if w.domain_name is None:
                return True
            
            # If we get WHOIS data, domain is registered
            return False
        
        except WhoisDomainNotFoundError:
            self._consecutive_errors = 0
            return True
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check for rate limiting
            if any(p in error_msg for p in self.RATE_LIMIT_PATTERNS):
                self._consecutive_errors += 1
                if retry:
                    time.sleep(self.backoff_delay)
                    return self.check_single(domain, retry=False)
                return None
            
            # Common patterns indicating availability
            if any(x in error_msg for x in ['no match', 'not found', 'no entries', 'available', 'domain not found']):
                self._consecutive_errors = 0
                return True
            
            # Common patterns indicating registration
            if any(x in error_msg for x in ['registered', 'exists']):
                self._consecutive_errors = 0
                return False
            
            # Unknown error - increment counter but don't fail hard
            self._consecutive_errors += 1
            return None
    
    def check_batch(self, domains: List[str], stop_on_found: bool = False) -> Dict[str, Optional[bool]]:
        """Check multiple domains sequentially with rate limiting.
        
        Args:
            domains: List of domains to check
            stop_on_found: If True, stop when first available domain is found
        """
        results = {}
        
        for domain in domains:
            result = self.check_single(domain)
            results[domain] = result
            
            if stop_on_found and result is True:
                break
        
        return results
    
    def get_whois_info(self, domain: str) -> Optional[Dict]:
        """Get full WHOIS information for a domain."""
        self._wait_for_rate_limit()
        
        try:
            w = whois.whois(domain)
            return {
                'domain_name': w.domain_name,
                'registrar': w.registrar,
                'creation_date': str(w.creation_date) if w.creation_date else None,
                'expiration_date': str(w.expiration_date) if w.expiration_date else None,
                'name_servers': w.name_servers,
                'status': w.status,
            }
        except Exception:
            return None
