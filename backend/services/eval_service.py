import numpy as np
from bert_score import score
from scipy import stats
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from utils.config import settings
from utils.logger import logger


class EvaluationService:
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()

    def calculate_bertscore(self, ai_travelogue: str, human_journal: str):
        """
        Calculate BERTScore F1 value
        """
        try:
            P, R, F1 = score(
                [ai_travelogue],
                [human_journal],
                lang="en",
                model_type=settings.BERTSCORE_MODEL,
                verbose=False,
                device="cpu",  # Also set `export PYTORCH_ENABLE_MPS_FALLBACK=1` in terminal before running the app
            )
            return {
                "precision": float(P[0].item()),
                "recall": float(R[0].item()),
                "f1": float(F1[0].item()),
                "is_equivalent": F1[0].item() >= 0.85,
            }
        except Exception as e:
            logger.error(f"BERTScore calculation failed: {e}")
            return {"precision": 0, "recall": 0, "f1": 0, "is_equivalent": False}

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
