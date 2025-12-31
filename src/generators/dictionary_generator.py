"""Dictionary-based word generator for domain names."""

import urllib.request
from pathlib import Path
from typing import List, Set, Optional
from ..utils.word_validator import WordValidator


class DictionaryGenerator:
    """Generates domain candidates from dictionary words."""
    
    # Common tech-friendly suffixes
    TECH_SUFFIXES = ['ly', 'ify', 'io', 'app', 'kit', 'hub', 'lab', 'box', 'pad']
    TECH_PREFIXES = ['go', 'my', 'get', 'use', 'try', 'pro']
    
    # Word categories that make good domains
    GOOD_CATEGORIES = {
        'action': ['build', 'ship', 'grow', 'flow', 'sync', 'link', 'push', 'pull', 
                   'loop', 'snap', 'dash', 'rush', 'leap', 'zoom', 'bolt', 'flip',
                   'spark', 'blend', 'craft', 'forge', 'mint', 'cast', 'fuse'],
        'nature': ['wave', 'wind', 'rain', 'fire', 'leaf', 'seed', 'root', 'bloom',
                   'cloud', 'storm', 'stone', 'river', 'ocean', 'peak', 'dawn', 'dusk'],
        'tech': ['code', 'data', 'byte', 'node', 'port', 'grid', 'mesh', 'core',
                 'stack', 'cache', 'queue', 'hash', 'ping', 'sync', 'pixel', 'vector'],
        'abstract': ['swift', 'bright', 'clear', 'prime', 'vivid', 'rapid', 'agile',
                     'nimble', 'sleek', 'crisp', 'bold', 'keen', 'pure', 'zen']
    }
    
    WORDS_URL = "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt"
    
    def __init__(self, wordlist_path: Optional[str] = None, min_length: int = 4, max_length: int = 10):
        self.validator = WordValidator(min_length=min_length, max_length=max_length)
        self.min_length = min_length
        self.max_length = max_length
        self.wordlist_path = Path(wordlist_path) if wordlist_path else Path("data/wordlists/english_words.txt")
        self._words: Set[str] = set()
    
    def load_words(self, download_if_missing: bool = True) -> int:
        """Load words from file or download if missing."""
        if self.wordlist_path.exists():
            with open(self.wordlist_path, 'r') as f:
                self._words = {line.strip().lower() for line in f if line.strip()}
        elif download_if_missing:
            self._download_wordlist()
        
        return len(self._words)
    
    def _download_wordlist(self):
        """Download English wordlist."""
        print(f"Downloading wordlist from {self.WORDS_URL}...")
        self.wordlist_path.parent.mkdir(parents=True, exist_ok=True)
        
        urllib.request.urlretrieve(self.WORDS_URL, self.wordlist_path)
        
        with open(self.wordlist_path, 'r') as f:
            self._words = {line.strip().lower() for line in f if line.strip()}
        
        print(f"Downloaded {len(self._words)} words")
    
    def generate(self, limit: Optional[int] = None) -> List[str]:
        """Generate domain-worthy words from dictionary."""
        if not self._words:
            self.load_words()
        
        candidates = []
        
        # Filter dictionary words
        for word in self._words:
            if self.validator.is_valid(word):
                candidates.append(word)
        
        # Sort by quality (shorter words first, then alphabetically)
        candidates.sort(key=lambda w: (len(w), w))
        
        if limit:
            candidates = candidates[:limit]
        
        return candidates
    
    def generate_curated(self) -> List[str]:
        """Generate from curated high-quality word lists."""
        candidates = []
        
        for category, words in self.GOOD_CATEGORIES.items():
            for word in words:
                if self.validator.is_valid(word):
                    candidates.append(word)
        
        return list(set(candidates))
    
    def generate_with_affixes(self, base_words: Optional[List[str]] = None) -> List[str]:
        """Generate variations with tech-friendly prefixes/suffixes."""
        if base_words is None:
            base_words = self.generate_curated()
        
        candidates = set(base_words)
        
        for word in base_words:
            # Add suffixes
            for suffix in self.TECH_SUFFIXES:
                new_word = word + suffix
                if self.validator.is_valid(new_word):
                    candidates.add(new_word)
            
            # Add prefixes
            for prefix in self.TECH_PREFIXES:
                new_word = prefix + word
                if self.validator.is_valid(new_word):
                    candidates.add(new_word)
        
        return list(candidates)
