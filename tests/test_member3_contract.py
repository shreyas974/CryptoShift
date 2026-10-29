"""Contract tests: committed Member 3 report and example files validate against schemas/member3."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas" / "member3"

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None


@unittest.skipIf(jsonschema is None, "jsonschema not installed (requirements-member3.txt)")
class ContractTests(unittest.TestCase):
    def _schema(self, name: str) -> dict:
        return json.loads((SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8"))

    def test_examples_validate(self) -> None:
        for name in ("plan", "gate_results", "rollback_record", "agent_api"):
            ex = json.loads((SCHEMAS / "examples" / f"{name}.example.json").read_text(encoding="utf-8"))
            jsonschema.validate(ex, self._schema(name))

    def test_committed_plan_report_validates_and_has_no_local_paths(self) -> None:
        text = (ROOT / "reports" / "member3" / "plan.json").read_text(encoding="utf-8")
        jsonschema.validate(json.loads(text), self._schema("plan"))
        self.assertNotRegex(text, r"[A-Za-z]:[\\/]+Users[\\/]")
        plan = json.loads(text)
        self.assertTrue(all(s["state"] != "APPROVED" for s in plan["steps"]))  # nothing approved by software


if __name__ == "__main__":
    unittest.main()
