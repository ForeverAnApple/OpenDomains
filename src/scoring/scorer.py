"""Domain scoring system - prioritizing real-world brandability."""

from pathlib import Path
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass
from ..utils.word_validator import WordValidator


@dataclass
class DomainScore:
    """Detailed domain score breakdown.

    Database schema note: 'euphony' field may need to be added to schema
    (currently dictionary_score serves as meaning_score).
    """
    domain: str
    total_score: float
    pronounceability: int
    spellability: int
    length_score: int
    memorability: int
    brandability: int
    euphony: int  # NEW: pleasant sound and morpheme quality
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
                'euphony': self.euphony,
                'dictionary': self.dictionary_score
            },
            'tld_multiplier': self.tld_multiplier
        }


class DomainScorer:
    """Scores domains based on brandability and meaning."""

    # New weight distribution - prioritizes euphony and real words over phonetics
    DEFAULT_WEIGHTS = {
        'meaning': 0.30,      # was 0.35 (real words still important)
        'euphony': 0.20,      # NEW: pleasant sound and morpheme quality
        'brandability': 0.20, # was 0.25
        'memorability': 0.15, # was 0.20
        'length': 0.05,       # was 0.10 (reduced - longer words OK if euphonious)
        'pronounceability': 0.05,
        'spellability': 0.05
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

    # Common morphemes and suffixes
    COMMON_SUFFIXES = {
        'ify', 'ize', 'ise', 'ly', 'er', 'or', 'ist', 'ism',
        'ing', 'tion', 'sion', 'ness', 'ment', 'able', 'ible',
        'ful', 'less', 'ous', 'ive', 'ary', 'ery', 'ory', 'ity',
        'ance', 'ence', 'ant', 'ent', 'dom', 'hood', 'ship', 'ward'
    }

    COMMON_PREFIXES = {
        'pre', 'pro', 'con', 'dis', 'un', 're', 'mis', 'over', 'under',
        'sub', 'super', 'hyper', 'ultra', 'mega', 'multi', 'auto', 'bio',
        'eco', 'e', 'cyber', 'inter', 'trans', 'meta', 'micro', 'nano', 'neo'
    }

    # Expanded COMMON_WORDS set to ~200 words for brandability scoring
    COMMON_WORDS = {
        # Tech/startup vocabulary
        'tech', 'code', 'data', 'sync', 'link', 'node', 'core', 'stack',
        'mesh', 'cloud', 'flow', 'wave', 'bolt', 'dash', 'pulse', 'beam',
        'pixel', 'byte', 'grid', 'hub', 'lab', 'kit', 'box', 'pad', 'dock',
        'scope', 'gate', 'base', 'forge', 'hive', 'nest', 'port', 'vault',
        'zone', 'net', 'web', 'app', 'site', 'page', 'feed', 'chat', 'bot',

        # Action verbs
        'make', 'build', 'ship', 'grow', 'push', 'pull', 'snap', 'flip',
        'zoom', 'rush', 'jump', 'leap', 'shift', 'spark', 'flash', 'blast',
        'boost', 'launch', 'drive', 'forge', 'craft', 'mint', 'cast', 'spin',
        'run', 'go', 'fly', 'rise', 'lift', 'drop', 'pick', 'choose',
        'take', 'give', 'get', 'set', 'fix', 'mix', 'blend', 'join', 'meet',

        # Quality adjectives
        'swift', 'bright', 'clear', 'fast', 'quick', 'smart', 'sharp', 'bold',
        'pure', 'prime', 'ultra', 'mega', 'super', 'hyper', 'omni', 'multi',
        'flex', 'open', 'free', 'easy', 'simple', 'next', 'new', 'true',
        'deep', 'high', 'wide', 'grand', 'royal', 'prime', 'top', 'best',

        # Nature nouns (create imagery)
        'sun', 'moon', 'star', 'sky', 'wind', 'fire', 'ice', 'storm',
        'rain', 'snow', 'leaf', 'tree', 'rock', 'stone', 'river', 'ocean',
        'peak', 'hill', 'vale', 'field', 'lake', 'bay', 'dawn', 'dusk',

        # Abstract concepts
        'mind', 'soul', 'spirit', 'dream', 'vision', 'quest', 'path', 'way',
        'light', 'dark', 'time', 'space', 'void', 'edge', 'apex', 'root',
        'seed', 'idea', 'notion', 'thought', 'sense', 'spark', 'glow',

        # Short brandable words
        'ace', 'jet', 'sky', 'red', 'blue', 'green', 'gold', 'silver',
        'key', 'lock', 'door', 'map', 'guide', 'tour', 'trip', 'ride',
        'shop', 'store', 'trade', 'sale', 'deal', 'buy', 'sell', 'bid',
        'cash', 'pay', 'bank', 'coin', 'fund', 'cap', 'share', 'stock'
    }

    # Compound word detection set - ~200 short words (3-6 chars)
    COMPOUND_WORDS = {
        # Tech words
        'code', 'data', 'sync', 'link', 'node', 'core', 'stack', 'mesh',
        'cloud', 'flow', 'wave', 'bolt', 'dash', 'pulse', 'beam', 'pixel',
        'byte', 'grid', 'hub', 'lab', 'kit', 'box', 'pad', 'dock', 'scope',
        'gate', 'base', 'forge', 'hive', 'nest', 'port', 'vault', 'zone',
        'tech', 'soft', 'hard', 'ware', 'app', 'web', 'net', 'sys',

        # Action words
        'make', 'build', 'ship', 'grow', 'push', 'pull', 'snap', 'flip',
        'zoom', 'rush', 'jump', 'leap', 'shift', 'spark', 'flash', 'blast',
        'boost', 'launch', 'drive', 'forge', 'craft', 'mint', 'cast', 'spin',

        # Quality words
        'swift', 'bright', 'clear', 'fast', 'quick', 'smart', 'sharp', 'bold',
        'pure', 'prime', 'ultra', 'mega', 'super', 'flex', 'open', 'free',
        'easy', 'simple', 'next', 'new', 'true', 'deep', 'high', 'wide',

        # Nature words
        'sun', 'moon', 'star', 'sky', 'wind', 'fire', 'ice', 'storm',
        'rain', 'snow', 'leaf', 'tree', 'rock', 'stone', 'river', 'ocean',
        'wave', 'peak', 'hill', 'vale',

        # Abstract words
        'mind', 'soul', 'dream', 'vision', 'quest', 'path', 'way', 'light',
        'dark', 'time', 'space', 'void', 'edge', 'apex', 'core', 'root', 'seed',

        # Short common words
        'go', 'run', 'fly', 'rise', 'lift', 'drop', 'top', 'best', 'ace',
        'key', 'lock', 'map', 'guide', 'tour', 'trip', 'ride', 'shop',

        # Additional brandable short words
        'bit', 'dot', 'pin', 'tap', 'tag', 'cut', 'fix', 'mix', 'fit',
        'set', 'get', 'let', 'put', 'bet', 'win', 'hit', 'hot', 'cool',
        'warm', 'cold', 'big', 'small', 'long', 'short', 'wide', 'narrow',

        # Business words
        'pay', 'cash', 'bank', 'fund', 'cap', 'trade', 'deal', 'sale',
        'shop', 'store', 'mart', 'post', 'mail', 'send', 'ship', 'order',
        'book', 'list', 'note', 'word', 'text', 'file', 'save', 'load'
    }

    # Tech-related morphemes for brandability
    TECH_MORPHEMES = {
        'tech', 'soft', 'ware', 'byte', 'bit', 'data', 'code', 'app', 'web',
        'net', 'cyber', 'digit', 'pixel', 'bot', 'auto', 'smart', 'intelli',
        'logic', 'algo', 'cloud', 'sync', 'link', 'node', 'hub', 'grid'
    }

    # Action-related morphemes
    ACTION_MORPHEMES = {
        'go', 'run', 'do', 'make', 'get', 'set', 'fix', 'move', 'flow',
        'push', 'pull', 'drive', 'ride', 'fly', 'jump', 'leap', 'rise',
        'boost', 'lift', 'grow', 'build', 'make', 'craft', 'forge', 'spin'
    }

    # Greek/Latin morphemes that sound sophisticated
    GREEK_LATIN_MORPHEMES = {
        # Prefixes
        'anti', 'auto', 'bio', 'chrono', 'crypto', 'cyber', 'dyna', 'eco',
        'electro', 'geo', 'hyper', 'meta', 'micro', 'mono', 'multi', 'neo',
        'omni', 'pan', 'para', 'photo', 'poly', 'proto', 'pseudo', 'psycho',
        'quasi', 'retro', 'semi', 'syn', 'tele', 'trans', 'ultra', 'uni',
        # Roots
        'aero', 'aqua', 'arch', 'astra', 'astro', 'audio', 'cardi', 'centric',
        'chrom', 'cogn', 'cosm', 'crat', 'crypt', 'cycl', 'demo', 'derm',
        'dict', 'dox', 'duc', 'dynam', 'endo', 'erg', 'eth', 'ethos', 'eu',
        'flux', 'form', 'fract', 'gen', 'glyph', 'gnos', 'graph', 'grav',
        'helio', 'hemi', 'hetero', 'homo', 'hydro', 'iso', 'kine', 'lith',
        'log', 'logos', 'luc', 'lum', 'luna', 'magn', 'manu', 'mech', 'morph',
        'naut', 'nav', 'necro', 'neur', 'nom', 'nova', 'nox', 'ocul', 'onym',
        'opt', 'ora', 'orth', 'path', 'ped', 'pend', 'phil', 'phon', 'phor',
        'phot', 'phys', 'plex', 'polis', 'port', 'pos', 'prim', 'pyr', 'quant',
        'radi', 'rupt', 'scop', 'scrib', 'sect', 'sens', 'sol', 'soph', 'spec',
        'spect', 'spir', 'stat', 'stell', 'struct', 'tact', 'techn', 'temp',
        'terra', 'therm', 'thesis', 'trop', 'typ', 'umbr', 'vac', 'val', 'ven',
        'ver', 'vid', 'vis', 'vit', 'voc', 'vol', 'xen', 'zer', 'zo',
        # Suffixes that sound good
        'tion', 'sion', 'ism', 'ist', 'ity', 'ous', 'ive', 'ary', 'ory',
        'ment', 'ness', 'able', 'ible', 'ful', 'less', 'ward', 'wise',
        'oid', 'esque', 'ine', 'ene', 'ase', 'ose', 'ule', 'cule',
        'ia', 'io', 'ium', 'ius', 'us', 'um', 'is', 'ix', 'ex', 'ax', 'ox',
        'al', 'el', 'il', 'ol', 'ul', 'ar', 'er', 'ir', 'or', 'ur',
        'an', 'en', 'in', 'on', 'un', 'ic', 'ac', 'tic', 'nic',
        'ent', 'ant', 'ence', 'ance', 'ency', 'ancy',
        # Pleasant sound clusters
        'phr', 'chr', 'sph', 'nth', 'mph', 'nch', 'rch', 'lch',
    }

    # Euphonic patterns - letter combinations that sound pleasing
    EUPHONIC_PATTERNS = {
        # Flowing consonant-vowel patterns
        'ela', 'elo', 'eli', 'ila', 'ilo', 'ola', 'ula', 'ulo',
        'ara', 'era', 'ira', 'ora', 'ura', 'ari', 'eri', 'ori', 'uri',
        'ana', 'ena', 'ina', 'ona', 'una', 'ani', 'eni', 'ini', 'oni',
        'ata', 'eta', 'ita', 'ota', 'uta', 'ati', 'eti', 'iti', 'oti',
        # Soft endings
        'ia', 'io', 'eo', 'ea', 'ae', 'ei', 'ie',
        # Liquid consonants (l, r) with vowels
        'le', 'la', 'li', 'lo', 'lu', 'ly',
        're', 'ra', 'ri', 'ro', 'ru', 'ry',
        # Nasal consonants (m, n) with vowels
        'ma', 'me', 'mi', 'mo', 'mu', 'my',
        'na', 'ne', 'ni', 'no', 'nu', 'ny',
        # Sibilants that flow
        'sa', 'se', 'si', 'so', 'su', 'sy',
        'za', 'ze', 'zi', 'zo', 'zu', 'zy',
        # Voiced stops that sound strong
        'ba', 'be', 'bi', 'bo', 'bu', 'by',
        'da', 'de', 'di', 'do', 'du', 'dy',
        'ga', 'ge', 'gi', 'go', 'gu', 'gy',
        # Pleasant combinations
        'ven', 'vin', 'van', 'vel', 'val', 'vol',
        'zen', 'zan', 'zin', 'zel', 'zal', 'zol',
        'pher', 'ther', 'spher', 'chron', 'tron',
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
        """Load dictionary words from wordlist file."""
        if self._dictionary is not None:
            return self._dictionary

        self._dictionary = set()
        if self.WORDLIST_PATH.exists():
            with open(self.WORDLIST_PATH, 'r') as f:
                self._dictionary = {line.strip().lower() for line in f if line.strip()}
        return self._dictionary

    def _is_gibberish(self, word: str) -> bool:
        """Detect if word is likely random syllables without meaning."""
        word_lower = word.lower()
        dictionary = self._load_dictionary()

        # Check for real word substring (4+ chars)
        has_word_substring = False
        for i in range(len(word) - 3):
            substring = word_lower[i:i+4]
            if substring in dictionary or substring in self.COMPOUND_WORDS:
                has_word_substring = True
                break

        # Check for common morphemes
        has_morpheme = any(m in word_lower for m in self.COMMON_SUFFIXES) or \
                       any(m in word_lower for m in self.COMMON_PREFIXES)

        # Check for simple CVCVCV pattern with no meaning
        vowels = set('aeiou')
        consonants = set('bcdfghjklmnpqrstvwxyz')

        # If it has recognizable parts, it's not gibberish
        if has_word_substring or has_morpheme:
            return False

        # Check if it follows simple alternating pattern with no real words
        if len(word) >= 5:
            alternating_count = 0
            for i in range(len(word) - 2):
                cv_pattern = ''
                for c in word[i:i+3]:
                    cv_pattern += 'v' if c in vowels else 'c'
                if cv_pattern in ['cvc', 'vcv']:
                    alternating_count += 1

            # If it's mostly alternating with no real words, mark as gibberish
            if alternating_count >= len(word) // 2:
                return True

        return False

    def _score_meaning(self, word: str) -> int:
        """Score meaning - 100 for real words, 0 for random syllables."""
        word_lower = word.lower()
        dictionary = self._load_dictionary()

        # 100: Exact match in dictionary or COMMON_WORDS
        if word_lower in dictionary or word_lower in self.COMMON_WORDS:
            return 100

        # 85: Recognized compound word (two real words combined)
        # More strict: both parts should be dictionary words or COMMON_WORDS
        # Only check splits where both parts are at least 3 chars
        for split_pos in range(3, len(word) - 2):
            first = word_lower[:split_pos]
            second = word_lower[split_pos:]

            # Require both parts to be at least 3 chars
            if len(first) < 3 or len(second) < 3:
                continue

            # Strict compound: both parts are dictionary words (4+ chars preferred)
            # or at least one is in COMMON_WORDS
            first_is_real = (first in dictionary and len(first) >= 4) or first in self.COMMON_WORDS
            second_is_real = (second in dictionary and len(second) >= 4) or second in self.COMMON_WORDS

            if first_is_real and second_is_real:
                # Both parts are recognizable words - compound detected
                return 85

        # 70: Real word + common suffix
        for suffix in self.COMMON_SUFFIXES:
            if word_lower.endswith(suffix) and len(word_lower) > len(suffix) + 3:
                root = word_lower[:-len(suffix)]
                if len(root) >= 3 and (root in dictionary or root in self.COMMON_WORDS):
                    return 70

        # 70: Common prefix + real word
        for prefix in self.COMMON_PREFIXES:
            if word_lower.startswith(prefix) and len(word_lower) > len(prefix) + 3:
                root = word_lower[len(prefix):]
                if len(root) >= 3 and (root in dictionary or root in self.COMMON_WORDS):
                    return 70

        # 50: Contains a real word as substring (at least 4 chars, minimum 4+2=6 total)
        if len(word) >= 6:
            for i in range(len(word) - 3):
                substring = word_lower[i:i+4]
                if substring in dictionary or substring in self.COMMON_WORDS:
                    return 50
                # Try 5-char substrings too
                if i < len(word) - 4:
                    substring5 = word_lower[i:i+5]
                    if substring5 in dictionary or substring5 in self.COMMON_WORDS:
                        return 50

        # 20: Has common morphemes but no real word
        if any(m in word_lower for m in self.COMMON_SUFFIXES) or \
           any(m in word_lower for m in self.COMMON_PREFIXES):
            return 20

        # 0: Random syllables with no recognizable parts
        return 0

    def _score_brandability(self, word: str) -> int:
        """Score brandability - favors real words and tech associations."""
        score = 40  # Base score
        word_lower = word.lower()
        is_gibberish = self._is_gibberish(word)
        dictionary = self._load_dictionary()

        # -20: Sounds like gibberish (no real word parts, random CVCV pattern)
        if is_gibberish:
            score -= 20

        # +20: Is a real word or compound
        if word_lower in dictionary or word_lower in self.COMMON_WORDS:
            score += 20
        else:
            # Check for compound - use strict detection
            for split_pos in range(3, len(word) - 2):
                first = word_lower[:split_pos]
                second = word_lower[split_pos:]

                if len(first) < 3 or len(second) < 3:
                    continue

                first_is_real = (first in dictionary and len(first) >= 4) or first in self.COMMON_WORDS
                second_is_real = (second in dictionary and len(second) >= 4) or second in self.COMMON_WORDS

                if first_is_real and second_is_real:
                    score += 20
                    break

        # +15: Evokes tech/innovation
        has_tech = any(m in word_lower for m in self.TECH_MORPHEMES)
        if has_tech:
            score += 15

        # +10: Evokes action/energy
        has_action = any(m in word_lower for m in self.ACTION_MORPHEMES) or \
                     any(s in word_lower for s in self.COMMON_SUFFIXES)
        if has_action:
            score += 10

        # +10: Good brand phonetics - starts with strong consonant
        strong_starts = 'bcdfgklmpstvz'
        if word_lower[0] in strong_starts:
            score += 10

        # +10: Pleasant ending
        pleasant_ends = 'aeiouy'
        pleasant_endings = {'ly', 'er', 'le', 'ia', 'io'}
        if word_lower[-1] in pleasant_ends:
            score += 10
        elif any(word_lower.endswith(e) for e in pleasant_endings):
            score += 10

        # -10: Hard to say in a sentence
        # Words with many rare consonant combinations are hard
        awkward_count = 0
        for i in range(len(word) - 1):
            bigram = word_lower[i:i+2]
            if bigram not in 'thheinreatondstionelngshar':
                awkward_count += 1

        if awkward_count > len(word) / 2:
            score -= 10

        return max(0, min(100, score))

    def _score_memorability(self, word: str) -> int:
        """Score memorability - favors real words and compounds."""
        score = 30  # Base score
        word_lower = word.lower()
        is_gibberish = self._is_gibberish(word)
        dictionary = self._load_dictionary()

        # +40: Is a real English word
        if word_lower in dictionary:
            score += 40

        # +30: Is a meaningful compound (strict detection)
        if word_lower not in dictionary:
            for split_pos in range(3, len(word) - 2):
                first = word_lower[:split_pos]
                second = word_lower[split_pos:]

                if len(first) < 3 or len(second) < 3:
                    continue

                first_is_real = (first in dictionary and len(first) >= 4) or first in self.COMMON_WORDS
                second_is_real = (second in dictionary and len(second) >= 4) or second in self.COMMON_WORDS

                if first_is_real and second_is_real:
                    score += 30
                    break

        # +20: Creates mental imagery (nature words)
        nature_words = {'sun', 'moon', 'star', 'sky', 'wind', 'fire', 'ice',
                        'storm', 'rain', 'snow', 'leaf', 'tree', 'rock', 'stone',
                        'river', 'ocean', 'wave', 'peak', 'hill', 'dawn', 'dusk',
                        'cloud', 'spark', 'glow', 'beam', 'light', 'flash'}
        if any(n in word_lower for n in nature_words):
            score += 20

        # +15: Short and punchy (4-6 chars)
        if 4 <= len(word) <= 6:
            score += 15

        # -30: Generic syllable pattern (CVCVCV with no meaning)
        if is_gibberish:
            score -= 30
        else:
            # Check if it has distinctive features
            # Words in dictionary or COMMON_WORDS are distinctive
            if word_lower not in dictionary and word_lower not in self.COMMON_WORDS:
                # Check if it's a compound
                is_compound = False
                for split_pos in range(3, len(word) - 2):
                    first = word_lower[:split_pos]
                    second = word_lower[split_pos:]

                    if len(first) < 3 or len(second) < 3:
                        continue

                    first_is_real = (first in dictionary and len(first) >= 4) or first in self.COMMON_WORDS
                    second_is_real = (second in dictionary and len(second) >= 4) or second in self.COMMON_WORDS

                    if first_is_real and second_is_real:
                        is_compound = True
                        break

                if not is_compound:
                    # -20: Forgettable (no distinctive features)
                    score -= 20

        return max(0, min(100, score))

    def _score_length(self, word: str) -> int:
        """Score based on word length - updated for euphony focus."""
        length = len(word)

        if 4 <= length <= 7:
            return 100
        elif length in (8, 9):
            return 90
        elif length == 10:
            return 80
        elif 11 <= length <= 12:
            return 70
        elif length < 4:
            return 50
        else:  # > 12
            return 40

    def _score_euphony(self, word: str) -> int:
        """Score euphony - pleasant sound and Greek/Latin morpheme quality."""
        score = 50  # Base score
        word_lower = word.lower()
        vowels = set('aeiou')

        # +5 for each Greek/Latin morpheme found (max +30)
        morpheme_count = 0
        for morpheme in self.GREEK_LATIN_MORPHEMES:
            if morpheme in word_lower:
                morpheme_count += 1
        score += min(30, morpheme_count * 5)

        # +3 for each euphonic pattern found (max +20)
        pattern_count = 0
        for pattern in self.EUPHONIC_PATTERNS:
            if pattern in word_lower:
                pattern_count += 1
        score += min(20, pattern_count * 3)

        # +10 if word has good "flow" (alternating stress pattern)
        # BUT only if word has at least one Greek/Latin morpheme
        cv_score = 0
        for i in range(len(word_lower) - 1):
            curr_is_vowel = word_lower[i] in vowels
            next_is_vowel = word_lower[i + 1] in vowels
            if curr_is_vowel != next_is_vowel:
                cv_score += 1
        # Good flow if >60% of pairs alternate AND has morphemes
        if cv_score / max(1, len(word_lower) - 1) > 0.6 and morpheme_count > 0:
            score += 10

        # +10 if word ends pleasantly
        pleasant_endings = {
            'a', 'e', 'i', 'o', 'u', 'y',  # Vowels
            'ly', 'er', 'le', 'ia', 'io', 'us', 'um', 'is'
        }
        if any(word_lower.endswith(end) for end in pleasant_endings):
            score += 10

        # -20 if word has harsh consonant clusters
        harsh_clusters = {'kg', 'gk', 'dk', 'kd', 'bp', 'pb', 'kp', 'pk',
                         'tg', 'gt', 'dt', 'td', 'xb', 'bx', 'xc', 'cx'}
        harsh_count = 0
        for cluster in harsh_clusters:
            if cluster in word_lower:
                harsh_count += 1
        score -= min(20, harsh_count * 20)

        # -30 if detected as random CVCVCV gibberish with no morphemes
        is_gibberish = self._is_gibberish(word)
        if is_gibberish and morpheme_count == 0:
            score -= 30

        # Extra penalty: if purely alternating CV pattern with no morphemes and no real words
        # This catches simple CVCVCV patterns like "bebade", "pepufo"
        if morpheme_count == 0:
            # Check if it's a simple alternating pattern
            cv_pattern = ''.join('v' if c in vowels else 'c' for c in word_lower)
            if 'cvcvcv' in cv_pattern or 'vcvcvc' in cv_pattern:
                # It's a simple alternating pattern with no morphemes - penalize heavily
                score -= 20

        return max(0, min(100, score))

    def _get_word_and_tld(self, domain: str) -> tuple[str, str]:
        """Extract word and TLD from domain."""
        parts = domain.lower().split('.')
        if len(parts) >= 2:
            return parts[0], parts[-1]
        return domain, ''

    def score(self, domain: str) -> DomainScore:
        """Calculate comprehensive score for a domain."""
        word, tld = self._get_word_and_tld(domain)

        # Get individual scores
        pronounceability = self.validator.get_pronounceability_score(word)
        spellability = self.validator.get_spellability_score(word)
        length_score = self._score_length(word)
        memorability = self._score_memorability(word)
        brandability = self._score_brandability(word)
        euphony = self._score_euphony(word)  # NEW: euphony scoring
        dictionary_score = self._score_meaning(word)  # Field name preserved for DB compatibility

        # Calculate weighted score with new weights
        raw_score = (
            pronounceability * self.weights['pronounceability'] +
            spellability * self.weights['spellability'] +
            length_score * self.weights['length'] +
            memorability * self.weights['memorability'] +
            brandability * self.weights['brandability'] +
            euphony * self.weights['euphony'] +  # NEW: euphony weight
            dictionary_score * self.weights['meaning']
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
            euphony=euphony,  # NEW: euphony field
            dictionary_score=dictionary_score,  # Field name preserved
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
