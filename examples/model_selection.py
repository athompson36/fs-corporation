"""Run: python3 -m examples.model_selection. Selects metadata, not inference."""
import json
from pathlib import Path
from company.routing import choose_model
registry=json.loads((Path(__file__).resolve().parents[1]/"config/models.example.json").read_text())
print(json.dumps(choose_model(registry,"engineering","engineering-reviewer","code_review","internal"),indent=2))
