"""Tests for domain generators."""

import pytest


@pytest.mark.unit
class TestCompoundGenerator:
    """Test CompoundGenerator functionality."""

    def test_compound_generator_initialization(self, compound_generator):
        """Test that CompoundGenerator initializes correctly."""
        assert compound_generator is not None
        assert compound_generator.max_length == 15
        assert compound_generator.validator is not None

    def test_generate_adj_noun(self, compound_generator):
        """Test adjective + noun combinations."""
        results = compound_generator.generate_adj_noun()

        assert isinstance(results, list)
        assert len(results) > 0
        assert all(compound_generator.validator.is_valid(w) for w in results)

        # Check for expected combinations
        assert 'swiftapp' in results or any('swift' in w for w in results)

    def test_generate_verb_noun(self, compound_generator):
        """Test verb + noun combinations."""
        results = compound_generator.generate_verb_noun()

        assert isinstance(results, list)
        assert len(results) > 0
        assert all(compound_generator.validator.is_valid(w) for w in results)

    def test_generate_noun_noun(self, compound_generator):
        """Test noun + noun combinations."""
        results = compound_generator.generate_noun_noun()

        assert isinstance(results, list)
        assert len(results) > 0
        assert all(compound_generator.validator.is_valid(w) for w in results)

    def test_generate_with_suffix(self, compound_generator):
        """Test word + suffix combinations."""
        results = compound_generator.generate_with_suffix()

        assert isinstance(results, list)
        assert len(results) > 0
        assert all(compound_generator.validator.is_valid(w) for w in results)

        # Check that suffixes are present
        assert any(w.endswith('ly') for w in results)
        assert any(w.endswith('io') for w in results)

    def test_generate_portmanteau(self, compound_generator):
        """Test portmanteau generation."""
        results = compound_generator.generate_portmanteau('cloud', 'app')

        assert isinstance(results, list)
        assert all(compound_generator.validator.is_valid(w) for w in results)

    def test_generate_all(self, compound_generator):
        """Test generating all compound types."""
        results = compound_generator.generate_all()

        assert isinstance(results, list)
        assert len(results) > 0
        assert all(compound_generator.validator.is_valid(w) for w in results)

        # Should include various types
        assert len(set(results)) == len(results)  # No duplicates

    def test_generate_custom(self, compound_generator):
        """Test generating compounds from custom word lists."""
        first_words = ['test', 'demo']
        second_words = ['app', 'lab', 'hub']

        results = compound_generator.generate_custom(first_words, second_words)

        assert isinstance(results, list)
        assert all(w.startswith(tuple(first_words)) for w in results)

    def test_flows_well_length_check(self, compound_generator):
        """Test _flows_well length check."""
        assert not compound_generator._flows_well('verylongword', 'test')

    def test_flows_well_bad_junction(self, compound_generator):
        """Test _flows_well rejects bad junctions."""
        assert not compound_generator._flows_well('testaa', 'test')

    def test_flows_well_good_junction(self, compound_generator):
        """Test _flows_well accepts good junctions."""
        assert compound_generator._flows_well('test', 'app')


@pytest.mark.unit
class TestDictionaryGenerator:
    """Test DictionaryGenerator functionality."""

    def test_dictionary_generator_initialization(self, dictionary_generator):
        """Test that DictionaryGenerator initializes correctly."""
        assert dictionary_generator is not None
        assert dictionary_generator.min_length == 4
        assert dictionary_generator.max_length == 10

    def test_load_words(self, dictionary_generator):
        """Test loading words from file."""
        count = dictionary_generator.load_words()

        assert count > 0
        assert len(dictionary_generator._words) > 0

    def test_generate(self, dictionary_generator):
        """Test generating words from dictionary."""
        results = dictionary_generator.generate()

        assert isinstance(results, list)
        assert len(results) > 0
        assert all(dictionary_generator.validator.is_valid(w) for w in results)

        # Should be sorted by length then alphabetically
        assert all(len(results[i]) <= len(results[i+1]) or
                  (len(results[i]) == len(results[i+1]) and results[i] <= results[i+1])
                  for i in range(len(results)-1))

    def test_generate_with_limit(self, dictionary_generator):
        """Test generating words with limit."""
        results = dictionary_generator.generate(limit=5)

        assert isinstance(results, list)
        assert len(results) <= 5

    def test_generate_curated(self, dictionary_generator):
        """Test generating from curated word lists."""
        results = dictionary_generator.generate_curated()

        assert isinstance(results, list)
        assert len(results) > 0
        assert all(dictionary_generator.validator.is_valid(w) for w in results)

        # Should contain words from GOOD_CATEGORIES
        assert any(w in ['build', 'ship', 'grow', 'flow', 'sync'] for w in results)

    def test_generate_with_affixes(self, dictionary_generator):
        """Test generating words with prefixes and suffixes."""
        results = dictionary_generator.generate_with_affixes()

        assert isinstance(results, list)
        assert len(results) > 0
        assert all(dictionary_generator.validator.is_valid(w) for w in results)

        # Should have words with prefixes
        assert any(w.startswith('go') or w.startswith('my') for w in results)

        # Should have words with suffixes
        assert any(w.endswith('ly') or w.endswith('io') for w in results)


@pytest.mark.unit
class TestPhoneticGenerator:
    """Test PhoneticGenerator functionality."""

    def test_phonetic_generator_initialization(self, phonetic_generator):
        """Test that PhoneticGenerator initializes correctly."""
        assert phonetic_generator is not None
        assert phonetic_generator.min_length == 4
        assert phonetic_generator.max_length == 10

    def test_generate_syllable(self, phonetic_generator):
        """Test single syllable generation."""
        syllable = phonetic_generator._generate_syllable()

        assert isinstance(syllable, str)
        assert 1 <= len(syllable) <= 10  # Reasonable length

    def test_generate_brandable(self, phonetic_generator):
        """Test brandable word generation."""
        word = phonetic_generator._generate_brandable()

        assert isinstance(word, str)
        assert len(word) <= phonetic_generator.max_length

    def test_generate_cv_pattern(self, phonetic_generator):
        """Test CV pattern generation."""
        word = phonetic_generator._generate_cv_pattern()

        assert isinstance(word, str)
        assert len(word) >= phonetic_generator.min_length

    def test_generate_method_syllable(self, phonetic_generator):
        """Test generate with syllable method."""
        results = phonetic_generator.generate(count=10, method='syllable')

        assert isinstance(results, list)
        assert len(results) <= 10
        assert all(phonetic_generator.validator.is_valid(w) for w in results)

    def test_generate_method_cv(self, phonetic_generator):
        """Test generate with CV method."""
        results = phonetic_generator.generate(count=10, method='cv')

        assert isinstance(results, list)
        assert len(results) <= 10
        assert all(phonetic_generator.validator.is_valid(w) for w in results)

    def test_generate_method_mixed(self, phonetic_generator):
        """Test generate with mixed method."""
        results = phonetic_generator.generate(count=20, method='mixed')

        assert isinstance(results, list)
        assert len(results) <= 20
        assert all(phonetic_generator.validator.is_valid(w) for w in results)

    def test_generate_with_prefix(self, phonetic_generator):
        """Test generating words with prefix."""
        results = phonetic_generator.generate_with_prefix(prefix='tech', count=5)

        assert isinstance(results, list)
        assert len(results) <= 5
        assert all(w.startswith('tech') for w in results)

    def test_generate_with_suffix(self, phonetic_generator):
        """Test generating words with suffix."""
        results = phonetic_generator.generate_with_suffix(suffix='io', count=5)

        assert isinstance(results, list)
        assert len(results) <= 5
        assert all(w.endswith('io') for w in results)

    def test_generate_reproducibility(self, phonetic_generator):
        """Test that generator produces same results with same seed."""
        gen1 = type(phonetic_generator)(seed=42)
        gen2 = type(phonetic_generator)(seed=42)

        results1 = gen1.generate(count=10, method='syllable')
        results2 = gen2.generate(count=10, method='syllable')

        assert results1 == results2

    def test_generate_unique(self, phonetic_generator):
        """Test that generator produces unique words."""
        results = phonetic_generator.generate(count=50, method='mixed')

        assert len(results) == len(set(results))  # No duplicates


@pytest.mark.integration
class TestGeneratorIntegration:
    """Integration tests for generators."""

    def test_compound_with_scorer(self, compound_generator, scorer):
        """Test that compound words can be scored."""
        compounds = compound_generator.generate_all()[:10]

        for compound in compounds:
            score = scorer.score(compound + '.com')
            assert score.total_score > 0
            assert score.dictionary_score > 0

    def test_dictionary_with_scorer(self, dictionary_generator, scorer):
        """Test that dictionary words can be scored."""
        words = dictionary_generator.generate_curated()[:10]

        for word in words:
            score = scorer.score(word + '.com')
            assert score.total_score > 0
            assert score.dictionary_score > 0

    def test_phonetic_with_scorer(self, phonetic_generator, scorer):
        """Test that phonetic words can be scored."""
        words = phonetic_generator.generate(count=10, method='mixed')

        for word in words:
            score = scorer.score(word + '.io')
            assert score.total_score > 0

    def test_all_generators_with_results_store(self, compound_generator,
                                                  dictionary_generator,
                                                  phonetic_generator,
                                                  temp_db):
        """Test that all generators can store results."""
        # Generate from all generators
        compounds = compound_generator.generate_all()[:5]
        dict_words = dictionary_generator.generate_curated()[:5]
        phonetic_words = phonetic_generator.generate(count=5, method='mixed')

        all_words = compounds + dict_words + phonetic_words

        # Add to results store
        for word in all_words:
            temp_db.add(
                domain=word + '.com',
                available=True,
                method='generator',
                error=None
            )

        # Verify all were stored
        for word in all_words:
            result = temp_db.get(word + '.com')
            assert result is not None
            assert result['available'] == 1


@pytest.mark.unit
class TestGeneratorEdgeCases:
    """Test edge cases for generators."""

    def test_compound_empty_lists(self, compound_generator):
        """Test compound generator with empty lists."""
        results = compound_generator.generate_custom([], ['test'])
        assert results == []

        results = compound_generator.generate_custom(['test'], [])
        assert results == []

    def test_compound_max_length_filter(self, compound_generator):
        """Test that compound generator respects max length."""
        compound_generator.max_length = 8
        results = compound_generator.generate_adj_noun()

        assert all(len(w) <= 8 for w in results)

    def test_phonetic_short_max_length(self, phonetic_generator):
        """Test phonetic generator with very short max length."""
        gen = type(phonetic_generator)(max_length=4, seed=42)
        results = gen.generate(count=10, method='syllable')

        assert all(len(w) <= 4 for w in results)

    def test_phonetic_long_max_length(self, phonetic_generator):
        """Test phonetic generator with long max length."""
        gen = type(phonetic_generator)(max_length=15, seed=42)
        results = gen.generate(count=10, method='syllable')

        assert all(len(w) <= 15 for w in results)

    def test_dictionary_no_file(self, tmp_path):
        """Test dictionary generator with missing file."""
        from generators.dictionary_generator import DictionaryGenerator

        # Point to non-existent file
        gen = DictionaryGenerator(wordlist_path=str(tmp_path / 'nonexistent.txt'),
                                  download_if_missing=False)

        count = gen.load_words(download_if_missing=False)
        assert count == 0

    def test_generator_output_types(self, compound_generator,
                                    dictionary_generator,
                                    phonetic_generator):
        """Test that generators return correct types."""
        compounds = compound_generator.generate_adj_noun()
        dict_words = dictionary_generator.generate()
        phonetic_words = phonetic_generator.generate(count=5)

        assert all(isinstance(w, str) for w in compounds)
        assert all(isinstance(w, str) for w in dict_words)
        assert all(isinstance(w, str) for w in phonetic_words)

    def test_generator_lowercase(self, compound_generator):
        """Test that generators produce lowercase output."""
        compounds = compound_generator.generate_all()

        assert all(w == w.lower() for w in compounds)


@pytest.mark.unit
class TestWordValidationInGenerators:
    """Test that generators properly validate words."""

    def test_compound_validation(self, compound_generator):
        """Test that compound generator filters invalid words."""
        results = compound_generator.generate_all()

        # All should pass validation
        assert all(compound_generator.validator.is_valid(w) for w in results)

    def test_dictionary_validation(self, dictionary_generator):
        """Test that dictionary generator filters invalid words."""
        results = dictionary_generator.generate()

        # All should pass validation
        assert all(dictionary_generator.validator.is_valid(w) for w in results)

    def test_phonetic_validation(self, phonetic_generator):
        """Test that phonetic generator filters invalid words."""
        results = phonetic_generator.generate(count=50, method='mixed')

        # All should pass validation
        assert all(phonetic_generator.validator.is_valid(w) for w in results)

    def test_compound_no_offensive_words(self, compound_generator):
        """Test that compound generator doesn't produce offensive words."""
        results = compound_generator.generate_all()

        from utils.word_validator import OFFENSIVE_PATTERNS

        for word in results:
            for pattern in OFFENSIVE_PATTERNS:
                assert pattern not in word.lower()


@pytest.mark.slow
class TestGeneratorPerformance:
    """Performance tests for generators (marked as slow)."""

    def test_compound_bulk_generation(self, compound_generator):
        """Test generating large number of compounds."""
        import time

        start = time.time()
        results = compound_generator.generate_all()
        elapsed = time.time() - start

        # Should complete in reasonable time
        assert elapsed < 1.0
        assert len(results) > 0

    def test_phonetic_bulk_generation(self, phonetic_generator):
        """Test generating large number of phonetic words."""
        import time

        start = time.time()
        results = phonetic_generator.generate(count=1000, method='mixed')
        elapsed = time.time() - start

        # Should complete in reasonable time
        assert elapsed < 5.0
        assert len(results) <= 1000
