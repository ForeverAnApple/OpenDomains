"""Compound word generator for domain names."""

from typing import List, Set, Optional, Tuple
from ..utils.word_validator import WordValidator


class CompoundGenerator:
    """Generates compound words from word pairs."""
    
    # Adjectives that pair well with nouns
    ADJECTIVES = [
        'swift', 'bright', 'clear', 'quick', 'fast', 'smart', 'sharp', 'bold',
        'pure', 'true', 'deep', 'high', 'open', 'super', 'ultra', 'mega', 'mini',
        'prime', 'next', 'new', 'top', 'hot', 'cool', 'wild', 'free', 'easy'
    ]
    
    # Action verbs
    VERBS = [
        'build', 'ship', 'grow', 'flow', 'sync', 'link', 'push', 'pull', 'get',
        'run', 'fly', 'jump', 'spin', 'flip', 'snap', 'drop', 'pop', 'zip',
        'dash', 'rush', 'boost', 'launch', 'start', 'spark', 'craft', 'make'
    ]
    
    # Tech/product nouns
    NOUNS = [
        'app', 'hub', 'lab', 'box', 'pad', 'kit', 'base', 'dock', 'port', 'link',
        'node', 'core', 'flow', 'wave', 'code', 'data', 'byte', 'sync', 'stack',
        'cloud', 'pixel', 'spark', 'forge', 'mint', 'nest', 'hive', 'grid', 'mesh',
        'path', 'gate', 'bolt', 'beam', 'pulse', 'shift', 'scope', 'space', 'spot'
    ]
    
    # Second-part nouns that flow well
    SUFFIXES = [
        'ly', 'ify', 'ize', 'io', 'ai', 'hq', 'os', 'up', 'go', 'now', 'pro'
    ]
    
    def __init__(self, max_length: int = 15):
        self.validator = WordValidator(min_length=4, max_length=max_length)
        self.max_length = max_length
    
    def _flows_well(self, word1: str, word2: str) -> bool:
        """Check if two words flow well together."""
        if not word1 or not word2:
            return False
        
        combined = word1 + word2
        
        # Check total length
        if len(combined) > self.max_length:
            return False
        
        # Avoid double letters at junction (except common ones)
        junction = word1[-1] + word2[0]
        bad_junctions = ['aa', 'ii', 'uu', 'ww', 'yy', 'hh', 'jj', 'qq', 'vv', 'xx']
        if junction in bad_junctions:
            return False
        
        # Avoid awkward consonant clusters at junction
        vowels = set('aeiou')
        last_char = word1[-1]
        first_char = word2[0]
        
        # Three consonants in a row at junction is usually bad
        if (last_char not in vowels and first_char not in vowels and 
            len(word1) > 1 and word1[-2] not in vowels):
            return False
        
        return True
    
    def generate_adj_noun(self) -> List[str]:
        """Generate adjective + noun combinations."""
        candidates: Set[str] = set()
        
        for adj in self.ADJECTIVES:
            for noun in self.NOUNS:
                if self._flows_well(adj, noun):
                    compound = adj + noun
                    if self.validator.is_valid(compound):
                        candidates.add(compound)
        
        return list(candidates)
    
    def generate_verb_noun(self) -> List[str]:
        """Generate verb + noun combinations."""
        candidates: Set[str] = set()
        
        for verb in self.VERBS:
            for noun in self.NOUNS:
                if self._flows_well(verb, noun):
                    compound = verb + noun
                    if self.validator.is_valid(compound):
                        candidates.add(compound)
        
        return list(candidates)
    
    def generate_noun_noun(self) -> List[str]:
        """Generate noun + noun combinations."""
        candidates: Set[str] = set()
        
        for noun1 in self.NOUNS:
            for noun2 in self.NOUNS:
                if noun1 != noun2 and self._flows_well(noun1, noun2):
                    compound = noun1 + noun2
                    if self.validator.is_valid(compound):
                        candidates.add(compound)
        
        return list(candidates)
    
    def generate_with_suffix(self) -> List[str]:
        """Generate word + suffix combinations."""
        candidates: Set[str] = set()
        
        base_words = self.ADJECTIVES + self.VERBS + self.NOUNS
        
        for word in base_words:
            for suffix in self.SUFFIXES:
                if self._flows_well(word, suffix):
                    compound = word + suffix
                    if self.validator.is_valid(compound):
                        candidates.add(compound)
        
        return list(candidates)
    
    def generate_portmanteau(self, word1: str, word2: str) -> List[str]:
        """Generate portmanteau by blending two words."""
        candidates = []
        
        # Try overlapping endings/beginnings
        for i in range(1, min(len(word1), 4)):
            suffix = word1[-i:]
            for j in range(1, min(len(word2), 4)):
                prefix = word2[:j]
                if suffix == prefix:
                    # Found overlap
                    portmanteau = word1 + word2[j:]
                    if self.validator.is_valid(portmanteau):
                        candidates.append(portmanteau)
        
        # Try blending by cutting
        for i in range(len(word1) // 2, len(word1)):
            for j in range(1, len(word2) // 2 + 1):
                blend = word1[:i] + word2[j:]
                if self.validator.is_valid(blend):
                    candidates.append(blend)
        
        return candidates
    
    def generate_all(self) -> List[str]:
        """Generate all types of compound words."""
        candidates: Set[str] = set()
        
        candidates.update(self.generate_adj_noun())
        candidates.update(self.generate_verb_noun())
        candidates.update(self.generate_noun_noun())
        candidates.update(self.generate_with_suffix())
        
        return list(candidates)
    
    def generate_custom(self, first_words: List[str], second_words: List[str]) -> List[str]:
        """Generate compounds from custom word lists."""
        candidates: Set[str] = set()
        
        for word1 in first_words:
            for word2 in second_words:
                if self._flows_well(word1, word2):
                    compound = word1 + word2
                    if self.validator.is_valid(compound):
                        candidates.add(compound)
        
        return list(candidates)
