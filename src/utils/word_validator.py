"""Word validation and filtering utilities."""

import re
from typing import Set

# Difficult consonant clusters to avoid
DIFFICULT_CLUSTERS = {
    'xq', 'zx', 'qx', 'vx', 'bx', 'dx', 'fx', 'gx', 'hx', 'jx', 'kx', 'lx',
    'mx', 'nx', 'px', 'rx', 'sx', 'tx', 'wx', 'zq', 'qz', 'vq', 'qv',
    'bq', 'dq', 'fq', 'gq', 'hq', 'jq', 'kq', 'lq', 'mq', 'nq', 'pq',
    'rq', 'sq', 'tq', 'wq', 'xhr', 'xhl', 'xhn', 'zhr', 'zhl', 'zhn',
    'pfr', 'pfl', 'scht', 'tsch', 'dsch', 'czk', 'szc', 'szcz'
}

# Common English bigrams - high frequency = natural sounding
COMMON_BIGRAMS = {
    'th', 'he', 'in', 'er', 'an', 're', 'on', 'at', 'en', 'nd',
    'ti', 'es', 'or', 'te', 'of', 'ed', 'is', 'it', 'al', 'ar',
    'st', 'to', 'nt', 'ng', 'se', 'ha', 'as', 'ou', 'io', 'le',
    'no', 've', 'co', 'me', 'de', 'hi', 'ri', 'ro', 'ic', 'ne',
    'ea', 'ra', 'ce', 'li', 'ch', 'be', 'ma', 'si', 'om', 'ur',
    'ta', 'la', 'el', 'so', 'na', 'pe', 'ni', 'lo', 'us', 'ad',
    'wa', 'ge', 'id', 'un', 'op', 'ow', 'vi', 'mo', 'we', 'da',
    'po', 'pa', 'ca', 'do', 'up', 'ke', 'go', 'di', 'fo', 'ol',
    'oo', 'ee', 'ai', 'ay', 'ey', 'oy', 'ab', 'ob', 'ub', 'ib',
    'am', 'im', 'um', 'em', 'ap', 'ip', 'ep', 'ot', 'ut', 'et',
    'ag', 'ig', 'og', 'ug', 'eg', 'ak', 'ik', 'ok', 'uk', 'ek',
}

# Rare/awkward bigrams - penalize these heavily
AWKWARD_BIGRAMS = {
    # j in awkward positions (j almost never ends English words)
    'aj', 'ej', 'ij', 'oj', 'uj', 'bj', 'cj', 'dj', 'fj', 'gj',
    'hj', 'kj', 'lj', 'mj', 'nj', 'pj', 'rj', 'sj', 'tj', 'vj',
    'wj', 'xj', 'yj', 'zj', 'jb', 'jc', 'jd', 'jf', 'jg', 'jh',
    'jk', 'jl', 'jm', 'jn', 'jp', 'jq', 'jr', 'js', 'jt', 'jv',
    'jw', 'jx', 'jy', 'jz',
    # w in awkward positions
    'iw', 'uw', 'wf', 'wg', 'wk', 'wm', 'wp', 'wt', 'wv', 'wz',
    # q without u
    'qa', 'qe', 'qi', 'qo', 'qy', 'qb', 'qc', 'qd', 'qf', 'qg',
    'qh', 'qj', 'qk', 'ql', 'qm', 'qn', 'qp', 'qr', 'qs', 'qt',
    'qv', 'qw', 'qx', 'qy', 'qz',
    # x in awkward positions
    'xb', 'xd', 'xf', 'xg', 'xj', 'xk', 'xl', 'xm', 'xn', 'xq',
    'xr', 'xs', 'xv', 'xw', 'xz',
    # z in awkward positions
    'zb', 'zc', 'zd', 'zf', 'zg', 'zj', 'zk', 'zm', 'zn', 'zp',
    'zq', 'zr', 'zs', 'zt', 'zv', 'zw', 'zx',
    # Other awkward consonant clusters
    'vh', 'vk', 'vp', 'vt', 'vw', 'vz',
    'hk', 'hm', 'hp', 'ht', 'hv', 'hw', 'hz',
    'kg', 'kp', 'kv', 'kz',
    'bk', 'bp', 'bv', 'bz', 'bg',
    'dk', 'dv', 'dz', 'dg',
    'fv', 'fz', 'fg',
    'gk', 'gp', 'gv', 'gz',
    'mk', 'mv', 'mz', 'mg',
    'pk', 'pv', 'pz', 'pg',
    'tk', 'tv', 'tz', 'tg',
}

# Strong valid English word endings (very common, natural)
STRONG_ENDINGS = {
    # Common word-final patterns (2-4 chars)
    'le', 'ly', 'ty', 'ry', 'ny', 'dy', 'fy', 'gy', 'ky', 'my', 'py', 'sy', 'zy',
    'er', 'or', 'ar', 'ir', 'ur',
    'en', 'on', 'an', 'in', 'un',
    'ed', 'es', 'ds', 'ps', 'ks', 'ns', 'rs', 'ls', 'ms', 'gs', 'bs', 'ts',
    'ow', 'ew', 'aw',
    'ay', 'ey', 'oy',
    've', 'se', 'te', 'de', 'ge', 'ke', 'me', 'ne', 'pe', 're', 'ze', 'ce', 'be',
    'al', 'el', 'il', 'ol', 'ul',
    'ch', 'ck', 'ct', 'dge', 'ft', 'gh', 'ld', 'lf', 'lk', 'lm', 'ln', 'lp',
    'lt', 'mp', 'nce', 'nch', 'nd', 'ng', 'nk', 'nse', 'nt', 'pt', 'rb',
    'rce', 'rch', 'rd', 'rf', 'rg', 'rk', 'rl', 'rm', 'rn', 'rp', 'rse',
    'rt', 'rve', 'sh', 'sk', 'sm', 'sp', 'ss', 'st', 'tch', 'th',
    'ize', 'ise', 'ous', 'ive', 'ble', 'tle', 'dle', 'gle', 'ple', 'fle',
    'ful', 'less', 'ness', 'ment', 'tion', 'sion', 'ing', 'ling', 'ting',
    'am', 'em', 'im', 'om', 'um',
    'ab', 'eb', 'ib', 'ob', 'ub',
    'ad', 'id', 'od', 'ud',
    'ag', 'eg', 'ig', 'og', 'ug',
    'ap', 'ep', 'ip', 'op', 'up',
    'at', 'et', 'it', 'ot', 'ut',
    'ax', 'ex', 'ix', 'ox',
    # Vowel endings
    'a', 'e', 'i', 'o', 'y',
    # Strong consonant endings
    'b', 'd', 'k', 'l', 'm', 'n', 'p', 'r', 's', 't',
}

# Weak endings - technically valid but unusual, warrant slight penalty
WEAK_ENDINGS = {
    'f', 'g', 'x', 'z', 'u',  # Less common final letters
    'af', 'ef', 'if', 'of', 'uf',  # f after vowel is rare
    'az', 'ez', 'iz', 'oz', 'uz',  # z after vowel
    'ux',  # rare
}

# Invalid word endings - these almost never end English words
INVALID_ENDINGS = {
    'j', 'q', 'v', 'w',  # Almost never end English words (w only in borrowed words)
    'uj', 'ij', 'aj', 'oj', 'ej',  # j after vowel is extremely rare
    'iw', 'uw',  # w after i/u is awkward (aw, ew, ow are exceptions but need vowel before)
    'ww', 'jj', 'qq', 'vv',  # Double rare consonants
    'zf', 'zg', 'zh', 'zk', 'zl', 'zm', 'zn', 'zp', 'zr', 'zt', 'zv', 'zw',
    'wf', 'wg', 'wk', 'wl', 'wm', 'wn', 'wp', 'wr', 'wt', 'wv', 'wz',
    'jf', 'jg', 'jk', 'jl', 'jm', 'jn', 'jp', 'jr', 'jt', 'jv', 'jw', 'jz',
}

# Awkward letter sequences anywhere in word (broader than just endings)
AWKWARD_SEQUENCES = {
    'wew', 'zuf', 'zaf', 'xuf', 'vuf',  # specific awkward combos
    'juw', 'jow', 'jew', 'jaw', 'jiw',
    'yiy', 'yuy', 'yoy',
    'uvu', 'ovo', 'ivi',
    'iwh', 'awh', 'uwh',  # wh after vowel is odd
    'oaf', 'oach', 'ihag',  # nonsense syllables
    'froa', 'ploa',  # unusual onset+vowel
}

# Common offensive word patterns to filter
OFFENSIVE_PATTERNS = {
    'fuck', 'shit', 'damn', 'hell', 'ass', 'bitch', 'cunt', 'dick', 'cock',
    'porn', 'xxx', 'sex', 'nazi', 'rape', 'kill', 'hate', 'slut', 'whore'
}

VOWELS = set('aeiou')
CONSONANTS = set('bcdfghjklmnpqrstvwxyz')


class WordValidator:
    """Validates words for domain suitability."""
    
    def __init__(self, min_length: int = 4, max_length: int = 12):
        self.min_length = min_length
        self.max_length = max_length
    
    def is_valid(self, word: str) -> bool:
        """Check if word passes all validation criteria."""
        word = word.lower().strip()
        
        if not self._check_length(word):
            return False
        if not self._check_characters(word):
            return False
        if self._contains_offensive(word):
            return False
        if self._has_difficult_clusters(word):
            return False
        if not self._is_pronounceable(word):
            return False
        
        return True
    
    def _check_length(self, word: str) -> bool:
        return self.min_length <= len(word) <= self.max_length
    
    def _check_characters(self, word: str) -> bool:
        """Only allow lowercase letters and occasional numbers."""
        return bool(re.match(r'^[a-z]+[0-9]?$', word) or re.match(r'^[a-z]+$', word))
    
    def _contains_offensive(self, word: str) -> bool:
        for pattern in OFFENSIVE_PATTERNS:
            if pattern in word:
                return True
        return False
    
    def _has_difficult_clusters(self, word: str) -> bool:
        word_lower = word.lower()
        for cluster in DIFFICULT_CLUSTERS:
            if cluster in word_lower:
                return True
        return False
    
    def _is_pronounceable(self, word: str) -> bool:
        """Check if word has reasonable vowel/consonant distribution."""
        if len(word) < 2:
            return False
        
        vowel_count = sum(1 for c in word if c in VOWELS)
        consonant_count = len(word) - vowel_count
        
        # Must have at least one vowel
        if vowel_count == 0:
            return False
        
        # Check for too many consecutive consonants (max 3)
        max_consecutive_consonants = 0
        current_consonants = 0
        for c in word:
            if c in CONSONANTS:
                current_consonants += 1
                max_consecutive_consonants = max(max_consecutive_consonants, current_consonants)
            else:
                current_consonants = 0
        
        if max_consecutive_consonants > 3:
            return False
        
        # Check for too many consecutive vowels (max 2)
        max_consecutive_vowels = 0
        current_vowels = 0
        for c in word:
            if c in VOWELS:
                current_vowels += 1
                max_consecutive_vowels = max(max_consecutive_vowels, current_vowels)
            else:
                current_vowels = 0
        
        if max_consecutive_vowels > 2:
            return False
        
        # Reasonable ratio
        ratio = vowel_count / len(word)
        if ratio < 0.2 or ratio > 0.7:
            return False
        
        return True
    
    def get_pronounceability_score(self, word: str) -> int:
        """Score pronounceability from 0-100 using English phonotactics."""
        if not word:
            return 0
        
        score = 100
        word = word.lower()
        
        # === Vowel ratio check (less aggressive than before) ===
        vowel_count = sum(1 for c in word if c in VOWELS)
        ratio = vowel_count / len(word)
        
        # Ideal ratio is 0.35-0.45, penalize deviation less harshly
        if ratio < 0.2 or ratio > 0.6:
            score -= 25  # Heavy penalty for extreme ratios
        elif ratio < 0.3 or ratio > 0.5:
            score -= 10  # Moderate penalty
        
        # === Consecutive consonant check ===
        max_cons = 0
        current = 0
        for c in word:
            if c in CONSONANTS:
                current += 1
                max_cons = max(max_cons, current)
            else:
                current = 0
        
        if max_cons > 3:
            score -= (max_cons - 3) * 20
        elif max_cons > 2:
            score -= 5
        
        # === Word ending check (important for natural sound) ===
        has_strong_ending = False
        has_weak_ending = False
        has_invalid_ending = False
        
        # Check for strong endings first (longest match wins)
        for length in [4, 3, 2, 1]:
            if len(word) >= length:
                ending = word[-length:]
                if ending in STRONG_ENDINGS:
                    has_strong_ending = True
                    break
                if ending in WEAK_ENDINGS:
                    has_weak_ending = True
        
        # Check for invalid endings
        for length in [3, 2, 1]:
            if len(word) >= length:
                ending = word[-length:]
                if ending in INVALID_ENDINGS:
                    has_invalid_ending = True
                    break
        
        # Check for awkward sequences anywhere in word
        awkward_seq_count = sum(1 for seq in AWKWARD_SEQUENCES if seq in word)
        
        # Apply penalties (these stack, not mutually exclusive)
        if has_invalid_ending:
            score -= 35
        
        if awkward_seq_count > 0:
            score -= 20 * awkward_seq_count  # Penalty per awkward sequence
        
        if has_weak_ending and not has_strong_ending:
            score -= 15
        elif not has_strong_ending and not has_invalid_ending:
            score -= 10
        
        # === Bigram analysis ===
        common_count = 0
        awkward_count = 0
        total_bigrams = len(word) - 1
        
        for i in range(total_bigrams):
            bigram = word[i:i+2]
            if bigram in COMMON_BIGRAMS:
                common_count += 1
            if bigram in AWKWARD_BIGRAMS:
                awkward_count += 1
        
        # Bonus for common bigrams (natural English flow)
        # Only give bonus if no awkward bigrams AND no awkward sequences
        if total_bigrams > 0 and awkward_count == 0 and awkward_seq_count == 0:
            common_ratio = common_count / total_bigrams
            score += int(common_ratio * 15)
        
        # Penalty for awkward bigrams (heavier penalty)
        score -= awkward_count * 20
        
        # === Length-based skepticism for long words ===
        # Longer made-up words are more likely to be unpronounceable
        # Real long words have recognizable morphemes
        if len(word) >= 8:
            # Check for common morphemes/patterns
            has_morpheme = any(m in word for m in [
                'ing', 'tion', 'ness', 'ment', 'able', 'ible', 'ful', 'less',
                'ize', 'ise', 'ous', 'ive', 'ary', 'ery', 'ory', 'ity',
                'pre', 'pro', 'con', 'dis', 'un', 're', 'mis', 'over', 'under',
            ])
            if not has_morpheme and common_count < total_bigrams * 0.5:
                score -= 15  # Penalty for long gibberish
        
        # === Bonus for common syllable patterns ===
        common_patterns = ['ing', 'tion', 'ness', 'ment', 'able', 'ible', 'ful', 
                          'less', 'ize', 'ise', 'ous', 'ive', 'ary', 'ery', 'ory']
        for pattern in common_patterns:
            if pattern in word:
                score += 5
        
        return max(0, min(100, score))
    
    def get_spellability_score(self, word: str) -> int:
        """Score how easy the word is to spell from 0-100."""
        score = 100
        word = word.lower()
        
        # Penalize ambiguous sounds
        ambiguous = [
            ('ph', 'f'), ('gh', 'f'), ('ck', 'k'), ('qu', 'kw'),
            ('x', 'ks'), ('c', 'k'), ('c', 's')
        ]
        
        for pair in ambiguous:
            if pair[0] in word:
                score -= 5
        
        # Double letters are okay but slightly harder
        for i in range(len(word) - 1):
            if word[i] == word[i + 1]:
                score -= 3
        
        # Unusual letter combinations
        unusual = ['ei', 'ie', 'ough', 'augh', 'igh']
        for combo in unusual:
            if combo in word:
                score -= 8
        
        return max(0, min(100, score))
