import numpy as np
from bert_score import BERTScorer
from scipy import stats
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from utils.config import settings
from utils.logger import logger


class EvaluationService:
    # Character limit fed to the tokenizer. At ~3.5 chars/token this comfortably
    # stays under a 512-token budget for any model.
    _MAX_CHARS = 1800

    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
        self._scorer: BERTScorer | None = None

    def _get_scorer(self) -> BERTScorer:
        """
        Lazily initialise (and cache) the BERTScorer.

        Using BERTScorer instead of the score() helper gives us direct access to
        the loaded tokenizer so we can clamp model_max_length.  Several models
        (DeBERTa in particular) set model_max_length to ~1e30; when bert_score
        passes that value to tokenizers' Rust enable_truncation(), the conversion
        from Python int → i64 raises "int too big to convert".  Clamping to 512
        fixes the overflow without changing the effective scoring window.
        """
        if self._scorer is None:
            self._scorer = BERTScorer(
                model_type=settings.BERTSCORE_MODEL,
                device="cpu",  # set PYTORCH_ENABLE_MPS_FALLBACK=1 on Apple Silicon
                all_layers=False,
            )
            tok = self._scorer._tokenizer
            if tok.model_max_length > 512:
                tok.model_max_length = 512
            logger.info(f"BERTScorer ready. Model: {settings.BERTSCORE_MODEL}")
        return self._scorer

    def warm_up(self) -> None:
        """Eagerly load the BERTScorer on startup so weights are cached in memory for the process lifetime."""
        self._get_scorer()

    def calculate_bertscore(self, ai_travelogue: str, human_journal: str):
        """Calculate BERTScore F1 between the AI travelogue and the human journal."""
        try:
            ai_text = ai_travelogue[: self._MAX_CHARS]
            human_text = human_journal[: self._MAX_CHARS]

            scorer = self._get_scorer()
            P, R, F1 = scorer.score([ai_text], [human_text], verbose=False)
            return {
                "precision": float(P[0].item()),
                "recall": float(R[0].item()),
                "f1": float(F1[0].item()),
                "is_equivalent": F1[0].item() >= 0.85,
                "bertscore_model": settings.BERTSCORE_MODEL,
            }
        except Exception as e:
            logger.error(f"BERTScore calculation failed: {e}", exc_info=True)
            return {"precision": 0, "recall": 0, "f1": 0, "is_equivalent": False, "bertscore_model": settings.BERTSCORE_MODEL}

    def calculate_sentiment(self, text: str) -> float:
        """
        Calculate VADER compound sentiment score.
        """
        try:
            scores = self.analyzer.polarity_scores(text)
            return scores["compound"]
        except Exception as e:
            logger.error(f"Sentiment calculation failed: {e}")
            return 0.0

    def run_statistical_tests(self, f1_scores: list[float], threshold: float = 0.85):
        """
        Run Shapiro-Wilk and T-Test/Wilcoxon.
        """
        if len(f1_scores) < 3:
            return {"error": "Not enough samples for statistical testing"}

        # Normality check
        stat, p_val_norm = stats.shapiro(f1_scores)
        is_normal = p_val_norm > 0.05

        if is_normal:
            # One-sample T-test
            t_stat, p_val = stats.ttest_1samp(
                f1_scores, threshold, alternative="greater"
            )
            test_name = "One-Sample T-Test"
        else:
            # Wilcoxon Signed-Rank Test
            adjusted = [x - threshold for x in f1_scores]
            res = stats.wilcoxon(adjusted, alternative="greater")
            t_stat, p_val = res.statistic, res.pvalue
            test_name = "Wilcoxon Signed-Rank Test"

        return {
            "test_name": test_name,
            "is_normal": is_normal,
            "statistic": float(t_stat),
            "p_value": float(p_val),
            "reject_h0": p_val < 0.05,
            "mean": float(np.mean(f1_scores)),
            "std": float(np.std(f1_scores)),
        }


eval_service = EvaluationService()
