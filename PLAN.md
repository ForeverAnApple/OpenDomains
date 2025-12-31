# Underrated Available Domains Lookup - Project Plan

## Overview
Build a tool to discover high-quality, available domain names by generating pronounceable, easily spellable words and checking their availability across various TLDs.

## Core Principles for Good Domain Names
1. **Pronounceable** - Easy to say out loud
2. **Easily Spellable** - No ambiguous spellings
3. **Short & Memorable** - Prefer 4-12 characters
4. **Single words preferred** - Two words only if they pair well naturally
5. **Avoid special characters** - No hyphens, underscores (rare exceptions for numbers in exceptional cases)
6. **Meaningful or brandable** - Real words or made-up words that sound good

## Phase 1: Word List Generation

### 1.1 Dictionary-Based Words
- **English dictionary words** (filtered for quality)
  - Common nouns, verbs, adjectives (4-8 letters)
  - Technology-relevant terms
  - Action words (build, grow, ship, etc.)
  - Descriptive words (swift, bright, clear, etc.)
  
- **Filter criteria**:
  - Length: 4-12 characters
  - Pronunciation score (vowel/consonant ratio)
  - Common letter patterns (avoid "xq", "zx", etc.)
  - Exclude vulgar/offensive words

### 1.2 Phonetically Generated Words
- **Syllable-based generation**
  - CV (consonant-vowel) patterns: "ba", "ko", "ri"
  - CVC patterns: "bat", "kit", "run"
  - Combine 2-3 syllables for brandable names
  - Examples: "zipo", "kora", "nexu"

- **Pronunciation rules**:
  - Start with consonant or vowel
  - Alternate consonants and vowels mostly
  - Avoid difficult clusters (scht, pfr)
  - Include double letters sparingly (ll, tt, ss)

### 1.3 Compound Words (Two-Word Combinations)
- **Natural pairs**:
  - Adjective + Noun: "quickbase", "brightspot"
  - Verb + Noun: "buildkit", "shipfast"
  - Noun + Noun: "cloudkit", "devtools"

- **Combination strategies**:
  - Portmanteaus: blend overlapping sounds (smoke + fog = smog)
  - Direct concatenation with natural flow
  - Total length ≤ 15 characters

### 1.4 Pattern-Based Variations
- **Vowel substitutions** (use sparingly):
  - "a" → "o" (track → trock)
  - Only if result is still pronounceable

- **Suffix/Prefix additions**:
  - Common tech suffixes: -ly, -ify, -io, -app, -kit, -hub
  - Prefixes: go-, my-, get-, use-

## Phase 2: Domain Availability Checking

### 2.1 TLD Priority List
Organize by popularity and purpose:

**Tier 1 - Most Valuable**:
- .com (primary)
- .io (tech/startups)
- .ai (AI/tech)
- .co (business)

**Tier 2 - Strong Alternatives**:
- .app
- .dev
- .tech
- .net
- .org

**Tier 3 - Niche/Newer**:
- .xyz
- .sh
- .gg
- .so
- .to

### 2.2 Availability Check Methods
1. **WHOIS Lookup**
   - Use WHOIS protocol for bulk checks
   - Rate limiting: respect registrar limits
   - Parse responses for availability status

2. **DNS Lookup**
   - Quick pre-filter (no DNS = likely available)
   - Faster than WHOIS for initial screening

3. **API Integration Options**:
   - Namecheap API
   - GoDaddy API
   - Cloudflare Registrar API
   - Consider costs vs. DIY WHOIS

### 2.3 Checking Strategy
1. First: DNS batch check (fast filter)
2. Second: WHOIS verification for DNS-available domains
3. Third: Manual spot-check on promising domains
4. Caching: Store results to avoid re-checking

## Phase 3: Scoring & Ranking System

### 3.1 Quality Score Factors
```
Total Score = (Pronounceability × 0.3) + 
              (Spellability × 0.25) + 
              (Length × 0.15) + 
              (Memorability × 0.15) +
              (Brandability × 0.15)
```

**Pronounceability (0-100)**:
- Vowel/consonant balance
- No difficult clusters
- Syllable clarity

**Spellability (0-100)**:
- Common letter combinations
- No ambiguous sounds (f/ph, k/c)
- Dictionary word bonus

**Length (0-100)**:
- 4-6 chars: 100
- 7-8 chars: 85
- 9-10 chars: 70
- 11-12 chars: 50
- 13+ chars: 30

**Memorability (0-100)**:
- Real word: +30
- Unique pattern: +20
- Easy rhythm: +25
- Common syllables: +25

**Brandability (0-100)**:
- Visual appeal
- Category fit (tech, business, etc.)
- Uniqueness in search

### 3.2 TLD Score Multiplier
- .com: 1.5x
- .io, .ai: 1.3x
- .co, .app, .dev: 1.2x
- Others: 1.0x

## Phase 4: Output & Presentation

### 4.1 Output Format
```json
{
  "domain": "example.com",
  "available": true,
  "score": 87,
  "breakdown": {
    "pronounceability": 92,
    "spellability": 88,
    "length": 85,
    "memorability": 80,
    "brandability": 90
  },
  "word_type": "dictionary|generated|compound",
  "pronunciation": "ex-am-pull",
  "checked_at": "2025-12-24T..."
}
```

### 4.2 Filtering & Export Options
- Filter by minimum score
- Filter by TLD
- Filter by word type
- Export: JSON, CSV, Markdown table
- Highlight "gems" (score > 85 + .com available)

## Phase 5: Implementation Architecture

### 5.1 Tech Stack Options
**Language**: Python or Node.js
- Python: Better libraries for NLP, word processing
- Node.js: Good async for parallel checks

**Libraries**:
- `nltk` or `wordlist` for dictionary
- `pronouncing` for syllables/phonetics
- `python-whois` or `whois` module
- `dnspython` for DNS checks

### 5.2 Project Structure
```
/src
  /generators
    - dictionary_generator.py
    - phonetic_generator.py
    - compound_generator.py
  /checkers
    - dns_checker.py
    - whois_checker.py
    - availability_service.py
  /scoring
    - scorer.py
    - filters.py
  /utils
    - word_validator.py
    - cache.py
/data
  /wordlists
    - english_words.txt
    - tech_terms.txt
    - syllables.json
  /results
    - available_domains.json
    - checked_cache.json
/config
  - config.yaml (TLDs, scoring weights, API keys)
/tests
  - test_generators.py
  - test_checkers.py
  - test_scoring.py
```

### 5.3 Workflow Pipeline
```
1. Generate wordlist → 2. Filter/validate → 3. DNS pre-check → 
4. WHOIS verify → 5. Score domains → 6. Rank & output
```

## Phase 6: Optimization & Features

### 6.1 Performance
- Parallel domain checking (batch processing)
- Rate limiting with exponential backoff
- Caching layer for checked domains
- Progress indicators for long runs

### 6.2 Advanced Features (Future)
- Category-specific generation (tech, food, travel, etc.)
- Similar domain finder (typos, variations)
- Historical price data integration
- Trademark checking
- Social media handle availability
- SEO difficulty estimation

### 6.3 CLI Interface
```bash
# Basic usage
python domain_finder.py --generate 1000 --check --output results.json

# With filters
python domain_finder.py --min-score 80 --tlds com,io --length 4-8

# Category specific
python domain_finder.py --category tech --compound-words

# Check specific list
python domain_finder.py --wordlist my_words.txt --check-all-tlds
```

## Success Metrics
- Generate 10,000+ quality word candidates
- Check availability across 5+ TLDs
- Find 100+ available domains with score > 75
- Find 10+ "gem" domains (score > 85, .com available)
- Execution time: < 5 minutes for 1000 domains

## Next Steps
1. Set up project structure
2. Implement dictionary-based generator (simplest start)
3. Implement DNS checker (fast validation)
4. Build basic scoring system
5. Create simple CLI
6. Iterate and add more sophisticated features
