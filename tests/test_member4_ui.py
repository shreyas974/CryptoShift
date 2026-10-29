"""Member 4 console tests: adapter, escaping, badges, approval logic, allow-list, and AppTest smoke tests per page."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from cryptoshift.ui.console import components as C  # noqa: E402
from cryptoshift.ui.console import data as D  # noqa: E402

APP = str(ROOT / "src" / "cryptoshift" / "ui" / "console" / "app.py")
HOSTILE = "<script>alert(1)</script>"
TRAVERSAL = "../../etc/passwd"


class AdapterTests(unittest.TestCase):
    def test_missing_file_is_a_status_not_a_crash(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            l = D.load("plan", Path(d))
        self.assertEqual(l.status, "missing")
        self.assertIn("member3_pipeline", l.command)

    def test_schema_mismatch_reported(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / D.SPEC["plan"][0]
            p.parent.mkdir(parents=True)
            p.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
            l = D.load("plan", Path(d))
        self.assertEqual(l.status, "schema_mismatch")
        self.assertTrue(l.errors)

    def test_unknown_status_never_passes(self) -> None:
        for v in ("passed", "ok", "", None, "Green", "READY!"):
            self.assertEqual(D.norm_status(v), "UNKNOWN")
        self.assertEqual(C.badge_text("weird"), "? UNKNOWN")
        self.assertEqual(C.badge_text("verified"), "✔ VERIFIED")


class ComponentTests(unittest.TestCase):
    def test_escaped_text_caps_and_strips_control_chars(self) -> None:
        s = C.escaped_text("a\x1b[31mb" + "x" * 10_000)
        self.assertLessEqual(len(s), C.SNIPPET_MAX)
        self.assertNotIn("\x1b", s)

    def test_every_badge_has_text_and_icon(self) -> None:
        for status in C.BADGES:
            icon, _ = C.BADGES[status]
            self.assertTrue(icon)
            self.assertIn(status, C.badge_text(status))

    def test_approve_logic(self) -> None:
        h = "ab" * 32
        ready = {"state": "READY", "gates": [{"gate": "g", "status": "PASS"}]}
        self.assertEqual(C.can_approve(ready, "TEST-ONLY", h[:12], h), (True, "ok"))
        self.assertFalse(C.can_approve({"state": "PROPOSED", "gates": []}, "TEST-ONLY", h[:12], h)[0])
        self.assertFalse(C.can_approve({"state": "READY", "gates": [{"gate": "g", "status": "FAIL"}]}, "TEST-ONLY", h[:12], h)[0])
        self.assertFalse(C.can_approve({"state": "READY", "gates": [{"gate": "g", "status": "maybe"}]}, "TEST-ONLY", h[:12], h)[0])
        self.assertFalse(C.can_approve(ready, " ", h[:12], h)[0])
        self.assertFalse(C.can_approve(ready, "TEST-ONLY", h[:8], h)[0])
        self.assertFalse(C.can_approve(ready, "TEST-ONLY", "f" * 12, h)[0])

    def test_command_allow_list(self) -> None:
        with self.assertRaises(ValueError):
            C.run_allowed("rm -rf /")
        for argv in C.ALLOWED_COMMANDS.values():
            self.assertIsInstance(argv, list)
            self.assertTrue(argv[1].startswith("scripts/"))


class UiCodeChecks(unittest.TestCase):
    def test_no_env_file_access_and_no_unsafe_html(self) -> None:
        code = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "src" / "cryptoshift" / "ui" / "console").rglob("*.py"))
        self.assertIsNone(re.search(r"""["'][^"']*\.env["']|qcloud\.env|load_dotenv|dotenv_values""", code))
        self.assertNotIn("unsafe_allow_html=True", code)

    def test_server_binds_localhost_only(self) -> None:
        cfg = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
        self.assertIn('address = "127.0.0.1"', cfg)
        self.assertIn("127.0.0.1", (ROOT / "scripts" / "run_ui.ps1").read_text(encoding="utf-8"))


def _run_all_pages(testcase: unittest.TestCase, env: dict) -> list:
    from streamlit.testing.v1 import AppTest

    texts = []
    with mock.patch.dict(os.environ, env):
        at = AppTest.from_file(APP, default_timeout=120).run()
        testcase.assertFalse(at.exception, [e.value for e in at.exception])
        for page in at.sidebar.radio(key="page").options:
            at.sidebar.radio(key="page").set_value(page).run()
            testcase.assertFalse(at.exception, f"{page}: {[e.value for e in at.exception]}")
            texts.append((page, [m.value for m in at.markdown]))
    return texts


class AppSmokeTests(unittest.TestCase):
    def test_every_page_with_real_data(self) -> None:
        _run_all_pages(self, {"CRYPTOSHIFT_UI_DATA_DIR": str(ROOT)})

    def test_every_page_with_all_files_missing(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            _run_all_pages(self, {"CRYPTOSHIFT_UI_DATA_DIR": d})

    def test_hostile_strings_are_never_rendered_as_markup(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            dst = Path(d) / D.SPEC["plan"][0]
            dst.parent.mkdir(parents=True)
            plan = json.loads((ROOT / D.SPEC["plan"][0]).read_text(encoding="utf-8"))
            f = plan["findings"][0]
            f["snippet_redacted"], f["file_path"], f["rationale"] = HOSTILE + "y" * 10_000, TRAVERSAL, HOSTILE
            dst.write_text(json.dumps(plan), encoding="utf-8")
            pages = _run_all_pages(self, {"CRYPTOSHIFT_UI_DATA_DIR": d})
        for page, markdowns in pages:
            for m in markdowns:
                self.assertNotIn("<script>", m, page)


if __name__ == "__main__":
    unittest.main()
