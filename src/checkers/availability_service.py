"""Combined availability checking service (powered by tldx)."""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from .tldx_checker import TldxChecker
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
    """Unified service for checking domain availability via tldx."""

    INTERMEDIATE_FILE = "data/results/.intermediate_results.json"
    METHOD = "tldx"

    def __init__(
        self,
        tldx_binary: str = "tldx",
        batch_size: int = 100,
        timeout: float = 180.0,
        use_cache: bool = True,
        cache_file: str = "data/results/checked_cache.json",
    ):
        self.checker = TldxChecker(binary=tldx_binary, batch_size=batch_size, timeout=timeout)
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

    def check_single(self, domain: str, **_ignored) -> DomainResult:
        """Check a single domain's availability."""
        if self.cache:
            cached = self.cache.get(domain)
            if cached is not None:
                return DomainResult(
                    domain=domain,
                    available=cached['available'],
                    method=cached['method'],
                    cached=True,
                )

        available = self.checker.check_single(domain)
        if self.cache and available is not None:
            self.cache.set(domain, available, self.METHOD)
        return DomainResult(domain=domain, available=available, method=self.METHOD)

    def check_batch(
        self,
        domains: List[str],
        progress_callback=None,
        phase_callback=None,
        **_ignored,
    ) -> List[DomainResult]:
        """Check multiple domains via tldx.

        phase_callback is invoked as phase_callback(phase, current, total) where
        phase is one of: 'cache', 'tldx'.
        """
        cached_results: Dict[str, DomainResult] = {}
        to_check: List[str] = []

        def notify(phase, current, total):
            if phase_callback:
                phase_callback(phase, current, total)
            if progress_callback:
                progress_callback(len(cached_results) + current, len(domains))

        if self.cache:
            for i, domain in enumerate(domains):
                cached = self.cache.get(domain)
                if cached is not None:
                    cached_results[domain] = DomainResult(
                        domain=domain,
                        available=cached['available'],
                        method=cached['method'],
                        cached=True,
                    )
                else:
                    to_check.append(domain)
                notify('cache', i + 1, len(domains))
        else:
            to_check = list(domains)
            notify('cache', len(domains), len(domains))

        fresh_results: List[DomainResult] = []
        if to_check:
            available_so_far: List[DomainResult] = []

            def on_progress(current, total):
                # Periodic intermediate snapshot
                if current and current % 50 == 0:
                    self._save_intermediate(fresh_results, available_so_far)
                notify('tldx', current, total)

            check_results = self.checker.check_batch(to_check, progress_callback=on_progress)

            for domain in to_check:
                available = check_results.get(domain)
                result = DomainResult(domain=domain, available=available, method=self.METHOD)
                fresh_results.append(result)
                if available is True:
                    available_so_far.append(result)
                if self.cache and available is not None:
                    self.cache.set(domain, available, self.METHOD)

        all_results = list(cached_results.values()) + fresh_results
        domain_order = {d: i for i, d in enumerate(domains)}
        all_results.sort(key=lambda r: domain_order.get(r.domain, 999999))

        available_results = [r for r in all_results if r.available is True]
        self._save_intermediate(all_results, available_results)

        return all_results

    def check_word_across_tlds(
        self,
        word: str,
        tlds: List[str],
        **_ignored,
    ) -> Dict[str, DomainResult]:
        """Check a single word across multiple TLDs."""
        domains = [f"{word}.{tld}" for tld in tlds]
        results = self.check_batch(domains)
        return {r.domain: r for r in results}

    def find_available(
        self,
        words: List[str],
        tlds: List[str],
        progress_callback=None,
        phase_callback=None,
        **_ignored,
    ) -> List[DomainResult]:
        """Find available domains from word list across TLDs."""
        domains = [f"{word}.{tld}" for word in words for tld in tlds]
        results = self.check_batch(
            domains,
            progress_callback=progress_callback,
            phase_callback=phase_callback,
        )
        return [r for r in results if r.available is True]
