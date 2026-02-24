import yaml
from main import app

with open("openapi.yaml", "w") as f:
    yaml.dump(app.openapi(), f, sort_keys=False)

print("OpenAPI schema successfully generated at openapi.yaml")
