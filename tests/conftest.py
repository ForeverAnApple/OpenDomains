"""Pytest configuration and shared fixtures for OpenDomains test suite."""

import json
import sqlite3
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, MagicMock
import pytest
import tempfile
import shutil
import sys
import os

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set PYTHONPATH for subprocess imports
os.environ['PYTHONPATH'] = str(project_root)


# ==============================================================================
# Pytest Configuration
# ==============================================================================

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests (module interactions)")
    config.addinivalue_line("markers", "slow: Slow tests (external APIs, should be skipped by default)")


# ==============================================================================
# Mock tldx Fixtures
# ==============================================================================

@pytest.fixture
def mock_tldx_checker():
    """Mock TldxChecker with predefined responses."""
    from src.checkers.tldx_checker import TldxChecker

    checker = Mock(spec=TldxChecker)
    available_domains = {'test1.com', 'test2.io', 'test3.ai'}

    checker.check_single.side_effect = lambda d: d in available_domains
    checker.check_batch.side_effect = lambda domains, progress_callback=None: {
        d: d in available_domains for d in domains
    }
    return checker


# ==============================================================================
# Database Fixtures
# ==============================================================================

@pytest.fixture
def temp_db(tmp_path):
    """Create temporary database for testing."""
    db_path = tmp_path / "test_domains.db"

    from utils.results_store import ResultsStore

    # Create ResultsStore with temp DB
    store = ResultsStore(str(db_path))

    yield store

    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def sample_domains_db(tmp_path):
    """Create temporary database with sample domain data."""
    db_path = tmp_path / "sample_domains.db"

    from utils.results_store import ResultsStore
    from datetime import datetime

    store = ResultsStore(str(db_path))

    # Add sample data
    now = datetime.now().isoformat()
    sample_data = [
        {
            'domain': 'test1.com',
            'word': 'test1',
            'tld': 'com',
            'available': True,
            'method': 'dns',
            'score': {
                'total_score': 85.5,
                'pronounceability': 90,
                'spellability': 85,
                'length_score': 100,
                'memorability': 80,
                'brandability': 85,
                'euphony': 82,
                'dictionary_score': 75,
                'tld_multiplier': 1.5
            }
        },
        {
            'domain': 'tech2.io',
            'word': 'tech2',
            'tld': 'io',
            'available': True,
            'method': 'dns',
            'score': {
                'total_score': 78.2,
                'pronounceability': 85,
                'spellability': 80,
                'length_score': 90,
                'memorability': 75,
                'brandability': 80,
                'euphony': 78,
                'dictionary_score': 70,
                'tld_multiplier': 1.3
            }
        },
        {
            'domain': 'taken3.ai',
            'word': 'taken3',
            'tld': 'ai',
            'available': False,
            'method': 'dns',
            'score': {
                'total_score': 92.0,
                'pronounceability': 95,
                'spellability': 90,
                'length_score': 100,
                'memorability': 90,
                'brandability': 92,
                'euphony': 88,
                'dictionary_score': 85,
                'tld_multiplier': 1.3
            }
        }
    ]

    for data in sample_data:
        store.add(
            domain=data['domain'],
            available=data['available'],
            method=data['method'],
            score=data.get('score')
        )

    yield store

    # Cleanup
    if db_path.exists():
        db_path.unlink()


# ==============================================================================
# Sample Data Fixtures
# ==============================================================================

@pytest.fixture
def sample_domains():
    """List of test domains with expected properties."""
    return [
        {'domain': 'test.com', 'available': True, 'expected_score_range': (70, 95)},
        {'domain': 'example.io', 'available': False, 'expected_score_range': (65, 90)},
        {'domain': 'brandable.ai', 'available': True, 'expected_score_range': (80, 100)},
        {'domain': 'quick.tech', 'available': True, 'expected_score_range': (75, 95)},
        {'domain': 'gibberishxq.io', 'available': True, 'expected_score_range': (0, 50)},
    ]


@pytest.fixture
def sample_words():
    """List of test words for scoring and generation."""
    return [
        {'word': 'swift', 'type': 'real', 'expected_meaning_score': 100},
        {'word': 'cloudapp', 'type': 'compound', 'expected_meaning_score': 85},
        {'word': 'brandable', 'type': 'real', 'expected_meaning_score': 100},
        {'word': 'testingly', 'type': 'suffix', 'expected_meaning_score': 70},
        {'word': 'xqkzmvb', 'type': 'gibberish', 'expected_meaning_score': 0},
        {'word': 'untest', 'type': 'prefix', 'expected_meaning_score': 70},
        {'word': 'tes', 'type': 'too_short', 'expected_meaning_score': 100},
    ]


@pytest.fixture
def sample_scores():
    """List of expected score calculations."""
    return [
        {
            'domain': 'test.com',
            'word': 'test',
            'tld': 'com',
            'expected_scores': {
                'pronounceability': (80, 100),
                'spellability': (80, 100),
                'length_score': 100,
                'memorability': (60, 80),
                'brandability': (60, 80),
                'euphony': (60, 80),
                'dictionary_score': 100,
            },
            'expected_total_range': (100, 150)  # With 1.5x TLD multiplier
        },
        {
            'domain': 'gibberish.io',
            'word': 'gibberish',
            'tld': 'io',
            'expected_scores': {
                'pronounceability': (40, 70),
                'spellability': (50, 80),
                'length_score': 80,
                'memorability': (30, 60),
                'brandability': (20, 50),
                'euphony': (20, 50),
                'dictionary_score': 100,
            },
            'expected_total_range': (60, 120)  # With 1.3x TLD multiplier
        }
    ]


# ==============================================================================
# Cache Fixtures
# ==============================================================================

@pytest.fixture
def temp_cache(tmp_path):
    """Create temporary cache file for testing."""
    cache_path = tmp_path / "test_cache.json"

    from utils.cache import ResultCache

    cache = ResultCache(str(cache_path), ttl_hours=24)

    # Add some cached data
    cache.set('test1.com', True, 'dns')
    cache.set('test2.io', False, 'dns')
    cache.set('test3.ai', True, 'whois')

    yield cache

    # Cleanup
    if cache_path.exists():
        cache_path.unlink()


# ==============================================================================
# Generator Fixtures
# ==============================================================================

@pytest.fixture
def mock_dictionary_words(tmp_path):
    """Create temporary wordlist file for testing."""
    wordlist_path = tmp_path / "test_words.txt"

    test_words = [
        'test', 'word', 'list', 'sample', 'data',
        'tech', 'code', 'sync', 'link', 'node',
        'build', 'ship', 'grow', 'flow', 'run',
        'sun', 'moon', 'star', 'sky', 'cloud',
    ]

    with open(wordlist_path, 'w') as f:
        for word in test_words:
            f.write(f"{word}\n")

    return wordlist_path


# ==============================================================================
# Real Instance Fixtures (for unit tests)
# ==============================================================================

@pytest.fixture
def scorer():
    """DomainScorer instance for testing."""
    from scoring.scorer import DomainScorer
    return DomainScorer()


@pytest.fixture
def compound_generator():
    """CompoundGenerator instance for testing."""
    from generators.compound_generator import CompoundGenerator
    return CompoundGenerator(max_length=15)


@pytest.fixture
def dictionary_generator(mock_dictionary_words):
    """DictionaryGenerator instance for testing."""
    from generators.dictionary_generator import DictionaryGenerator
    return DictionaryGenerator(wordlist_path=str(mock_dictionary_words))


@pytest.fixture
def phonetic_generator():
    """PhoneticGenerator instance for testing."""
    from generators.phonetic_generator import PhoneticGenerator
    return PhoneticGenerator(seed=42)  # Fixed seed for reproducibility


@pytest.fixture
def word_validator():
    """WordValidator instance for testing."""
    from utils.word_validator import WordValidator
    return WordValidator(min_length=4, max_length=12)


# ==============================================================================
# Async Test Support
# ==============================================================================

@pytest.fixture
def event_loop_policy():
    """Event loop policy for async tests."""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()
