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
        passes that value to tokenizers' must enable_truncation(), the conversion
        from Python int → i64 raises "int too big to convert".  Clamping to 512
        fixes the overflow without changing the effective scoring window.
        """
        if self._scorer is None:
            self._scorer = BERTScorer(
                model_type=settings.BERTSCORE_MODEL,
                device="cpu",  # set PYTORCH_ENABLE_MPS_FALLBACK=1 on Apple Silicon
                all_layers=False,
                rescale_with_baseline=True,
                lang="en",
            )
            tok = self._scorer._tokenizer
            if tok.model_max_length > 512:
                tok.model_max_length = 512
            logger.info(f"BERTScorer ready. Model: {settings.BERTSCORE_MODEL}")

            # Print ceiling similiarity values
            P, R, F1 = self._scorer.score(
                ["The quick brown fox jumps over the lazy dog."],
                ["The quick brown fox jumps over the lazy dog."],
            )
            print(
                f"Ceil vals: F1: {F1.item():.4f}, P: {P.item():.4f}, R: {R.item():.4f}"
            )

            # Paraphrased
            P, R, F1 = self._scorer.score(
                ["We walked along the old stone bridge crossing the river."],
                ["The group crossed the ancient bridge that spanned the river."],
            )

            print(
                f"Paraphrased vals: F1: {F1.item():.4f}, P: {P.item():.4f}, R: {R.item():.4f}"
            )  # expect ~0.55–0.75 w/rescaled on

            # Unrelated
            P, R, F1 = self._scorer.score(
                ["The river flows north."], ["Stock prices fell sharply."]
            )

            print(
                f"Worst case vals: F1: {F1.item():.4f}, P: {P.item():.4f}, R: {R.item():.4f}"
            )  # expect ~0.0–0.15
        return self._scorer

    def warm_up(self) -> None:
        """Eagerly load the BERTScorer on startup so weights are cached in memory for the process lifetime."""
        self._get_scorer()

    def calculate_bertscore(self, ai_travelogue: str, human_journal: str):
        """Calculate BERTScore F1 between the AI travelogue and the human journal (legacy single-pair path)."""
        try:
            ai_text = ai_travelogue[: self._MAX_CHARS]
            human_text = human_journal[: self._MAX_CHARS]

            scorer = self._get_scorer()
            tok = scorer._tokenizer
            ai_token_count = len(tok.encode(ai_text, add_special_tokens=True))
            human_token_count = len(tok.encode(human_text, add_special_tokens=True))
            is_truncated = ai_token_count > 512 or human_token_count > 512

            P, R, F1 = scorer.score([ai_text], [human_text], verbose=False)
            return {
                "precision": float(P[0].item()),
                "recall": float(R[0].item()),
                "f1": float(F1[0].item()),
                "is_equivalent": F1[0].item() >= 0.85,
                "bertscore_model": settings.BERTSCORE_MODEL,
                "is_truncated": is_truncated,
            }
        except Exception as e:
            logger.error(f"BERTScore calculation failed: {e}", exc_info=True)
            return {
                "precision": 0,
                "recall": 0,
                "f1": 0,
                "is_equivalent": False,
                "bertscore_model": settings.BERTSCORE_MODEL,
                "is_truncated": False,
            }

    def calculate_bertscore_pairs(
        self, human_notes: list[str], ai_paragraphs: list[str]
    ) -> dict:
        """
        Paragraph-to-paragraph BERTScore comparison with macro averaging.

        Pairs human_notes[i] with ai_paragraphs[i] up to min(len) of both.
        All pairs are scored in a single batched scorer call for efficiency.
        Returns macro-averaged precision/recall/F1 plus per-pair detail arrays.
        """
        pairs = list(zip(human_notes, ai_paragraphs))
        if not pairs:
            return {
                "precision": 0.0,
                "recall": 0.0,
                "f1": 0.0,
                "is_equivalent": False,
                "bertscore_model": settings.BERTSCORE_MODEL,
                "is_truncated": False,
                "pair_f1": [],
                "pair_precision": [],
                "pair_recall": [],
                "pair_is_truncated": [],
            }

        try:
            scorer = self._get_scorer()
            tok = scorer._tokenizer

            human_texts = [h[: self._MAX_CHARS] for h, _ in pairs]
            ai_texts = [a[: self._MAX_CHARS] for _, a in pairs]

            pair_is_truncated = [
                len(tok.encode(h, add_special_tokens=True)) > 512
                or len(tok.encode(a, add_special_tokens=True)) > 512
                for h, a in zip(human_texts, ai_texts)
            ]

            P_all, R_all, F1_all = scorer.score(ai_texts, human_texts, verbose=False)

            pair_f1 = [float(v.item()) for v in F1_all]
            pair_precision = [float(v.item()) for v in P_all]
            pair_recall = [float(v.item()) for v in R_all]

            n = len(pairs)
            macro_f1 = sum(pair_f1) / n
            macro_p = sum(pair_precision) / n
            macro_r = sum(pair_recall) / n

            logger.info(
                f"BERTScore pairs: {n} pair(s), macro F1={macro_f1:.4f}, "
                f"truncated={sum(pair_is_truncated)}/{n}"
            )

            return {
                "precision": macro_p,
                "recall": macro_r,
                "f1": macro_f1,
                "is_equivalent": macro_f1 >= 0.85,
                "bertscore_model": settings.BERTSCORE_MODEL,
                "is_truncated": any(pair_is_truncated),
                "pair_f1": pair_f1,
                "pair_precision": pair_precision,
                "pair_recall": pair_recall,
                "pair_is_truncated": pair_is_truncated,
            }
        except Exception as e:
            logger.error(f"BERTScore pair scoring failed: {e}", exc_info=True)
            n = len(pairs)
            return {
                "precision": 0.0,
                "recall": 0.0,
                "f1": 0.0,
                "is_equivalent": False,
                "bertscore_model": settings.BERTSCORE_MODEL,
                "is_truncated": False,
                "pair_f1": [0.0] * n,
                "pair_precision": [0.0] * n,
                "pair_recall": [0.0] * n,
                "pair_is_truncated": [False] * n,
            }

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
