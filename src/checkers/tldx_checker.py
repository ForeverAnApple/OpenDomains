"""tldx-based domain availability checker.

Wraps the `tldx` CLI (https://github.com/brandonyoungdev/tldx) for fast,
RDAP/WHOIS-backed availability checks. tldx accepts keywords + TLDs and
emits results as a stream of JSON objects, which we parse line by line.
"""

import json
import shutil
import subprocess
from collections import defaultdict
from typing import Dict, List, Optional, Tuple


class TldxChecker:
    """Checks domain availability by shelling out to `tldx`."""

    def __init__(
        self,
        binary: str = "tldx",
        batch_size: int = 100,
        timeout: float = 180.0,
    ):
        self.binary = binary
        self.batch_size = batch_size
        self.timeout = timeout

        if shutil.which(self.binary) is None:
            raise RuntimeError(
                f"`{self.binary}` binary not found on PATH. Install tldx from "
                "https://github.com/brandonyoungdev/tldx"
            )

    @staticmethod
    def _split_domain(domain: str) -> Tuple[str, str]:
        """Split 'word.tld' into (word, tld). Supports multi-label TLDs (e.g. co.uk)."""
        keyword, _, tld = domain.partition(".")
        if not keyword or not tld:
            raise ValueError(f"Invalid domain: {domain!r}")
        return keyword, tld

    def _run(self, keywords: List[str], tld: str) -> Dict[str, Optional[bool]]:
        """Invoke tldx for one batch of keywords against a single TLD."""
        cmd = [
            self.binary,
            *keywords,
            "-t", tld,
            "--format", "json-stream",
            "--no-color",
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {f"{kw}.{tld}": None for kw in keywords}

        results: Dict[str, Optional[bool]] = {}
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            domain = obj.get("domain")
            if not domain:
                continue
            results[domain] = obj.get("available")

        # Fill in misses (keyword that didn't appear in output) as unknown
        for kw in keywords:
            results.setdefault(f"{kw}.{tld}", None)

        return results

    def check_single(self, domain: str) -> Optional[bool]:
        """Check a single domain. Returns True/False/None (unknown)."""
        keyword, tld = self._split_domain(domain)
        return self._run([keyword], tld).get(domain)

    def check_batch(
        self,
        domains: List[str],
        progress_callback=None,
    ) -> Dict[str, Optional[bool]]:
        """Check many domains. Groups by TLD, batches keywords per call."""
        grouped: Dict[str, List[str]] = defaultdict(list)
        seen_per_tld: Dict[str, set] = defaultdict(set)
        for d in domains:
            keyword, tld = self._split_domain(d)
            if keyword in seen_per_tld[tld]:
                continue
            seen_per_tld[tld].add(keyword)
            grouped[tld].append(keyword)

        domain_set = set(domains)
        results: Dict[str, Optional[bool]] = {}
        completed = 0
        total = len(domains)

        for tld, keywords in grouped.items():
            for i in range(0, len(keywords), self.batch_size):
                batch = keywords[i:i + self.batch_size]
                batch_results = self._run(batch, tld)
                for domain, available in batch_results.items():
                    if domain in domain_set:
                        results[domain] = available
                completed += len(batch)
                if progress_callback:
                    progress_callback(completed, total)

        for d in domains:
            results.setdefault(d, None)
        return results
