"""Combined availability checking service."""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from .dns_checker import DNSChecker
from .whois_checker import WhoisChecker
from ..utils.cache import ResultCache


@dataclass
class DomainResult:
    """Result of domain availability check."""
    domain: str
    available: Optional[bool]
    method: str
    cached: bool = False
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'domain': self.domain,
            'available': self.available,
            'method': self.method,
            'cached': self.cached
        }
        if self.error:
            result['error'] = self.error
        return result


class AvailabilityService:
    """Unified service for checking domain availability."""
    
    INTERMEDIATE_FILE = "data/results/.intermediate_results.json"
    
    def __init__(
        self,
        dns_timeout: float = 3.0,
        whois_timeout: float = 10.0,
        max_concurrent: int = 10,
        rate_limit_delay: float = 1.5,
        use_cache: bool = True,
        cache_file: str = "data/results/checked_cache.json"
    ):
        self.dns_checker = DNSChecker(timeout=dns_timeout, max_concurrent=max_concurrent)
        self.whois_checker = WhoisChecker(timeout=whois_timeout, rate_limit_delay=rate_limit_delay)
        self.cache = ResultCache(cache_file=cache_file) if use_cache else None
    
    def _save_intermediate(self, results: List[DomainResult], available: List[DomainResult]):
        """Save intermediate results to recover from crashes."""
        path = Path(self.INTERMEDIATE_FILE)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'timestamp': datetime.now().isoformat(),
            'checked_count': len(results),
            'available_count': len(available),
            'available_domains': [r.to_dict() for r in available]
        }
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_intermediate(self) -> Optional[Dict]:
        """Load intermediate results from previous run."""
        path = Path(self.INTERMEDIATE_FILE)
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return None
    
    def clear_intermediate(self):
        """Clear intermediate results file."""
        path = Path(self.INTERMEDIATE_FILE)
        if path.exists():
            path.unlink()
    
    def check_single(self, domain: str, verify_with_whois: bool = True) -> DomainResult:
        """Check a single domain's availability.
        
        Args:
            domain: Full domain name (e.g., 'example.com')
            verify_with_whois: If DNS suggests available, verify with WHOIS
        """
        # Check cache first
        if self.cache:
            cached = self.cache.get(domain)
            if cached is not None:
                return DomainResult(
                    domain=domain,
                    available=cached['available'],
                    method=cached['method'],
                    cached=True
                )
        
        # DNS check first (fast)
        dns_result = self.dns_checker.check_single(domain)
        
        if dns_result is False:
            # Definitely not available
            if self.cache:
                self.cache.set(domain, False, 'dns')
            return DomainResult(domain=domain, available=False, method='dns')
        
        if dns_result is True and verify_with_whois:
            # Verify with WHOIS
            whois_result = self.whois_checker.check_single(domain)
            available = whois_result is True
            method = 'whois'
        else:
            available = dns_result
            method = 'dns'
        
        if self.cache and available is not None:
            self.cache.set(domain, available, method)
        
        return DomainResult(domain=domain, available=available, method=method)
    
    def check_batch(
        self,
        domains: List[str],
        verify_with_whois: bool = True,
        progress_callback=None,
        phase_callback=None
    ) -> List[DomainResult]:
        """Check multiple domains.
        
        Args:
            domains: List of full domain names
            verify_with_whois: Verify DNS-available domains with WHOIS
            progress_callback: Optional callback(current, total) for progress (legacy)
            phase_callback: Optional callback(phase, current, total) for multi-phase progress
                           phase is one of: 'cache', 'dns', 'whois'
        """
        results = []
        cached_results = {}
        to_check = []
        
        def notify(phase, current, total):
            if phase_callback:
                phase_callback(phase, current, total)
            if progress_callback:
                progress_callback(len(results) + len(cached_results), len(domains))
        
        # Check cache first
        if self.cache:
            for i, domain in enumerate(domains):
                cached = self.cache.get(domain)
                if cached is not None:
                    cached_results[domain] = DomainResult(
                        domain=domain,
                        available=cached['available'],
                        method=cached['method'],
                        cached=True
                    )
                else:
                    to_check.append(domain)
                notify('cache', i + 1, len(domains))
        else:
            to_check = domains
            notify('cache', len(domains), len(domains))
        
        # DNS batch check for uncached domains
        if to_check:
            dns_results = self.dns_checker.check_batch(to_check)
            
            possibly_available = []
            
            for i, (domain, dns_result) in enumerate(dns_results.items()):
                if dns_result is False:
                    result = DomainResult(domain=domain, available=False, method='dns')
                    results.append(result)
                    if self.cache:
                        self.cache.set(domain, False, 'dns')
                elif dns_result is True:
                    possibly_available.append(domain)
                else:
                    # Unknown - treat as unavailable for safety
                    results.append(DomainResult(domain=domain, available=None, method='dns'))
                
                notify('dns', i + 1, len(to_check))
            
            # WHOIS verification for possibly available domains
            if verify_with_whois and possibly_available:
                available_so_far = [r for r in results if r.available is True]
                
                for i, domain in enumerate(possibly_available):
                    error_msg = None
                    try:
                        whois_result = self.whois_checker.check_single(domain)
                        available = whois_result is True
                    except Exception as e:
                        # Track error silently, trust DNS result
                        error_msg = str(e)
                        available = True
                    
                    result = DomainResult(domain=domain, available=available, method='whois', error=error_msg)
                    results.append(result)
                    
                    if available:
                        available_so_far.append(result)
                    
                    if self.cache:
                        self.cache.set(domain, available, 'whois')
                    
                    # Save intermediate results every 10 domains
                    if len(results) % 10 == 0:
                        self._save_intermediate(results, available_so_far)
                    
                    notify('whois', i + 1, len(possibly_available))
            elif possibly_available:
                # No WHOIS verification, trust DNS
                for domain in possibly_available:
                    result = DomainResult(domain=domain, available=True, method='dns')
                    results.append(result)
                    if self.cache:
                        self.cache.set(domain, True, 'dns')
        
        # Combine cached and fresh results
        all_results = list(cached_results.values()) + results
        
        # Sort by original order
        domain_order = {d: i for i, d in enumerate(domains)}
        all_results.sort(key=lambda r: domain_order.get(r.domain, 999999))
        
        # Final save and cleanup
        available_results = [r for r in all_results if r.available is True]
        self._save_intermediate(all_results, available_results)
        
        return all_results
    
    def check_word_across_tlds(
        self,
        word: str,
        tlds: List[str],
        verify_with_whois: bool = True
    ) -> Dict[str, DomainResult]:
        """Check a single word across multiple TLDs."""
        domains = [f"{word}.{tld}" for tld in tlds]
        results = self.check_batch(domains, verify_with_whois=verify_with_whois)
        return {r.domain: r for r in results}
    
    def find_available(
        self,
        words: List[str],
        tlds: List[str],
        verify_with_whois: bool = True,
        progress_callback=None,
        phase_callback=None
    ) -> List[DomainResult]:
        """Find available domains from word list across TLDs."""
        domains = [f"{word}.{tld}" for word in words for tld in tlds]
        results = self.check_batch(
            domains,
            verify_with_whois=verify_with_whois,
            progress_callback=progress_callback,
            phase_callback=phase_callback
        )
        return [r for r in results if r.available is True]
