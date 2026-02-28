Affective Travelogue Backend
==============

## 1. Running
Ensure the `uv` application is installed
Start the application using:
```
uv run --env-file ../.env uvicorn main:app --port 8000
```

TODO items
==============

1. Fetch AI travelogue that was previously generated from neo4j
2. Store generated travelogue in neo4j
3. Fetch previous AI sentiment analysis from neo4j
4. Ensure all API endpoints are covered by the hurl test cases
5. Ensure happy path results in 0 errors when running hurl tests
