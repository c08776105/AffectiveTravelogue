"""
Tests for EvaluationService.

calculate_bertscore_pairs is covered exhaustively because it is the primary
metric driving the research evaluation pipeline.
"""

import pytest

from tests.conftest import make_mock_scorer


# ===========================================================================
# calculate_bertscore_pairs
# ===========================================================================

class TestCalculateBertscorePairs:

    # -----------------------------------------------------------------------
    # Empty inputs
    # -----------------------------------------------------------------------

    def test_empty_both_lists_returns_zero_dict(self, eval_svc):
        result = eval_svc.calculate_bertscore_pairs([], [])

        assert result["f1"] == 0.0
        assert result["precision"] == 0.0
        assert result["recall"] == 0.0
        assert result["is_equivalent"] is False
        assert result["is_truncated"] is False
        assert result["pair_f1"] == []
        assert result["pair_precision"] == []
        assert result["pair_recall"] == []
        assert result["pair_is_truncated"] == []

    def test_empty_ai_list_returns_zero_dict(self, eval_svc):
        result = eval_svc.calculate_bertscore_pairs(["human note"], [])
        assert result["f1"] == 0.0
        assert result["pair_f1"] == []

    def test_empty_human_list_returns_zero_dict(self, eval_svc):
        result = eval_svc.calculate_bertscore_pairs([], ["ai paragraph"])
        assert result["f1"] == 0.0
        assert result["pair_f1"] == []

    # -----------------------------------------------------------------------
    # Single pair
    # -----------------------------------------------------------------------

    def test_single_pair_high_f1_is_equivalent(self, eval_svc, mocker):
        scorer = make_mock_scorer([0.92], [0.91], [0.90])
        mocker.patch.object(eval_svc, "_get_scorer", return_value=scorer)

        result = eval_svc.calculate_bertscore_pairs(
            ["We walked through the park."],
            ["We began our walk through the park."],
        )

        assert pytest.approx(result["f1"], abs=1e-4) == 0.90
        assert pytest.approx(result["precision"], abs=1e-4) == 0.92
        assert pytest.approx(result["recall"], abs=1e-4) == 0.91
        assert result["is_equivalent"] is True
        assert result["pair_f1"] == pytest.approx([0.90], abs=1e-4)

    def test_single_pair_low_f1_not_equivalent(self, eval_svc, mocker):
        scorer = make_mock_scorer([0.72], [0.68], [0.70])
        mocker.patch.object(eval_svc, "_get_scorer", return_value=scorer)

        result = eval_svc.calculate_bertscore_pairs(
            ["A sunny walk by the river."],
            ["We trudged through urban sprawl."],
        )

        assert pytest.approx(result["f1"], abs=1e-4) == 0.70
        assert result["is_equivalent"] is False

    # -----------------------------------------------------------------------
    # Equivalence boundary
    # -----------------------------------------------------------------------

    def test_f1_exactly_085_is_equivalent(self, eval_svc, mocker):
        scorer = make_mock_scorer([0.85], [0.85], [0.85])
        mocker.patch.object(eval_svc, "_get_scorer", return_value=scorer)

        result = eval_svc.calculate_bertscore_pairs(["a"], ["b"])
        assert result["is_equivalent"] is True

    def test_f1_just_below_085_not_equivalent(self, eval_svc, mocker):
        scorer = make_mock_scorer([0.849], [0.849], [0.849])
        mocker.patch.object(eval_svc, "_get_scorer", return_value=scorer)

        result = eval_svc.calculate_bertscore_pairs(["a"], ["b"])
        assert result["is_equivalent"] is False

    # -----------------------------------------------------------------------
    # Macro averaging over multiple pairs
    # -----------------------------------------------------------------------

    def test_macro_averaging_is_mean_of_pair_scores(self, eval_svc, mocker):
        p_vals  = [0.90, 0.80, 0.70]
        r_vals  = [0.88, 0.78, 0.68]
        f1_vals = [0.89, 0.79, 0.69]
        scorer = make_mock_scorer(p_vals, r_vals, f1_vals)
        mocker.patch.object(eval_svc, "_get_scorer", return_value=scorer)

        human = ["note one", "note two", "note three"]
        ai    = ["para one", "para two", "para three"]
        result = eval_svc.calculate_bertscore_pairs(human, ai)

        expected_f1 = sum(f1_vals) / 3
        expected_p  = sum(p_vals) / 3
        expected_r  = sum(r_vals) / 3

        assert pytest.approx(result["f1"],       abs=1e-5) == expected_f1
        assert pytest.approx(result["precision"], abs=1e-5) == expected_p
        assert pytest.approx(result["recall"],    abs=1e-5) == expected_r
        assert result["pair_f1"]        == pytest.approx(f1_vals, abs=1e-4)
        assert result["pair_precision"] == pytest.approx(p_vals,  abs=1e-4)
        assert result["pair_recall"]    == pytest.approx(r_vals,  abs=1e-4)

    def test_pair_count_matches_input_length(self, eval_svc, mocker):
        scorer = make_mock_scorer([0.80, 0.75], [0.78, 0.73], [0.79, 0.74])
        mocker.patch.object(eval_svc, "_get_scorer", return_value=scorer)

        result = eval_svc.calculate_bertscore_pairs(
            ["h1", "h2"], ["a1", "a2"]
        )
        assert len(result["pair_f1"]) == 2
        assert len(result["pair_precision"]) == 2
        assert len(result["pair_recall"]) == 2
        assert len(result["pair_is_truncated"]) == 2

    # -----------------------------------------------------------------------
    # Mismatched list lengths — zip truncates to the shorter
    # -----------------------------------------------------------------------

    def test_more_human_notes_than_ai_paragraphs_uses_min_length(self, eval_svc, mocker):
        scorer = make_mock_scorer([0.80, 0.75], [0.78, 0.73], [0.79, 0.74])
        mocker.patch.object(eval_svc, "_get_scorer", return_value=scorer)

        result = eval_svc.calculate_bertscore_pairs(
            ["h1", "h2", "h3"],   # 3 human notes
            ["a1", "a2"],          # 2 AI paragraphs → 2 pairs
        )
        assert len(result["pair_f1"]) == 2
        # Scorer was called with exactly 2 texts per side
        call_args = scorer.score.call_args
        assert len(call_args.args[0]) == 2  # ai_texts
        assert len(call_args.args[1]) == 2  # human_texts

    def test_more_ai_paragraphs_than_human_notes_uses_min_length(self, eval_svc, mocker):
        scorer = make_mock_scorer([0.80], [0.78], [0.79])
        mocker.patch.object(eval_svc, "_get_scorer", return_value=scorer)

        result = eval_svc.calculate_bertscore_pairs(
            ["h1"],              # 1 human note
            ["a1", "a2", "a3"], # 3 AI paragraphs → 1 pair
        )
        assert len(result["pair_f1"]) == 1

    # -----------------------------------------------------------------------
    # Truncation detection
    # -----------------------------------------------------------------------

    def test_truncation_flag_set_when_token_count_exceeds_512(self, eval_svc, mocker):
        # encode() called twice per pair (once for human, once for ai)
        # Pair 0: human=600 tokens (truncated), ai=100 tokens
        # Pair 1: human=100 tokens, ai=100 tokens (not truncated)
        token_lengths = [600, 100, 100, 100]
        scorer = make_mock_scorer([0.80, 0.80], [0.78, 0.78], [0.79, 0.79],
                                  token_lengths=token_lengths)
        mocker.patch.object(eval_svc, "_get_scorer", return_value=scorer)

        result = eval_svc.calculate_bertscore_pairs(["h1", "h2"], ["a1", "a2"])

        assert result["pair_is_truncated"][0] is True   # pair 0 truncated
        assert result["pair_is_truncated"][1] is False  # pair 1 not truncated
        assert result["is_truncated"] is True           # any() → True

    def test_no_truncation_when_all_token_counts_under_512(self, eval_svc, mocker):
        token_lengths = [100, 120, 90, 110]  # all under 512
        scorer = make_mock_scorer([0.80, 0.80], [0.78, 0.78], [0.79, 0.79],
                                  token_lengths=token_lengths)
        mocker.patch.object(eval_svc, "_get_scorer", return_value=scorer)

        result = eval_svc.calculate_bertscore_pairs(["h1", "h2"], ["a1", "a2"])

        assert result["pair_is_truncated"] == [False, False]
        assert result["is_truncated"] is False

    def test_truncation_flag_true_when_exactly_513_tokens(self, eval_svc, mocker):
        token_lengths = [513, 50]
        scorer = make_mock_scorer([0.80], [0.78], [0.79],
                                  token_lengths=token_lengths)
        mocker.patch.object(eval_svc, "_get_scorer", return_value=scorer)

        result = eval_svc.calculate_bertscore_pairs(["h"], ["a"])
        assert result["pair_is_truncated"][0] is True

    # -----------------------------------------------------------------------
    # Text clamping at _MAX_CHARS
    # -----------------------------------------------------------------------

    def test_long_text_is_clamped_before_scoring(self, eval_svc, mocker):
        scorer = make_mock_scorer([0.80], [0.78], [0.79])
        mocker.patch.object(eval_svc, "_get_scorer", return_value=scorer)

        long_human = "a" * 5000
        long_ai    = "b" * 5000
        eval_svc.calculate_bertscore_pairs([long_human], [long_ai])

        ai_texts, human_texts = scorer.score.call_args.args[:2]
        assert len(ai_texts[0])    <= eval_svc._MAX_CHARS
        assert len(human_texts[0]) <= eval_svc._MAX_CHARS

    # -----------------------------------------------------------------------
    # Scorer call argument order
    # -----------------------------------------------------------------------

    def test_scorer_called_with_ai_first_then_human(self, eval_svc, mocker):
        """BERTScore convention: score(candidates, references)."""
        scorer = make_mock_scorer([0.80], [0.78], [0.79])
        mocker.patch.object(eval_svc, "_get_scorer", return_value=scorer)

        eval_svc.calculate_bertscore_pairs(["human note"], ["ai para"])

        ai_texts, human_texts = scorer.score.call_args.args[:2]
        assert ai_texts    == ["ai para"]
        assert human_texts == ["human note"]

    # -----------------------------------------------------------------------
    # Exception handling
    # -----------------------------------------------------------------------

    def test_scorer_exception_returns_zero_dict_with_correct_pair_length(self, eval_svc, mocker):
        scorer = make_mock_scorer([0.80, 0.78], [0.79, 0.77], [0.79, 0.78])
        scorer.score.side_effect = RuntimeError("CUDA OOM")
        mocker.patch.object(eval_svc, "_get_scorer", return_value=scorer)

        result = eval_svc.calculate_bertscore_pairs(["h1", "h2"], ["a1", "a2"])

        assert result["f1"] == 0.0
        assert result["precision"] == 0.0
        assert result["recall"] == 0.0
        assert result["is_equivalent"] is False
        assert result["pair_f1"]        == [0.0, 0.0]
        assert result["pair_precision"] == [0.0, 0.0]
        assert result["pair_recall"]    == [0.0, 0.0]
        assert result["pair_is_truncated"] == [False, False]

    def test_scorer_exception_single_pair_returns_one_zero(self, eval_svc, mocker):
        scorer = make_mock_scorer([0.80], [0.79], [0.79])
        scorer.score.side_effect = ValueError("model error")
        mocker.patch.object(eval_svc, "_get_scorer", return_value=scorer)

        result = eval_svc.calculate_bertscore_pairs(["h"], ["a"])
        assert result["pair_f1"] == [0.0]

    # -----------------------------------------------------------------------
    # Return-value keys completeness
    # -----------------------------------------------------------------------

    def test_result_contains_all_expected_keys(self, eval_svc, mocker):
        scorer = make_mock_scorer([0.80], [0.78], [0.79])
        mocker.patch.object(eval_svc, "_get_scorer", return_value=scorer)

        result = eval_svc.calculate_bertscore_pairs(["h"], ["a"])

        required_keys = {
            "f1", "precision", "recall", "is_equivalent",
            "bertscore_model", "is_truncated",
            "pair_f1", "pair_precision", "pair_recall", "pair_is_truncated",
        }
        assert required_keys == set(result.keys())


# ===========================================================================
# calculate_bertscore (legacy single-pair)
# ===========================================================================

class TestCalculateBertscore:

    def test_basic_scores_returned(self, eval_svc, mocker):
        scorer = make_mock_scorer([0.88], [0.86], [0.87])
        mocker.patch.object(eval_svc, "_get_scorer", return_value=scorer)

        result = eval_svc.calculate_bertscore("ai text", "human text")

        assert pytest.approx(result["f1"],       abs=1e-4) == 0.87
        assert pytest.approx(result["precision"], abs=1e-4) == 0.88
        assert pytest.approx(result["recall"],    abs=1e-4) == 0.86

    def test_is_equivalent_true_above_threshold(self, eval_svc, mocker):
        scorer = make_mock_scorer([0.86], [0.86], [0.86])
        mocker.patch.object(eval_svc, "_get_scorer", return_value=scorer)

        result = eval_svc.calculate_bertscore("a", "b")
        assert result["is_equivalent"] is True

    def test_is_equivalent_false_below_threshold(self, eval_svc, mocker):
        scorer = make_mock_scorer([0.70], [0.70], [0.70])
        mocker.patch.object(eval_svc, "_get_scorer", return_value=scorer)

        result = eval_svc.calculate_bertscore("a", "b")
        assert result["is_equivalent"] is False

    def test_exception_returns_zero_dict(self, eval_svc, mocker):
        scorer = make_mock_scorer([0.80], [0.80], [0.80])
        scorer.score.side_effect = RuntimeError("fail")
        mocker.patch.object(eval_svc, "_get_scorer", return_value=scorer)

        result = eval_svc.calculate_bertscore("a", "b")
        assert result["f1"] == 0
        assert result["is_equivalent"] is False


# ===========================================================================
# calculate_sentiment
# ===========================================================================

class TestCalculateSentiment:
    """VADER is deterministic and lightweight — no mocking needed."""

    def test_positive_text_returns_positive_score(self, eval_svc):
        score = eval_svc.calculate_sentiment("What a wonderful, joyful walk through the beautiful park!")
        assert score > 0.05

    def test_negative_text_returns_negative_score(self, eval_svc):
        score = eval_svc.calculate_sentiment("Terrible, miserable, depressing slog through grey concrete.")
        assert score < -0.05

    def test_neutral_text_returns_near_zero(self, eval_svc):
        score = eval_svc.calculate_sentiment("We walked along the road.")
        assert -0.05 <= score <= 0.05

    def test_empty_string_returns_zero(self, eval_svc):
        score = eval_svc.calculate_sentiment("")
        assert score == 0.0

    def test_returns_float(self, eval_svc):
        score = eval_svc.calculate_sentiment("some text")
        assert isinstance(score, float)


# ===========================================================================
# run_statistical_tests
# ===========================================================================

class TestRunStatisticalTests:

    def test_insufficient_samples_returns_error(self, eval_svc):
        result = eval_svc.run_statistical_tests([0.80, 0.82])
        assert "error" in result

    def test_exactly_two_samples_returns_error(self, eval_svc):
        result = eval_svc.run_statistical_tests([0.80, 0.90])
        assert "error" in result

    def test_three_samples_returns_result_keys(self, eval_svc):
        result = eval_svc.run_statistical_tests([0.80, 0.82, 0.84])
        expected_keys = {"test_name", "is_normal", "statistic", "p_value", "reject_h0", "mean", "std"}
        assert expected_keys.issubset(result.keys())

    def test_mean_and_std_correct(self, eval_svc):
        scores = [0.80, 0.85, 0.90]
        result = eval_svc.run_statistical_tests(scores)
        assert pytest.approx(result["mean"], abs=1e-6) == pytest.approx(sum(scores) / len(scores))

    def test_normal_distribution_uses_ttest(self, eval_svc, mocker):
        # Force Shapiro-Wilk to report normality (p > 0.05)
        mocker.patch("services.eval_service.stats.shapiro", return_value=(0.99, 0.8))
        mocker.patch("services.eval_service.stats.ttest_1samp", return_value=(2.5, 0.03))

        result = eval_svc.run_statistical_tests([0.80, 0.85, 0.90])
        assert result["test_name"] == "One-Sample T-Test"

    def test_non_normal_distribution_uses_wilcoxon(self, eval_svc, mocker):
        # Force Shapiro-Wilk to report non-normality (p < 0.05)
        mocker.patch("services.eval_service.stats.shapiro", return_value=(0.70, 0.02))

        from unittest.mock import MagicMock
        wilcoxon_result = MagicMock()
        wilcoxon_result.statistic = 6.0
        wilcoxon_result.pvalue = 0.04
        mocker.patch("services.eval_service.stats.wilcoxon", return_value=wilcoxon_result)

        result = eval_svc.run_statistical_tests([0.80, 0.85, 0.90])
        assert result["test_name"] == "Wilcoxon Signed-Rank Test"

    def test_reject_h0_true_when_p_below_005(self, eval_svc, mocker):
        mocker.patch("services.eval_service.stats.shapiro", return_value=(0.99, 0.8))
        mocker.patch("services.eval_service.stats.ttest_1samp", return_value=(3.0, 0.01))

        result = eval_svc.run_statistical_tests([0.80, 0.85, 0.90])
        assert result["reject_h0"] is True

    def test_reject_h0_false_when_p_above_005(self, eval_svc, mocker):
        mocker.patch("services.eval_service.stats.shapiro", return_value=(0.99, 0.8))
        mocker.patch("services.eval_service.stats.ttest_1samp", return_value=(0.5, 0.30))

        result = eval_svc.run_statistical_tests([0.80, 0.85, 0.90])
        assert result["reject_h0"] is False
