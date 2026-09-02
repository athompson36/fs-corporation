"""Check JSON syntax, internal Markdown file links, and required context files."""
import json
from pathlib import Path
import re
root=Path(__file__).resolve().parents[1]
_skip=(".venv","upstream",".local","node_modules")
for p in root.rglob("*.json"):
    if not any(x in p.parts for x in _skip):
        json.loads(p.read_text())
for name in ("README.md","START_HERE.md","AGENTS.md","docs/00-project-context.md","docs/14-roadmap.md","docs/26-owner-live-configuration.md","fs-corporation.code-workspace"):
    assert (root/name).is_file(),name
for p in root.rglob("*.md"):
    if any(x in p.parts for x in _skip):
        continue
    for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
        if ":" in link or link.startswith("#"): continue
        target=link.split("#")[0]
        assert (p.parent/target).exists(),f"Broken link in {p}: {link}"
print("Bundle checks passed")
