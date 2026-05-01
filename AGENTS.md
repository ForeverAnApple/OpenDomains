# AGENTS.md

## Project Overview

OpenDomains is a Python CLI for generating domain-name candidates, checking availability, scoring domain quality, and analyzing saved domain results or auction CSV exports.

The main flow is:

1. Candidate words are produced by generators in `src/generators/`.
2. `src.utils.word_validator.WordValidator` filters candidate words for length, characters, offensive substrings, awkward clusters, and pronounceability.
3. Availability checks run through `src.checkers.availability_service.AvailabilityService`:
   - cache lookup first via `src.utils.cache.ResultCache`
   - availability check via `src.checkers.tldx_checker.TldxChecker`, which shells out to the external `tldx` binary (https://github.com/brandonyoungdev/tldx) and parses its JSON-stream output
4. Scores are computed by `src.scoring.scorer.DomainScorer`.
5. CLI commands persist all check results and scores to SQLite through `src.utils.results_store.ResultsStore`.

`main.py` is only the entry point and delegates to `src.cli.main()`.

## Environment and Commands

### Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

A Nix dev shell is also defined:

```bash
nix develop
pip install -r requirements.txt
```

The Nix shell creates and activates `.venv` if missing, but it does not install Python requirements automatically.

### Main CLI

```bash
python main.py generate --count 100 --output data/wordlists/words.json
python main.py check swift bolt nexu --tlds com,io,ai
python main.py check --wordlist data/wordlists/words.json --tlds com,io
python main.py hunt --tlds com,io,ai --count 200 --min-score 70
python main.py score swift.com
python main.py results --min-score 70 --limit 50
python main.py results --all --export data/results/domains.csv
```

Availability checking requires the `tldx` binary on PATH (`brew install tldx` or see https://github.com/brandonyoungdev/tldx).

### Utility Scripts

```bash
python analyze_auctions.py --csv data/auctions/gd_auctions_export.csv --min-score 60 --max-price 500
python analyze_auctions.py --vibe elegant --top 50 --details
python analyze_auctions.py --real-words --max-length 7 --tld com
python rescore_domains.py
```

`analyze_auctions.py` supports Namecheap and GoDaddy CSV formats and defaults to `data/auctions/namecheap_market_sales_2026_01_01.csv` if `--csv` is not supplied.

### Tests

```bash
python -m pytest
python -m pytest tests/test_generators.py
python -m pytest tests/test_scorer.py
python -m pytest -m unit
python -m pytest -m integration
```

`pytest.ini` configures verbose output, strict markers, short tracebacks, and `asyncio_mode = auto`.

At the time this file was written, running `python -m pytest` with the system Python failed because `pytest` was not installed. Install `requirements.txt` in the active environment first.

No lint, formatting, packaging, or CI configuration was found.

## Code Organization

- `main.py`: script entry point.
- `src/cli.py`: Click command definitions and top-level orchestration for generation, checking, scoring, results display, JSON output, and SQLite persistence.
- `src/generators/`:
  - `dictionary_generator.py`: dictionary-backed and curated word generation; downloads `data/wordlists/english_words.txt` from the hard-coded `WORDS_URL` if missing and `download_if_missing=True`.
  - `phonetic_generator.py`: pseudo-word generation using syllables, CV patterns, optional deterministic seed.
  - `compound_generator.py`: adjective+noun, verb+noun, noun+noun, suffix, portmanteau, and custom compound generation.
- `src/checkers/`:
  - `tldx_checker.py`: subprocess wrapper around the `tldx` CLI; groups domains by TLD, batches keywords per invocation, parses `--format json-stream` output line by line.
  - `availability_service.py`: cache + tldx composition with intermediate result snapshots.
- `src/scoring/scorer.py`: scoring model and `DomainScore` dataclass.
- `src/utils/`:
  - `word_validator.py`: central candidate validation and pronounceability/spellability scoring.
  - `cache.py`: JSON availability cache with 24-hour TTL by default.
  - `results_store.py`: SQLite persistence and CSV export.
- `tests/`: pytest tests for generators and scoring with shared fixtures in `tests/conftest.py`.
- `config/config.yaml`: TLD tiers and checker/scoring settings, but current CLI/service/scorer constructors mostly rely on in-code defaults rather than loading this config.

## Data and Persistence

Generated/runtime data lives under `data/`, which is gitignored.

Observed paths used by code:

- `data/wordlists/english_words.txt`: dictionary wordlist used by `DictionaryGenerator` and `DomainScorer`.
- `data/results/checked_cache.json`: default availability cache.
- `data/results/.intermediate_results.json`: crash-recovery snapshot written by `AvailabilityService` during batch checks.
- `data/results/domains.db`: default SQLite results database.
- `data/results/available_domains.json`: default `hunt` output.
- `data/auctions/...`: expected location for auction CSVs.

`ResultsStore` creates or migrates the `domains` table automatically and adds `euphony INTEGER NOT NULL DEFAULT 0` for older DBs.

## Important Gotchas

- Import style is inconsistent between runtime code and some tests. Runtime code uses package imports from `src.*` or relative imports inside `src`; several fixtures/tests import from top-level `scoring`, `generators`, or `utils` after `tests/conftest.py` puts the project root on `sys.path`. Check imports carefully when moving files.
- `tests/test_scorer.py` contains expectations for `score.word` and `score.tld` in the subdomain test, but the observed `DomainScore` dataclass does not define those fields.
- `tests/test_generators.py::test_dictionary_no_file` instantiates `DictionaryGenerator(..., download_if_missing=False)`, but the observed constructor does not accept `download_if_missing`.
- `tests/conftest.py` has some imports like `from utils.results_store import ResultsStore`; those packages are under `src/` in the repository layout.
- `AvailabilityService.check_batch()` records `available=None` for any domain tldx returns no answer for (e.g. tldx timeout, malformed output) and persists nothing for those into the cache.
- `AvailabilityService.check_batch()` always writes `.intermediate_results.json` at the end and does not call `clear_intermediate()`.
- `TldxChecker` requires the `tldx` binary on PATH; the constructor raises `RuntimeError` if not found.
- `TldxChecker` shells out per TLD (groups keywords by TLD, then chunks of `batch_size`). Large keyword-set × TLD-set runs are still bounded by tldx's own RDAP/WHOIS speed.
- `ResultCache.set()` saves the full JSON file on every result; large uncached batches may do frequent disk writes.
- `DomainScorer._get_word_and_tld()` scores only the first label and last label of a domain. For `sub.example.com`, it scores `sub` with TLD `com`.
- `dictionary_score` is the persisted field name for meaning score; comments indicate this is kept for database compatibility.
- `config/config.yaml` has scoring weights that do not match `DomainScorer.DEFAULT_WEIGHTS`, and `load_config()` in `src/cli.py` is defined but not used by the CLI commands observed. Do not assume config edits affect scoring/checking unless you wire them in.
- `analyze_namecheap_data.py` uses hard-coded absolute paths under `/Users/daaaa/Projects/Code/OpenDomains/...`, not the current repository path.
- `requirements.txt` does not include `pandas`, `numpy`, `matplotlib`, or `seaborn`, even though `analyze_namecheap_data.py` imports them.

## Scoring Model Notes

`DomainScorer.DEFAULT_WEIGHTS` currently prioritizes:

- meaning: `0.30`
- euphony: `0.20`
- brandability: `0.20`
- memorability: `0.15`
- length: `0.05`
- pronounceability: `0.05`
- spellability: `0.05`

TLD multipliers are applied after the weighted raw score: `.com` `1.5`, `.io`/`.ai` `1.3`, `.co`/`.app`/`.dev` `1.2`, `.tech` `1.1`, `.net`/`.org` `1.0`, unknown TLDs `1.0`.

The meaning score intentionally uses the persisted name `dictionary_score`. It gives high scores for exact dictionary/common words, strict two-part compounds, word+suffix/prefix forms, substrings, or morpheme-only words, and penalizes random syllables.

If changing score fields, update all of these together:

- `DomainScore` dataclass and `to_dict()` in `src/scoring/scorer.py`
- CLI score serialization in `src/cli.py`
- SQLite schema and insert/update code in `src/utils/results_store.py`
- `rescore_domains.py`
- tests in `tests/test_scorer.py`

## Testing Patterns

Tests are marked with `@pytest.mark.unit`, `@pytest.mark.integration`, and `@pytest.mark.slow`.

Representative patterns:

- Generator tests assert returned types, uniqueness, validation via `WordValidator`, and deterministic phonetic generation when seeded.
- Scorer tests validate individual private scoring helpers as well as total scoring and ranking.
- Fixtures in `tests/conftest.py` create temp wordlists, temp SQLite DBs, seeded generators, and a mock `TldxChecker`.

When modifying network-facing checkers, prefer tests with a mocked `TldxChecker` (or monkeypatched `subprocess.run`) rather than real network access. Slow/external behavior should be marked `slow` if added.

## Style and Conventions

- Python modules use simple classes and dataclasses rather than a framework.
- Public CLI is Click-based; terminal output uses Rich tables/progress/status.
- Most source files use short module docstrings and type hints on public methods.
- Runtime-generated file paths are mostly relative to the repository root; run commands from the repo root unless you pass explicit paths.
- Validation/scoring constants are large in-module sets/lists; existing code keeps these close to the scoring or validation logic rather than externalizing them.
- The project has no observed formatter configuration. Preserve existing local style when editing.
