"""Syntax and package-boundary check. Runtime semantics are validated by Agent."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent
schema = json.loads((root / "manifest.schema.json").read_text())
assert schema["type"] == "object"
seen = set()
for path in sorted((root / "capabilities").glob("*.json")):
    package = json.loads(path.read_text())
    assert set(schema["required"]) <= package.keys(), path.name
    assert not (package.keys() - schema["properties"].keys()), path.name
    assert package["id"] not in seen, path.name
    seen.add(package["id"])
    assert package["steps"], path.name
    assert all(step["kind"] in {"say", "confirm", "timer"} for step in package["steps"])
print(f"Validated JSON structure for {len(seen)} capability packages")
