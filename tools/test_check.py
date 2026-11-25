"""Regression checks for the package trust boundary and offline walkthrough."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools import check


class PackageChecks(unittest.TestCase):
    def setUp(self):
        self.package = check.load(check.ROOT / "capabilities/tea-guide.json")

    def test_bundled_packages_and_walkthrough(self):
        for path in sorted((check.ROOT / "capabilities").glob("*.json")):
            package = check.load(path)
            text = check.preview(package, {"content": "查看清单"} if package["id"] == "check-reminder" else {})
            self.assertNotIn("{{", text)
            self.assertIn("[simulated completion]", text)
        text = check.preview(self.package, {"tea": "示例茶"})
        self.assertLess(text.index("simulate user confirmation"), text.index("simulate 180 seconds"))
        self.assertIn("示例茶准备好了", text)

    def test_invalid_manifests(self):
        invalid = []
        for key, value in [("id", "Bad ID"), ("version", ""), ("fields", None), ("steps", []), ("permissions", ["network"]), ("name", "茶" * 41)]:
            package = copy.deepcopy(self.package)
            package[key] = value
            invalid.append(package)
        package = copy.deepcopy(self.package)
        del package["version"]
        invalid.append(package)
        package = copy.deepcopy(self.package)
        package["fields"].append(package["fields"][0].copy())
        invalid.append(package)
        for field in [dict(kind="shell"), dict(required="true"), dict(default=42), dict(kind="secret", default="example"), dict(kind="credential_ref", default="example")]:
            package = copy.deepcopy(self.package)
            package["fields"][0].update(field)
            invalid.append(package)
        for step in [dict(kind="http", text="x"), dict(kind="say", text="x", seconds=1), dict(kind="say", text="{{missing}}"), dict(kind="say", text="{{tea + 1}}"), dict(kind="say", text=""), dict(kind="timer", text="x"), dict(kind="timer", text="x", seconds=0), dict(kind="timer", text="x", seconds=604801), dict(kind="timer", text="x", seconds=True), dict(kind="timer", text="x", seconds=1.5), dict(kind="say", text="x", command="echo x")]:
            package = copy.deepcopy(self.package)
            package["steps"] = [step]
            invalid.append(package)
        for kind in ["secret", "credential_ref"]:
            package = copy.deepcopy(self.package)
            package["fields"][0].update(kind=kind, default="")
            invalid.append(package)
        for package in invalid:
            with self.subTest(package=package), self.assertRaises(ValueError):
                check.validate(package)

    def test_limits_and_credentials(self):
        self.package["steps"] = [{"kind": "timer", "text": "x", "seconds": 604800}]
        check.validate(self.package)
        self.package["fields"][0].update(kind="secret", default="")
        check.validate(self.package)  # Managed field definitions are valid, but never rendered offline.
        with self.assertRaises(ValueError):
            check.preview(self.package, {})
        with self.assertRaises(ValueError):
            check.preview(self.package, {"tea": "example"})

    def test_preview_input_validation(self):
        package = check.load(check.ROOT / "capabilities/check-reminder.json")
        for inputs in [{}, {"content": " "}, {"unknown": "x"}]:
            with self.assertRaises(ValueError):
                check.preview(package, inputs)
        self.package["fields"][0].update(kind="number", default="1")
        check.preview(self.package, {"tea": "-1.5e2"})
        for value in ["NaN", "Infinity", "true", "01", "1e999"]:
            with self.assertRaises(ValueError):
                check.preview(self.package, {"tea": value})

    def test_duplicate_json_keys_and_cli_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text('{"id":"x","id":"y"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                check.load(path)
            result = subprocess.run([sys.executable, str(check.ROOT / "tools/check.py"), str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("duplicate object key", result.stderr)
            path.write_text(json.dumps(self.package), encoding="utf-8")
            result = subprocess.run([sys.executable, str(check.ROOT / "tools/check.py"), str(path), str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("duplicate package id", result.stderr)


if __name__ == "__main__":
    unittest.main()
