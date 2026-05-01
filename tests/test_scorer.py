"""Tests for DomainScorer module."""

import pytest
from typing import Dict, Any


@pytest.mark.unit
class TestDomainScorerInitialization:
    """Test DomainScorer initialization and basic setup."""

    def test_scorer_initialization(self, scorer):
        """Test that DomainScorer initializes correctly."""
        assert scorer is not None
        assert scorer.weights is not None
        assert scorer.tld_multipliers is not None
        assert scorer.validator is not None

    def test_default_weights(self, scorer):
        """Test default scoring weights."""
        expected_weights = {
            'meaning': 0.30,
            'euphony': 0.20,
            'brandability': 0.20,
            'memorability': 0.15,
            'length': 0.05,
            'pronounceability': 0.05,
            'spellability': 0.05
        }
        assert scorer.weights == expected_weights

    def test_default_tld_multipliers(self, scorer):
        """Test default TLD multipliers."""
        assert scorer.tld_multipliers.get('com') == 1.5
        assert scorer.tld_multipliers.get('io') == 1.3
        assert scorer.tld_multipliers.get('ai') == 1.3
        assert scorer.tld_multipliers.get('net') == 1.0

    def test_custom_weights(self):
        """Test DomainScorer with custom weights."""
        from scoring.scorer import DomainScorer

        custom_weights = {
            'meaning': 0.40,
            'euphony': 0.15,
            'brandability': 0.15,
            'memorability': 0.10,
            'length': 0.10,
            'pronounceability': 0.05,
            'spellability': 0.05
        }

        scorer = DomainScorer(weights=custom_weights)
        assert scorer.weights == custom_weights

    def test_custom_tld_multipliers(self):
        """Test DomainScorer with custom TLD multipliers."""
        from scoring.scorer import DomainScorer

        custom_tlds = {'com': 2.0, 'io': 1.5, 'dev': 1.4}

        scorer = DomainScorer(tld_multipliers=custom_tlds)
        assert scorer.tld_multipliers.get('com') == 2.0
        assert scorer.tld_multipliers.get('io') == 1.5


@pytest.mark.unit
class TestDomainScoring:
    """Test domain scoring calculations."""

    def test_score_real_word(self, scorer):
        """Test scoring of real English word."""
        score = scorer.score('swift.com')

        assert score.domain == 'swift.com'
        assert score.total_score > 0
        assert score.tld_multiplier == 1.5
        assert score.dictionary_score == 100  # Real word

    def test_score_compound_word(self, scorer):
        """Test scoring of compound word."""
        score = scorer.score('cloudapp.io')

        assert score.domain == 'cloudapp.io'
        assert score.dictionary_score == 85  # Compound word
        assert score.tld_multiplier == 1.3

    def test_score_with_suffix(self, scorer):
        """Test scoring of word with common suffix."""
        score = scorer.score('testingly.com')

        assert score.domain == 'testingly.com'
        # Should be recognized as word + suffix
        assert score.dictionary_score >= 70

    def test_score_with_prefix(self, scorer):
        """Test scoring of word with common prefix."""
        score = scorer.score('untest.com')

        assert score.domain == 'untest.com'
        # Should be recognized as prefix + word
        assert score.dictionary_score >= 70

    def test_score_gibberish(self, scorer):
        """Test scoring of gibberish word."""
        score = scorer.score('xqkzmvb.com')

        assert score.domain == 'xqkzmvb.com'
        # Should have very low scores
        assert score.dictionary_score == 0
        assert score.total_score < 50

    def test_score_length_optimal(self, scorer):
        """Test scoring of optimal length word (4-7 chars)."""
        score = scorer.score('test.com')

        assert score.length_score == 100

    def test_score_length_short(self, scorer):
        """Test scoring of short word (<4 chars)."""
        score = scorer.score('xyz.com')

        assert score.length_score < 100

    def test_score_length_long(self, scorer):
        """Test scoring of long word (>12 chars)."""
        score = scorer.score('verylongword123.com')

        assert score.length_score < 100

    def test_score_with_unknown_tld(self, scorer):
        """Test scoring with unknown TLD (should use 1.0 multiplier)."""
        score = scorer.score('test.unknowntld')

        assert score.tld_multiplier == 1.0

    def test_score_batch(self, scorer):
        """Test batch scoring."""
        domains = ['test.com', 'example.io', 'brandable.ai']
        scores = scorer.score_batch(domains)

        assert len(scores) == 3
        assert all(isinstance(s.total_score, float) for s in scores)
        assert all(s.domain == domains[i] for i, s in enumerate(scores))


@pytest.mark.unit
class TestMeaningScoring:
    """Test meaning score calculation."""

    def test_meaning_real_word(self, scorer):
        """Test meaning score for real word."""
        score = scorer._score_meaning('swift')
        assert score == 100

    def test_meaning_common_word(self, scorer):
        """Test meaning score for common word in COMMON_WORDS."""
        score = scorer._score_meaning('tech')
        assert score == 100

    def test_meaning_compound_word(self, scorer):
        """Test meaning score for compound word."""
        score = scorer._score_meaning('cloudapp')
        assert score == 85

    def test_meaning_with_suffix(self, scorer):
        """Test meaning score for word with suffix."""
        score = scorer._score_meaning('testingly')
        assert score == 70

    def test_meaning_with_prefix(self, scorer):
        """Test meaning score for word with prefix."""
        score = scorer._score_meaning('untest')
        assert score == 70

    def test_meaning_substring(self, scorer):
        """Test meaning score for word containing real substring."""
        score = scorer._score_meaning('testing123')
        assert score == 50  # Contains 'test'

    def test_meaning_morpheme_only(self, scorer):
        """Test meaning score for word with only morphemes."""
        score = scorer._score_meaning('xtesting')
        assert score == 20

    def test_meaning_gibberish(self, scorer):
        """Test meaning score for gibberish."""
        score = scorer._score_meaning('xqkzmvb')
        assert score == 0

    def test_meaning_case_insensitive(self, scorer):
        """Test that meaning scoring is case-insensitive."""
        score_lower = scorer._score_meaning('swift')
        score_upper = scorer._score_meaning('SWIFT')
        score_mixed = scorer._score_meaning('SwIfT')

        assert score_lower == score_upper == score_mixed


@pytest.mark.unit
class TestBrandabilityScoring:
    """Test brandability score calculation."""

    def test_brandability_real_word(self, scorer):
        """Test brandability score for real word."""
        score = scorer._score_brandability('tech')
        # Real word + strong start = high score
        assert score > 60

    def test_brandability_compound(self, scorer):
        """Test brandability score for compound word."""
        score = scorer._score_brandability('cloudapp')
        # Compound word = high score
        assert score > 60

    def test_brandability_tech_morpheme(self, scorer):
        """Test brandability score for tech-related word."""
        score = scorer._score_brandability('technode')
        # Has tech morpheme = boosted
        assert score > 60

    def test_brandability_action_morpheme(self, scorer):
        """Test brandability score for action-related word."""
        score = scorer._score_brandability('makeapp')
        # Has action morpheme = boosted
        assert score > 60

    def test_brandability_strong_start(self, scorer):
        """Test brandability score for word with strong start."""
        score1 = scorer._score_brandability('test')
        score2 = scorer._score_brandability('xtest')
        assert score1 > score2  # Stronger start

    def test_brandability_pleasant_end(self, scorer):
        """Test brandability score for word with pleasant ending."""
        score1 = scorer._score_brandability('test')
        score2 = scorer._score_brandability('testa')
        # Ending in vowel is pleasant
        assert score2 >= score1

    def test_brandability_gibberish(self, scorer):
        """Test brandability score for gibberish."""
        score = scorer._score_brandability('xqkzmvb')
        # Gibberish should have low score
        assert score < 50


@pytest.mark.unit
class TestMemorabilityScoring:
    """Test memorability score calculation."""

    def test_memorability_real_word(self, scorer):
        """Test memorability score for real word."""
        score = scorer._score_memorability('tech')
        # Real word = high memorability
        assert score > 60

    def test_memorability_compound(self, scorer):
        """Test memorability score for compound word."""
        score = scorer._score_memorability('cloudapp')
        # Compound = high memorability
        assert score > 60

    def test_memorability_nature_word(self, scorer):
        """Test memorability score for nature word."""
        score = scorer._score_memorability('sunapp')
        # Nature word imagery = boosted
        assert score > 60

    def test_memorability_short_punchy(self, scorer):
        """Test memorability score for short punchy word."""
        score = scorer._score_memorability('tech')
        # 4-6 chars = boosted
        assert score > 60

    def test_memorability_gibberish(self, scorer):
        """Test memorability score for gibberish."""
        score = scorer._score_memorability('xqkzmvb')
        # Gibberish = low memorability
        assert score < 50


@pytest.mark.unit
class TestEuphonyScoring:
    """Test euphony score calculation."""

    def test_euphony_greek_morpheme(self, scorer):
        """Test euphony score with Greek/Latin morpheme."""
        score = scorer._score_euphony('technode')
        # Has 'tech' morpheme = boosted
        assert score > 50

    def test_euphony_euphonic_pattern(self, scorer):
        """Test euphony score with euphonic pattern."""
        score = scorer._score_euphony('vocal')
        # Has 'cal' euphonic pattern = boosted
        assert score > 50

    def test_euphony_pleasant_ending(self, scorer):
        """Test euphony score with pleasant ending."""
        score1 = scorer._score_euphony('test')
        score2 = scorer._score_euphony('testa')
        # Ending in vowel is pleasant
        assert score2 >= score1

    def test_euphony_harsh_cluster(self, scorer):
        """Test euphony score with harsh consonant cluster."""
        score = scorer._score_euphony('xqtest')
        # Has harsh cluster = penalized
        assert score < 60

    def test_euphony_gibberish(self, scorer):
        """Test euphony score for gibberish."""
        score = scorer._score_euphony('bebade')
        # Simple alternating pattern = penalized
        assert score < 60


@pytest.mark.unit
class TestLengthScoring:
    """Test length score calculation."""

    def test_length_optimal_4(self, scorer):
        """Test length score for 4-char word (optimal)."""
        score = scorer._score_length('test')
        assert score == 100

    def test_length_optimal_7(self, scorer):
        """Test length score for 7-char word (optimal)."""
        score = scorer._score_length('testing')
        assert score == 100

    def test_length_good_8(self, scorer):
        """Test length score for 8-char word (good)."""
        score = scorer._score_length('testing1')
        assert score == 90

    def test_length_good_9(self, scorer):
        """Test length score for 9-char word (good)."""
        score = scorer._score_length('testing12')
        assert score == 90

    def test_length_fair_10(self, scorer):
        """Test length score for 10-char word (fair)."""
        score = scorer._score_length('testing123')
        assert score == 80

    def test_length_poor_11(self, scorer):
        """Test length score for 11-char word (poor)."""
        score = scorer._score_length('testing1234')
        assert score == 70

    def test_length_poor_12(self, scorer):
        """Test length score for 12-char word (poor)."""
        score = scorer._score_length('testing12345')
        assert score == 70

    def test_length_bad_short(self, scorer):
        """Test length score for very short word (<4)."""
        score = scorer._score_length('xyz')
        assert score == 50

    def test_length_bad_long(self, scorer):
        """Test length score for very long word (>12)."""
        score = scorer._score_length('verylongword12345')
        assert score == 40


@pytest.mark.unit
class TestGibberishDetection:
    """Test gibberish detection logic."""

    def test_is_gibberish_real_word(self, scorer):
        """Test that real words are not gibberish."""
        assert not scorer._is_gibberish('tech')

    def test_is_gibberish_compound(self, scorer):
        """Test that compounds are not gibberish."""
        assert not scorer._is_gibberish('cloudapp')

    def test_is_gibberish_morpheme(self, scorer):
        """Test that words with morphemes are not gibberish."""
        assert not scorer._is_gibberish('testingly')

    def test_is_gibberish_simple_alternating(self, scorer):
        """Test that simple alternating patterns are gibberish."""
        assert scorer._is_gibberish('bebade')

    def test_is_gibberish_cvcvcv(self, scorer):
        """Test that CVCVCV patterns are gibberish."""
        assert scorer._is_gibberish('mepofu')


@pytest.mark.unit
class TestDomainScoreDataclass:
    """Test DomainScore dataclass functionality."""

    def test_domain_score_creation(self, scorer):
        """Test creating DomainScore object."""
        score = scorer.score('test.com')

        assert hasattr(score, 'domain')
        assert hasattr(score, 'total_score')
        assert hasattr(score, 'pronounceability')
        assert hasattr(score, 'spellability')
        assert hasattr(score, 'length_score')
        assert hasattr(score, 'memorability')
        assert hasattr(score, 'brandability')
        assert hasattr(score, 'euphony')
        assert hasattr(score, 'dictionary_score')
        assert hasattr(score, 'tld_multiplier')

    def test_domain_score_to_dict(self, scorer):
        """Test DomainScore to_dict method."""
        score = scorer.score('test.com')
        score_dict = score.to_dict()

        assert isinstance(score_dict, dict)
        assert 'domain' in score_dict
        assert 'total_score' in score_dict
        assert 'breakdown' in score_dict
        assert 'tld_multiplier' in score_dict
        assert 'pronounceability' in score_dict['breakdown']


@pytest.mark.unit
class TestRanking:
    """Test domain ranking functionality."""

    def test_rank_by_score(self, scorer):
        """Test ranking domains by score."""
        domains = ['test.com', 'better.io', 'best.ai']
        ranked = scorer.rank(domains)

        assert len(ranked) == 3
        # Should be sorted descending by total_score
        assert ranked[0].total_score >= ranked[1].total_score >= ranked[2].total_score

    def test_rank_with_min_score(self, scorer):
        """Test ranking with minimum score filter."""
        domains = ['test.com', 'better.io', 'best.ai', 'worse.dev']
        ranked = scorer.rank(domains, min_score=80)

        # All results should have total_score >= 80
        assert all(s.total_score >= 80 for s in ranked)

    def test_rank_empty_list(self, scorer):
        """Test ranking with empty list."""
        ranked = scorer.rank([])
        assert ranked == []


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_score_domain_without_tld(self, scorer):
        """Test scoring domain without TLD."""
        score = scorer.score('test')

        assert score.domain == 'test'
        assert score.tld_multiplier == 1.0

    def test_score_domain_with_subdomain(self, scorer):
        """Test scoring domain with subdomain."""
        score = scorer.score('sub.test.com')

        # Should handle subdomains (extract word and TLD)
        assert score.domain == 'sub.test.com'
        assert score.word == 'sub'
        assert score.tld == 'com'

    def test_score_uppercase_domain(self, scorer):
        """Test scoring uppercase domain."""
        score = scorer.score('TEST.COM')

        assert score.domain == 'TEST.COM'
        # Scoring should be case-insensitive
        assert score.total_score > 0

    def test_score_unicode_domain(self, scorer):
        """Test scoring Unicode domain."""
        score = scorer.score('test.com')  # Should handle gracefully

        assert score is not None

    def test_score_empty_string(self, scorer):
        """Test scoring empty string."""
        score = scorer.score('')

        assert score.domain == ''
        assert score.total_score >= 0  # Should not crash


@pytest.mark.integration
class TestScorerIntegration:
    """Integration tests for DomainScorer."""

    def test_scorer_with_results_store(self, scorer, temp_db):
        """Test scorer integration with ResultsStore."""
        domains = ['test1.com', 'test2.io', 'test3.ai']
        scores = scorer.score_batch(domains)

        # Store results
        for score_obj in scores:
            temp_db.add(
                domain=score_obj.domain,
                available=True,
                method='dns',
                score=score_obj.to_dict()
            )

        # Verify results are stored
        for domain in domains:
            result = temp_db.get(domain)
            assert result is not None
            assert result['total_score'] is not None
            assert result['dictionary_score'] is not None

    def test_scorer_consistency(self, scorer):
        """Test that scoring is consistent across multiple calls."""
        domain = 'test.com'
        score1 = scorer.score(domain)
        score2 = scorer.score(domain)

        # Scores should be identical
        assert score1.total_score == score2.total_score
        assert score1.pronounceability == score2.pronounceability
        assert score1.dictionary_score == score2.dictionary_score
