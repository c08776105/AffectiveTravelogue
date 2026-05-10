import asyncio

import pytest
from fastapi import HTTPException

from models.route import TravelogueCreate
from services.rag_service import TravelogueGenerationError


class TestGenerateApi:

    def test_failed_generation_returns_502_and_does_not_store(self, mocker):
        from api import generate

        mocker.patch.object(generate.neo4j_service, "get_route", return_value={"id": "r1"})
        mock_store = mocker.patch.object(generate.neo4j_service, "store_travelogue_node")
        mocker.patch.object(
            generate.rag_service,
            "generate_travelogue",
            side_effect=TravelogueGenerationError("Generation failed: Ollama timeout"),
        )

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                generate.generate_travelogue("r1", TravelogueCreate(prompt_type="zero_shot"))
            )

        assert exc.value.status_code == 502
        mock_store.assert_not_called()


class TestEvaluateApi:

    def test_auto_generation_failure_does_not_store_travelogue(self, mocker):
        from api import evaluate

        mocker.patch.object(evaluate.neo4j_service, "get_route", return_value={"id": "r1"})
        mocker.patch.object(evaluate.neo4j_service, "get_travelogues", return_value=[])
        mock_store = mocker.patch.object(evaluate.neo4j_service, "store_travelogue_node")
        mocker.patch.object(
            evaluate.rag_service,
            "generate_travelogue",
            side_effect=TravelogueGenerationError("Generation failed: Ollama timeout"),
        )

        with pytest.raises(HTTPException) as exc:
            asyncio.run(evaluate.evaluate_route("r1", travelogue_id=None))

        assert exc.value.status_code == 502
        mock_store.assert_not_called()
