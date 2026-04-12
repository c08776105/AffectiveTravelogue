import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from models.evaluation import EvaluationResponse
from services.eval_service import eval_service
from services.neo4j_service import neo4j_service
from services.rag_service import rag_service

router = APIRouter(prefix="/api/evaluate", tags=["Evaluation"])


def _get_human_notes(route_id: str) -> list[str]:
    """Return waypoint text notes as an ordered list (oldest first)."""
    waypoints = neo4j_service.get_waypoints(route_id)
    notes = []
    for wp in waypoints:
        raw = wp.get("text_note")
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
            text = parsed.get("text") or parsed.get("content") or raw
        except (json.JSONDecodeError, AttributeError, TypeError):
            text = raw
        if text and text.strip():
            notes.append(text.strip())
    return notes


def _split_ai_paragraphs(travelogue: str) -> list[str]:
    """Split AI travelogue into per-waypoint paragraphs."""
    paragraphs = [p.strip() for p in travelogue.split("\n\n") if p.strip()]
    # Fall back to single-newline split if the model produced no double newlines
    if len(paragraphs) <= 1:
        paragraphs = [p.strip() for p in travelogue.split("\n") if p.strip()]
    return paragraphs


@router.get("/{route_id}", response_model=EvaluationResponse)
async def get_evaluation(route_id: str, travelogue_id: Optional[str] = Query(None)):
    if travelogue_id:
        eval_data = neo4j_service.get_evaluation_for_travelogue(travelogue_id)
    else:
        eval_data = neo4j_service.get_evaluation(route_id)
    if not eval_data:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return dict(eval_data)


@router.post("/{route_id}", response_model=EvaluationResponse)
async def evaluate_route(route_id: str, travelogue_id: Optional[str] = Query(None)):
    route = neo4j_service.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    # Resolve which travelogue to evaluate
    if travelogue_id:
        travelogue_node = neo4j_service.get_travelogue(travelogue_id)
        if not travelogue_node:
            raise HTTPException(status_code=404, detail="Travelogue not found")
        ai_travelogue = travelogue_node["text"]
    else:
        travelogues = neo4j_service.get_travelogues(route_id)
        if travelogues:
            travelogue_node = travelogues[0]
            travelogue_id = travelogue_node["id"]
            ai_travelogue = travelogue_node["text"]
        else:
            result = rag_service.generate_travelogue(route_id)
            travelogue_node = neo4j_service.store_travelogue_node(
                route_id, result["text"], result["llm_model"], result["prompt_type"]
            )
            travelogue_id = travelogue_node["id"]
            ai_travelogue = travelogue_node["text"]

    human_notes = _get_human_notes(route_id)
    if not human_notes:
        raise HTTPException(
            status_code=422,
            detail="No waypoint notes found for this route. Add notes during your walk before evaluating.",
        )

    ai_paragraphs = _split_ai_paragraphs(ai_travelogue)

    neo4j_service.delete_evaluation_for_travelogue(travelogue_id)

    scores = eval_service.calculate_bertscore_pairs(human_notes, ai_paragraphs)

    human_journal = "\n\n".join(human_notes)
    human_sent = eval_service.calculate_sentiment(human_journal)
    ai_sent = eval_service.calculate_sentiment(ai_travelogue)

    result = {
        "bertscore_f1": scores["f1"],
        "bertscore_precision": scores["precision"],
        "bertscore_recall": scores["recall"],
        "is_equivalent": scores["is_equivalent"],
        "human_sentiment": human_sent,
        "ai_sentiment": ai_sent,
        "human_journal": human_journal,
        "ai_travelogue": ai_travelogue,
        "bertscore_model": scores["bertscore_model"],
        "travelogue_id": travelogue_id,
        "prompt_type": travelogue_node.get("prompt_type", "zero_shot"),
        "is_truncated": scores["is_truncated"],
        "pair_f1": scores["pair_f1"],
        "pair_precision": scores["pair_precision"],
        "pair_recall": scores["pair_recall"],
        "pair_is_truncated": scores["pair_is_truncated"],
        "human_waypoint_count": len(human_notes),
        "ai_paragraph_count": len(ai_paragraphs),
    }

    neo4j_service.store_evaluation_for_travelogue(travelogue_id, result)
    return result
