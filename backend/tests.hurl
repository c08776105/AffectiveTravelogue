# tests.hurl

# -------------------------------------------------------------
# 1. Create a modern Psychogeographic Route
# -------------------------------------------------------------
POST http://localhost:8000/api/routes/
Content-Type: application/json

{
  "name": "Integration Test Derive",
  "startLat": 53.3498,
  "startLon": -6.2603
}

HTTP 201
[Captures]
route_id: jsonpath "$.id"

[Asserts]
jsonpath "$.status" == "active"
jsonpath "$.name" == "Integration Test Derive"

# -------------------------------------------------------------
# 2. Log Waypoint 1 (The starting mood)
# -------------------------------------------------------------
POST http://localhost:8000/api/waypoints/
Content-Type: application/json

{
  "routeId": "{{route_id}}",
  "latitude": 53.3498,
  "longitude": -6.2603,
  "textNote": "Starting the walk. The urban ambient noise is overwhelming, lots of grey concrete."
}

HTTP 201
[Asserts]
jsonpath "$.textNote" contains "urban ambient noise"

# -------------------------------------------------------------
# 3. Log Waypoint 2 (A shift in the environment)
# -------------------------------------------------------------
POST http://localhost:8000/api/waypoints/
Content-Type: application/json

{
  "routeId": "{{route_id}}",
  "latitude": 53.3382,
  "longitude": -6.2591,
  "textNote": "Stumbled into a quiet park. The mood shifted. Greener colors, birds chirping."
}

HTTP 201

# -------------------------------------------------------------
# 4. End the walk
# -------------------------------------------------------------
POST http://localhost:8000/api/routes/{{route_id}}/finalise
Content-Type: application/json

{
  "endLat": 53.3382,
  "endLon": -6.2591,
  "distanceKm": 1.5
}

HTTP 200
[Asserts]
jsonpath "$.distanceKm" == 1.5

# -------------------------------------------------------------
# 5. Generate AI Travelogue (RAG Pipeline)
# -------------------------------------------------------------
POST http://localhost:8000/api/generate/{{route_id}}

HTTP 200
[Captures]
ai_travelogue: jsonpath "$.travelogue"
[Asserts]
jsonpath "$.status" == "completed"

# -------------------------------------------------------------
# 6. Evaluate Semantic Equivalence
# -------------------------------------------------------------
POST http://localhost:8000/api/evaluate/{{route_id}}
Content-Type: application/json

{
  "routeId": "{{route_id}}",
  "humanJournal": "I started my walk surrounded by loud, grey concrete which felt oppressive. Eventually, I drifted into a small park where the green space and bird sounds made me feel much more relaxed."
}

HTTP 200
[Asserts]
jsonpath "$.bertscoreF1" >= 0.0
jsonpath "$.aiSentiment" exists
jsonpath "$.humanSentiment" exists
