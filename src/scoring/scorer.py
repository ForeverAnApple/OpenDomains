"""Domain scoring system."""

from pathlib import Path
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass
from ..utils.word_validator import WordValidator


@dataclass
class DomainScore:
    """Detailed domain score breakdown."""
    domain: str
    total_score: float
    pronounceability: int
    spellability: int
    length_score: int
    memorability: int
    brandability: int
    dictionary_score: int
    tld_multiplier: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'domain': self.domain,
            'total_score': round(self.total_score, 1),
            'breakdown': {
                'pronounceability': self.pronounceability,
                'spellability': self.spellability,
                'length': self.length_score,
                'memorability': self.memorability,
                'brandability': self.brandability,
                'dictionary': self.dictionary_score
            },
            'tld_multiplier': self.tld_multiplier
        }


class DomainScorer:
    """Scores domains based on quality metrics."""
    
    DEFAULT_WEIGHTS = {
        'pronounceability': 0.25,
        'spellability': 0.20,
        'length': 0.15,
        'memorability': 0.15,
        'brandability': 0.10,
        'dictionary': 0.15
    }
    
    WORDLIST_PATH = Path("data/wordlists/english_words.txt")
    
    DEFAULT_TLD_MULTIPLIERS = {
        'com': 1.5,
        'io': 1.3,
        'ai': 1.3,
        'co': 1.2,
        'app': 1.2,
        'dev': 1.2,
        'tech': 1.1,
        'net': 1.0,
        'org': 1.0
    }
    
    # Common word patterns that are memorable
    MEMORABLE_PATTERNS = [
        'ing', 'tion', 'ness', 'ment', 'able', 'ible', 'ful', 'less',
        'ly', 'er', 'or', 'ist', 'ism'
    ]
    
    # Dictionary of common English words (for memorability bonus)
    COMMON_WORDS = {
        'cloud', 'swift', 'spark', 'flow', 'wave', 'bolt', 'dash', 'pulse',
        'bright', 'clear', 'fast', 'quick', 'smart', 'sharp', 'bold', 'pure',
        'code', 'data', 'sync', 'link', 'node', 'core', 'stack', 'mesh',
        'build', 'ship', 'grow', 'push', 'pull', 'snap', 'flip', 'zoom'
    }
    
    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        tld_multipliers: Optional[Dict[str, float]] = None
    ):
        self.weights = weights or self.DEFAULT_WEIGHTS
        self.tld_multipliers = tld_multipliers or self.DEFAULT_TLD_MULTIPLIERS
        self.validator = WordValidator()
        self._dictionary: Optional[Set[str]] = None
    
    def _load_dictionary(self) -> Set[str]:
        """Load dictionary words for single-word bonus scoring."""
        if self._dictionary is not None:
            return self._dictionary
        
        self._dictionary = set()
        if self.WORDLIST_PATH.exists():
            with open(self.WORDLIST_PATH, 'r') as f:
                self._dictionary = {line.strip().lower() for line in f if line.strip()}
        return self._dictionary
    
    def _score_dictionary(self, word: str) -> int:
        """Score bonus for real single dictionary words."""
        dictionary = self._load_dictionary()
        word_lower = word.lower()
        
        # Perfect match - real English word
        if word_lower in dictionary:
            return 100
        
        # Check if it's in our curated common words
        if word_lower in self.COMMON_WORDS:
            return 100
        
        return 0
    
    def _get_word_and_tld(self, domain: str) -> tuple[str, str]:
        """Extract word and TLD from domain."""
        parts = domain.lower().split('.')
        if len(parts) >= 2:
            return parts[0], parts[-1]
        return domain, ''
    
    def _score_length(self, word: str) -> int:
        """Score based on word length."""
        length = len(word)
        if 4 <= length <= 6:
            return 100
        elif 7 <= length <= 8:
            return 85
        elif 9 <= length <= 10:
            return 70
        elif 11 <= length <= 12:
            return 50
        elif length < 4:
            return 40
        else:
            return 30
    
    def _score_memorability(self, word: str) -> int:
        """Score how memorable the word is."""
        score = 50  # Base score
        word_lower = word.lower()
        
        # Real common word bonus
        if word_lower in self.COMMON_WORDS:
            score += 30
        
        # Recognizable pattern bonus
        for pattern in self.MEMORABLE_PATTERNS:
            if pattern in word_lower:
                score += 5
                break
        
        # Rhythm bonus (alternating consonant/vowel)
        vowels = set('aeiou')
        alternating = True
        for i in range(len(word) - 1):
            both_vowels = word[i] in vowels and word[i+1] in vowels
            both_consonants = word[i] not in vowels and word[i+1] not in vowels
            if both_vowels or (both_consonants and i < len(word) - 2):
                if word[i] != word[i+1]:  # Allow double letters
                    alternating = False
                    break
        
        if alternating:
            score += 15
        
        # Short word bonus
        if len(word) <= 6:
            score += 10
        
        return min(100, score)
    
    def _score_brandability(self, word: str) -> int:
        """Score brandability potential."""
        score = 50
        word_lower = word.lower()
        
        # Starts with strong consonant
        strong_starts = 'bcdfgklmpstvz'
        if word_lower[0] in strong_starts:
            score += 10
        
        # Ends with a vowel or soft consonant (pleasing sound)
        soft_ends = 'aeioumnrly'
        if word_lower[-1] in soft_ends:
            score += 10
        
        # No repeating letters except common doubles
        allowed_doubles = {'ll', 'ss', 'tt', 'ff', 'ee', 'oo'}
        has_bad_doubles = False
        for i in range(len(word) - 1):
            if word[i] == word[i+1] and word[i:i+2].lower() not in allowed_doubles:
                has_bad_doubles = True
                break
        
        if not has_bad_doubles:
            score += 10
        
        # Known brandable word
        if word_lower in self.COMMON_WORDS:
            score += 15
        
        # Good length for brand
        if 5 <= len(word) <= 8:
            score += 10
        
        return min(100, score)
    
    def score(self, domain: str) -> DomainScore:
        """Calculate comprehensive score for a domain."""
        word, tld = self._get_word_and_tld(domain)
        
        # Get individual scores
        pronounceability = self.validator.get_pronounceability_score(word)
        spellability = self.validator.get_spellability_score(word)
        length_score = self._score_length(word)
        memorability = self._score_memorability(word)
        brandability = self._score_brandability(word)
        dictionary_score = self._score_dictionary(word)
        
        # Calculate weighted score
        raw_score = (
            pronounceability * self.weights['pronounceability'] +
            spellability * self.weights['spellability'] +
            length_score * self.weights['length'] +
            memorability * self.weights['memorability'] +
            brandability * self.weights['brandability'] +
            dictionary_score * self.weights['dictionary']
        )
        
        # Apply TLD multiplier
        tld_multiplier = self.tld_multipliers.get(tld, 1.0)
        total_score = raw_score * tld_multiplier
        
        return DomainScore(
            domain=domain,
            total_score=total_score,
            pronounceability=pronounceability,
            spellability=spellability,
            length_score=length_score,
            memorability=memorability,
            brandability=brandability,
            dictionary_score=dictionary_score,
            tld_multiplier=tld_multiplier
        )
    
    def score_batch(self, domains: list[str]) -> list[DomainScore]:
        """Score multiple domains."""
        return [self.score(domain) for domain in domains]
    
    def rank(self, domains: list[str], min_score: float = 0) -> list[DomainScore]:
        """Score and rank domains by total score."""
        scores = self.score_batch(domains)
        scores = [s for s in scores if s.total_score >= min_score]
        scores.sort(key=lambda s: s.total_score, reverse=True)
        return scores
