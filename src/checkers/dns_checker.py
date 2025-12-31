"""DNS-based domain availability checker."""

import asyncio
from typing import List, Dict, Optional
import dns.resolver
import dns.asyncresolver


class DNSChecker:
    """Fast DNS-based domain availability pre-filter."""
    
    def __init__(self, timeout: float = 3.0, max_concurrent: int = 20):
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self._semaphore: Optional[asyncio.Semaphore] = None
    
    def check_single(self, domain: str) -> bool:
        """Check if a single domain is likely available via DNS.
        
        Returns True if domain has no DNS records (likely available).
        """
        try:
            resolver = dns.resolver.Resolver()
            resolver.timeout = self.timeout
            resolver.lifetime = self.timeout
            
            # Try to resolve A record
            resolver.resolve(domain, 'A')
            return False  # Has records, not available
        except dns.resolver.NXDOMAIN:
            return True  # No domain, likely available
        except dns.resolver.NoAnswer:
            return False  # Domain exists but no A record
        except dns.resolver.NoNameservers:
            return True  # Could be available
        except dns.resolver.Timeout:
            return None  # Unknown, timeout
        except Exception:
            return None  # Unknown error
    
    async def _check_single_async(self, domain: str) -> tuple[str, Optional[bool]]:
        """Async check for a single domain."""
        async with self._semaphore:
            try:
                resolver = dns.asyncresolver.Resolver()
                resolver.timeout = self.timeout
                resolver.lifetime = self.timeout
                
                await resolver.resolve(domain, 'A')
                return (domain, False)  # Has records
            except dns.resolver.NXDOMAIN:
                return (domain, True)  # Available
            except dns.resolver.NoAnswer:
                return (domain, False)  # Exists
            except dns.resolver.NoNameservers:
                return (domain, True)  # Likely available
            except dns.resolver.Timeout:
                return (domain, None)  # Unknown
            except Exception:
                return (domain, None)
    
    async def check_batch_async(self, domains: List[str]) -> Dict[str, Optional[bool]]:
        """Check multiple domains concurrently."""
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        
        tasks = [self._check_single_async(domain) for domain in domains]
        results = await asyncio.gather(*tasks)
        
        return {domain: available for domain, available in results}
    
    def check_batch(self, domains: List[str]) -> Dict[str, Optional[bool]]:
        """Synchronous wrapper for batch checking."""
        return asyncio.run(self.check_batch_async(domains))
    
    def check_with_tlds(self, word: str, tlds: List[str]) -> Dict[str, Optional[bool]]:
        """Check a word across multiple TLDs."""
        domains = [f"{word}.{tld}" for tld in tlds]
        return self.check_batch(domains)
