from fastapi import APIRouter

from models.evaluation import EvaluationCreate, EvaluationResponse
from services.eval_service import eval_service
from services.neo4j_service import neo4j_service
from services.rag_service import rag_service

router = APIRouter(prefix="/api/evaluate", tags=["Evaluation"])


@router.post("/{route_id}", response_model=EvaluationResponse)
async def evaluate_route(route_id: str, evaluation: EvaluationCreate):
    # Get AI travelogue (generate if not exists, otherwise fetch from Neo4j)
    # TODO: fetch the stored travelogue
    ai_travelogue = rag_service.generate_travelogue(route_id)

    # Calculate bertscore
    scores = eval_service.calculate_bertscore(ai_travelogue, evaluation.human_journal)

    # 3. Calculate sentiment
    human_sent = eval_service.calculate_sentiment(evaluation.human_journal)
    ai_sent = eval_service.calculate_sentiment(ai_travelogue)

    # Build result JSON
    result = {
        "bertscore_f1": scores["f1"],
        "bertscore_precision": scores["precision"],
        "bertscore_recall": scores["recall"],
        "is_equivalent": scores["is_equivalent"],
        "human_sentiment": human_sent,
        "ai_sentiment": ai_sent,
    }

    # Store in neo4j
    neo4j_service.store_evaluation(route_id, result)

    return result
