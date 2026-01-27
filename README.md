# OpenDomains

A CLI tool to discover high-quality, available domain names. Generates pronounceable, easily spellable words and checks their availability across multiple TLDs.

## Installation

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Hunt for Domains (Full Pipeline)

Generate words, check availability, and find gems in one command:

```bash
python main.py hunt --tlds com,io,ai --count 200 --min-score 70
```

### Generate Word Candidates

```bash
# Generate from all sources
python main.py generate --count 100 --output data/wordlists/words.json

# Control which generators to use
python main.py generate --no-dictionary --phonetic --compound
```

### Check Specific Words

```bash
# Check words across TLDs
python main.py check swift bolt nexu --tlds com,io,ai

# Check from a wordlist file
python main.py check --wordlist data/wordlists/words.json --tlds com,io

# Skip WHOIS verification (faster but less accurate)
python main.py check myword --no-verify
```

### Score a Domain

```bash
python main.py score swift.com
```

Output:
```
Domain: swift.com
Total Score: 137.6

Breakdown:
  Pronounceability: 80/100
  Spellability:     100/100
  Length:           100/100
  Memorability:     90/100
  Brandability:     95/100
  Euphony:          85/100
  Dictionary:       100/100
  TLD Multiplier:   1.5x
```

## Word Generators

| Generator | Description | Examples |
|-----------|-------------|----------|
| Dictionary | Filtered English words (4-10 chars) | swift, spark, cloud |
| Phonetic | Brandable made-up words | nexu, kora, zipo |
| Compound | Two-word combinations | quickbase, buildkit, cloudflow |

## Scoring System

Domains are scored on 7 factors (0-100 each):

- **Dictionary** (30%) - Real English words or meaningful compounds
- **Euphony** (20%) - Pleasant sound and sophisticated morpheme quality
- **Brandability** (20%) - Strong sounds, tech associations, and visual appeal
- **Memorability** (15%) - Recognizable patterns and mental imagery
- **Length** (5%) - Shorter is better (4-7 chars ideal)
- **Pronounceability** (5%) - Easy to say out loud
- **Spellability** (5%) - No ambiguous spellings

TLD multipliers boost scores: `.com` (1.5x), `.io/.ai` (1.3x), `.co/.app/.dev` (1.2x)

## Utilities

Beyond the main CLI, several utility scripts are available for specialized tasks:

- **`analyze_auctions.py`**: Analyzes domain auction exports (Namecheap/GoDaddy CSVs) to find undervalued gems. Supports "vibe" filtering (elegant, brandable, tech, neutral) and valuation-to-price ratios.
- **`rescore_domains.py`**: Re-scores all domains in the local database using the latest scoring algorithm.

> **Note**: Many previous one-off scripts have been consolidated into the main `main.py` CLI for a more consistent experience.

## Configuration

Edit `config/config.yaml` to customize TLDs, scoring weights, and checker settings.
