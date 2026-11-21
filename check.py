"""Offline package checks and text walkthrough; no Agent, network or audio I/O."""
import argparse
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
SCHEMA = json.loads((ROOT / "manifest.schema.json").read_text(encoding="utf-8"))
PLACEHOLDER = re.compile(r"\{\{([a-z][a-z0-9_-]*)\}\}")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_schema(value, rule, location="manifest"):
    """Check only the JSON Schema keywords used by this repository's schema."""
    types = {"object": dict, "array": list, "string": str, "boolean": bool, "integer": int}
    if "type" in rule:
        require(type(value) is types[rule["type"]], f"{location}: expected {rule['type']}")
    if "enum" in rule:
        require(value in rule["enum"], f"{location}: unsupported value")
    if "const" in rule:
        require(value == rule["const"], f"{location}: unexpected value")
    if isinstance(value, dict):
        require(set(rule.get("required", [])) <= value.keys(), f"{location}: missing required keys")
        properties = rule.get("properties", {})
        if rule.get("additionalProperties") is False:
            require(not value.keys() - properties.keys(), f"{location}: unknown keys")
        for key in value.keys() & properties.keys():
            check_schema(value[key], properties[key], f"{location}.{key}")
    if isinstance(value, list):
        require(rule.get("minItems", 0) <= len(value) <= rule.get("maxItems", len(value)), f"{location}: invalid item count")
        if "items" in rule:
            for index, item in enumerate(value):
                check_schema(item, rule["items"], f"{location}[{index}]")
    if isinstance(value, str):
        # Agent uses Go len(string), so enforce UTF-8 bytes as well as schema character limits.
        require(rule.get("minLength", 0) <= len(value) and len(value.encode("utf-8")) <= rule.get("maxLength", len(value.encode("utf-8"))), f"{location}: invalid text length")
        if "pattern" in rule:
            require(re.fullmatch(rule["pattern"], value) is not None, f"{location}: invalid identifier")
    if type(value) is int:
        require(rule.get("minimum", value) <= value <= rule.get("maximum", value), f"{location}: out of range")
    for branch in rule.get("allOf", []):
        check_schema(value, branch, location)
    if "if" in rule:
        try:
            check_schema(value, rule["if"], location)
        except ValueError:
            branch = rule.get("else", {})
        else:
            branch = rule.get("then", {})
        check_schema(value, branch, location)


def validate(package):
    check_schema(package, SCHEMA)
    fields = {}
    for field in package["fields"]:
        require(field["key"] not in fields, "fields: duplicate key")
        fields[field["key"]] = field
    for index, step in enumerate(package["steps"]):
        for key in PLACEHOLDER.findall(step["text"]):
            require(key in fields, f"steps[{index}]: unknown template field")
            require(fields[key]["kind"] not in {"secret", "credential_ref"}, f"steps[{index}]: credentials cannot appear in text")
        require("{{" not in PLACEHOLDER.sub("", step["text"]), f"steps[{index}]: invalid template expression")
    return package


def load(path):
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "JSON: duplicate object key")
            result[key] = value
        return result

    return validate(json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_keys))


def preview(package, overrides):
    """Render a walkthrough; confirmations and elapsed time are explicitly simulated."""
    fields = {field["key"]: field for field in package["fields"]}
    values = {key: field.get("default", "") for key, field in fields.items()}
    for key, value in overrides.items():
        require(key in fields and fields[key]["kind"] in {"text", "number"}, "preview: only declared text/number inputs are allowed")
        values[key] = value
    for key, field in fields.items():
        require(field["kind"] in {"text", "number"}, "preview: credential fields require Agent configuration; not supported offline")
        require(len(values[key].encode("utf-8")) <= 2000, "preview: input too long")
        require(not field["required"] or values[key].strip(), f"preview: required input {key}")
        if field["kind"] == "number" and values[key]:
            require(re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", values[key]) is not None, f"preview: invalid number {key}")
            require(math.isfinite(float(values[key])), f"preview: number out of range {key}")
    lines = [f"OFFLINE SIMULATION · {package['id']}@{package['version']} · no audio or saved state"]
    for step in package["steps"]:
        lines.append(f"{step['kind']}: " + PLACEHOLDER.sub(lambda match: values[match[1]], step["text"]))
        if step["kind"] in {"confirm", "ask"}:
            lines.append("  [simulate user confirmation; continue]")
        elif step["kind"] == "timer":
            lines.append(f"  [simulate {step['seconds']} seconds elapsed; no real wait]")
    lines.append("[simulated completion]")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="JSON files; defaults to bundled capabilities")
    parser.add_argument("--preview", action="store_true", help="simulate one package's steps without executing")
    parser.add_argument("--value", action="append", default=[], metavar="KEY=TEXT", help="public text/number preview input; never pass credentials")
    args = parser.parse_args()
    paths = args.paths or sorted((ROOT / "capabilities").glob("*.json"))
    try:
        require(bool(paths), "no capability packages found")
        require(not args.preview or len(paths) == 1, "--preview requires exactly one package path")
        require(args.preview or not args.value, "--value requires --preview")
        overrides = {}
        for entry in args.value:
            key, separator, value = entry.partition("=")
            require(separator and key not in overrides, "--value requires unique KEY=TEXT entries")
            overrides[key] = value
        seen = set()
        for path in paths:
            package = load(path)
            require(package["id"] not in seen, f"{path.name}: duplicate package id")
            seen.add(package["id"])
            if args.preview:
                print(preview(package, overrides))
        print(f"Validated {len(seen)} declarative capability packages (offline)")
    except (ValueError, OSError) as error:
        print(f"Invalid package: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
