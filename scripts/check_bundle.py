"""Check JSON syntax, internal Markdown file links, and required context files."""
import json
from pathlib import Path
import re
root=Path(__file__).resolve().parents[1]
for p in root.rglob("*.json"):
    if not any(x in p.parts for x in (".venv","upstream",".local")):
        json.loads(p.read_text())
for name in ("README.md","START_HERE.md","AGENTS.md","docs/00-project-context.md","docs/14-roadmap.md"):
    assert (root/name).is_file(),name
for p in root.rglob("*.md"):
    for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
        if ":" in link or link.startswith("#"): continue
        target=link.split("#")[0]
        assert (p.parent/target).exists(),f"Broken link in {p}: {link}"
print("Bundle checks passed")
