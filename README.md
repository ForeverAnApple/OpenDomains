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
  TLD Multiplier:   1.5x
```

## Word Generators

| Generator | Description | Examples |
|-----------|-------------|----------|
| Dictionary | Filtered English words (4-10 chars) | swift, spark, cloud |
| Phonetic | Brandable made-up words | nexu, kora, zipo |
| Compound | Two-word combinations | quickbase, buildkit, cloudflow |

## Scoring System

Domains are scored on 5 factors (0-100 each):

- **Pronounceability** (30%) - Easy to say out loud
- **Spellability** (25%) - No ambiguous spellings
- **Length** (15%) - Shorter is better (4-6 chars ideal)
- **Memorability** (15%) - Recognizable patterns, real words
- **Brandability** (15%) - Strong sounds, visual appeal

TLD multipliers boost scores: `.com` (1.5x), `.io/.ai` (1.3x), `.co/.app/.dev` (1.2x)

## Configuration

Edit `config/config.yaml` to customize TLDs, scoring weights, and checker settings.
