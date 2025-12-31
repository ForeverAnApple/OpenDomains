"""Phonetically-generated brandable word generator."""

import random
from typing import List, Set, Optional
from ..utils.word_validator import WordValidator


class PhoneticGenerator:
    """Generates pronounceable made-up words for brandable domains."""
    
    # Syllable building blocks
    ONSETS = [
        '', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'p', 'r', 's', 't', 'v', 'w', 'z',
        'bl', 'br', 'cl', 'cr', 'dr', 'fl', 'fr', 'gl', 'gr', 'pl', 'pr', 'sc', 'sk', 'sl', 'sm',
        'sn', 'sp', 'st', 'sw', 'tr', 'tw', 'ch', 'sh', 'th', 'wh'
    ]
    
    VOWELS = ['a', 'e', 'i', 'o', 'u', 'ai', 'ea', 'ee', 'oa', 'oo', 'ou']
    SIMPLE_VOWELS = ['a', 'e', 'i', 'o', 'u']
    
    CODAS = [
        '', 'b', 'd', 'f', 'g', 'k', 'l', 'm', 'n', 'p', 'r', 's', 't', 'x', 'z',
        'ck', 'ft', 'ld', 'lk', 'lm', 'lp', 'lt', 'mp', 'nd', 'nk', 'nt', 'pt',
        'rd', 'rk', 'rm', 'rn', 'rp', 'rt', 'sk', 'sp', 'st', 'ng', 'sh', 'ch', 'th'
    ]
    
    # Pleasing syllable patterns for brandable names
    BRAND_PATTERNS = [
        'CVC', 'CV', 'CVV', 'CVCV', 'CVCC', 'CCVC', 'CCVV',
    ]
    
    # Tech-inspired endings
    TECH_ENDINGS = ['io', 'ly', 'fy', 'ix', 'ex', 'ox', 'ax', 'um', 'us', 'ia', 'eo', 'ara', 'ora', 'ura']
    
    def __init__(self, min_length: int = 4, max_length: int = 10, seed: Optional[int] = None):
        self.validator = WordValidator(min_length=min_length, max_length=max_length)
        self.min_length = min_length
        self.max_length = max_length
        if seed is not None:
            random.seed(seed)
    
    def _generate_syllable(self, simple: bool = False) -> str:
        """Generate a single syllable."""
        onset = random.choice(self.ONSETS)
        vowel = random.choice(self.SIMPLE_VOWELS if simple else self.VOWELS)
        
        # 50% chance of adding a coda
        coda = random.choice(self.CODAS) if random.random() > 0.5 else ''
        
        return onset + vowel + coda
    
    def _generate_brandable(self) -> str:
        """Generate a brandable word using syllable patterns."""
        num_syllables = random.randint(2, 3)
        word = ''
        
        for i in range(num_syllables):
            simple = i > 0  # First syllable can be complex
            syllable = self._generate_syllable(simple=simple)
            word += syllable
            
            if len(word) >= self.max_length:
                break
        
        # Sometimes add a tech ending
        if random.random() > 0.7 and len(word) <= self.max_length - 2:
            ending = random.choice(self.TECH_ENDINGS)
            # Remove last vowel if word ends in vowel
            if word[-1] in 'aeiou' and ending[0] in 'aeiou':
                word = word[:-1]
            word += ending
        
        return word[:self.max_length]
    
    def _generate_cv_pattern(self) -> str:
        """Generate word using strict CV alternation."""
        consonants = 'bcdfghjklmnprstvwz'
        vowels = 'aeiou'
        
        length = random.randint(self.min_length, min(8, self.max_length))
        word = ''
        
        # Start with consonant 70% of the time
        start_with_consonant = random.random() > 0.3
        
        for i in range(length):
            if (i % 2 == 0) == start_with_consonant:
                word += random.choice(consonants)
            else:
                word += random.choice(vowels)
        
        return word
    
    def generate(self, count: int = 100, method: str = 'mixed') -> List[str]:
        """Generate phonetically pleasing words.
        
        Args:
            count: Number of words to generate
            method: 'syllable', 'cv', or 'mixed'
        """
        candidates: Set[str] = set()
        attempts = 0
        max_attempts = count * 20
        
        while len(candidates) < count and attempts < max_attempts:
            attempts += 1
            
            if method == 'syllable':
                word = self._generate_brandable()
            elif method == 'cv':
                word = self._generate_cv_pattern()
            else:  # mixed
                word = self._generate_brandable() if random.random() > 0.4 else self._generate_cv_pattern()
            
            word = word.lower()
            
            if self.validator.is_valid(word) and word not in candidates:
                candidates.add(word)
        
        return list(candidates)
    
    def generate_with_prefix(self, prefix: str, count: int = 50) -> List[str]:
        """Generate words starting with a specific prefix."""
        candidates: Set[str] = set()
        attempts = 0
        max_attempts = count * 30
        
        remaining_length = self.max_length - len(prefix)
        if remaining_length < 2:
            return []
        
        while len(candidates) < count and attempts < max_attempts:
            attempts += 1
            
            # Generate suffix
            suffix_length = random.randint(2, min(6, remaining_length))
            suffix = self._generate_cv_pattern()[:suffix_length]
            
            word = prefix + suffix
            
            if self.validator.is_valid(word):
                candidates.add(word)
        
        return list(candidates)
    
    def generate_with_suffix(self, suffix: str, count: int = 50) -> List[str]:
        """Generate words ending with a specific suffix."""
        candidates: Set[str] = set()
        attempts = 0
        max_attempts = count * 30
        
        remaining_length = self.max_length - len(suffix)
        if remaining_length < 2:
            return []
        
        while len(candidates) < count and attempts < max_attempts:
            attempts += 1
            
            prefix_length = random.randint(2, min(6, remaining_length))
            prefix = self._generate_cv_pattern()[:prefix_length]
            
            word = prefix + suffix
            
            if self.validator.is_valid(word):
                candidates.add(word)
        
        return list(candidates)
