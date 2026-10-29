"""Member 2 (v1.1) detector, attribution, relationship, redaction and export tests.

Fixture: tests/fixtures/multiservice_bank (SYNTHETIC). Hard negatives are asserted explicitly.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from cryptoshift.inventory import build_cbom_like, scan_inventory  # noqa: E402
from cryptoshift.inventory.common import redact_snippet  # noqa: E402
from cryptoshift.inventory.cyclonedx import to_cyclonedx, validate  # noqa: E402
from cryptoshift.inventory.haproxy import scan_haproxy_text  # noqa: E402
from cryptoshift.inventory.java_source import scan_java_source  # noqa: E402
from cryptoshift.inventory.python_ast import scan_python_source  # noqa: E402
from cryptoshift.inventory.relationships import extract_relationships  # noqa: E402
from cryptoshift.inventory.services import discover_services  # noqa: E402
from cryptoshift.inventory.shell_scripts import scan_shell_text  # noqa: E402
from cryptoshift.inventory.structured_config import scan_structured_text  # noqa: E402
from cryptoshift.inventory.tls_config import analyse_cipher_string, scan_tls_config_text  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "multiservice_bank"


def fams(hits):
    return {(h["line"], h["family"], h["purpose"]) for h in hits}


class AlgorithmConstantRule(unittest.TestCase):
    def test_constants_found(self) -> None:
        src = 'JWT_SIGNING_ALG = "RS256"\nKEY_WRAP_MODE = "RSA_OAEP"\nclass C:\n    BATCH_CIPHER = "TripleDES"\n'
        self.assertEqual(fams(scan_python_source(src)), {(1, "RSA", "digital_signature"), (2, "RSA", "key_establishment"),
                                                         (4, "3DES", "symmetric_encryption")})
        self.assertTrue(all(h["confidence"] == "low" for h in scan_python_source(src)))

    def test_hard_negatives(self) -> None:
        src = ('"""Uses RSA and SHA1."""\n'
               'TOKEN_ALG = "HS256"\n'               # HMAC
               'ERROR_ALG = "RS256 not supported"\n'  # free text
               'rsa_building_floor = "RS256"\n'      # not upper-case
               'TIMEOUT = "RS256"\n'                 # no algorithm keyword in the name
               'def f():\n    LOCAL_ALG = "RS256"\n'  # function-local
               '# JWT_ALG = "RS256"\n')               # comment
        self.assertEqual(scan_python_source(src), [])

    def test_pqc_constant_is_info_family(self) -> None:
        hits = scan_python_source('KEM_ALGORITHM = "X25519MLKEM768"\nSIGNATURE_ALGORITHM = "ML-DSA-65"\n')
        self.assertEqual({h["family"] for h in hits}, {"Hybrid-ML-KEM", "ML-DSA"})


class StructuredConfig(unittest.TestCase):
    def test_yaml_lines_lists_and_disabled_keys(self) -> None:
        hits = scan_structured_text((FIX / "services/ledger/application.yaml").read_text(), Path("application.yaml"))
        self.assertEqual(fams(hits), {(4, "RSA", "digital_signature"), (4, "SHA-1", "message_digest"),
                                      (10, "ECDH", "key_establishment"), (10, "Hybrid-ML-KEM", "key_establishment")})
        # [TLSv1.2, TLSv1.3] is a valid list (no finding); disabled-ciphers and the feature flag are hard negatives

    def test_properties_and_java_security(self) -> None:
        hits = scan_structured_text((FIX / "services/payments/application.properties").read_text(), Path("application.properties"))
        lines = {h["line"] for h in hits}
        self.assertEqual(lines, {3, 4, 10})  # 8 (commented), 9 (excluded-algorithms) are hard negatives
        jdk = [h for h in hits if h["line"] == 10][0]
        self.assertIn("TLSv1.1", jdk["reason"])

    def test_json(self) -> None:
        text = json.dumps({"tls": {"cipherSuites": ["TLS_RSA_WITH_AES_128_CBC_SHA"], "minVersion": "TLSv1.2"},
                           "jwt": {"signingAlgorithm": "PS256"}, "excludedAlgorithms": ["RS256"]}, indent=2)
        hits = scan_structured_text(text, Path("settings.json"))
        self.assertEqual({(h["family"], h["purpose"]) for h in hits}, {("RSA", "key_establishment"), ("RSA", "digital_signature")})


class HAProxy(unittest.TestCase):
    def test_haproxy(self) -> None:
        hits = scan_haproxy_text((FIX / "edge/haproxy.cfg").read_text(), FIX / "edge/haproxy.cfg")
        self.assertEqual({h["line"] for h in hits}, {3, 5, 6, 12, 17})  # 4 = TLS1.3 suites only, 13 = comment
        self.assertIn(("TLS-protocol", "transport_protocol"), {(h["family"], h["purpose"]) for h in hits if h["line"] == 5})


class ShellAndDockerfile(unittest.TestCase):
    def test_shell_commands_and_hard_negatives(self) -> None:
        hits = scan_shell_text((FIX / "scripts/rotate_keys.sh").read_text(), Path("rotate_keys.sh"))
        self.assertEqual({h["line"] for h in hits}, {4, 5, 6, 7, 8, 9})  # 10-13 are hard negatives
        self.assertEqual({h["family"] for h in hits if h["line"] == 7}, {"RSA"})

    def test_passphrase_and_paths_redacted(self) -> None:
        hits = scan_shell_text((FIX / "scripts/rotate_keys.sh").read_text(), Path("rotate_keys.sh"))
        blob = json.dumps(hits)
        self.assertNotIn("not-a-real-passphrase", blob)
        self.assertNotIn("/tmp/deploy_key", blob)

    def test_dockerfile(self) -> None:
        hits = scan_shell_text((FIX / "services/ledger/Dockerfile").read_text(), Path("Dockerfile"))
        self.assertEqual(fams(hits), {(5, "RSA", "digital_signature"), (5, "SHA-1", "message_digest")})


class JavaDetector(unittest.TestCase):
    def test_fixture(self) -> None:
        hits = scan_java_source((FIX / "services/ledger/java/src/LedgerCrypto.java").read_text())
        self.assertEqual({h["line"] for h in hits}, {13, 14, 15, 16, 17, 18, 22})  # 19-21, 23 are hard negatives
        const = [h for h in hits if h["line"] == 15][0]
        self.assertEqual(const["confidence"], "medium")
        self.assertIn("constant WRAP", const["reason"])

    def test_class_must_resolve_through_imports(self) -> None:
        src = 'class Cipher { static Cipher getInstance(String s){return null;} }\nclass A { void f(){ Cipher.getInstance("DES"); } }'
        self.assertEqual(scan_java_source(src), [])
        src2 = 'import javax.crypto.Cipher;\nclass A { void f(){ Cipher.getInstance("DES"); } }'
        self.assertEqual({h["family"] for h in scan_java_source(src2)}, {"DES"})

    def test_block_comment_and_text_block(self) -> None:
        src = 'import java.security.MessageDigest;\n/* MessageDigest.getInstance("MD5"); */\nclass A { String t = """\nMessageDigest.getInstance("SHA1")\n"""; }'
        self.assertEqual(scan_java_source(src), [])


class TlsConfigCalibration2Fixes(unittest.TestCase):
    def test_dhe_dss(self) -> None:
        self.assertIn("DSA", {d[0] for d in analyse_cipher_string("DHE-DSS-AES256-SHA")})
        self.assertIn("DSA", {d[0] for d in analyse_cipher_string("TLS_DHE_DSS_WITH_AES_128_CBC_SHA")})

    def test_apache_ecdhparameters(self) -> None:
        hits = scan_tls_config_text("SSLOpenSSLConfCmd ECDHParameters X25519\n", Path("ssl.conf"))
        self.assertEqual(fams(hits), {(1, "ECDH", "key_establishment")})


class ServiceAttribution(unittest.TestCase):
    def setUp(self) -> None:
        self.cat = discover_services(FIX)

    def test_rules(self) -> None:
        a = self.cat.attribute
        self.assertEqual((a("gateway/nginx.conf").service_id, a("gateway/nginx.conf").rule), ("gateway", "compose"))
        self.assertEqual((a("services/ledger/ledger/client.py").service_id, a("services/ledger/ledger/client.py").rule), ("ledger", "compose"))
        self.assertEqual(a("services/payments/application.properties").rule, "declared")
        self.assertEqual(a("scripts/rotate_keys.sh").service_id, "unknown")
        self.assertEqual(a("scripts/rotate_keys.sh").confidence, "none")

    def test_folder_and_file_name_rules(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "svc" / "billing").mkdir(parents=True)
            (root / "svc" / "billing" / "pom.xml").write_text("<project/>")
            (root / "svc" / "billing" / "Main.java").write_text("class Main {}")
            (root / "payments_tls.conf").write_text("ssl_protocols TLSv1.2;\n")
            (root / "nginx.conf").write_text("ssl_protocols TLSv1.2;\n")
            cat = discover_services(root)
            self.assertEqual((cat.attribute("svc/billing/Main.java").service_id, cat.attribute("svc/billing/Main.java").rule), ("billing", "folder"))
            self.assertEqual((cat.attribute("payments_tls.conf").service_id, cat.attribute("payments_tls.conf").confidence), ("payments_tls", "low"))
            self.assertEqual(cat.attribute("nginx.conf").service_id, "unknown")  # generic name is never a service

    def test_every_finding_has_basis(self) -> None:
        findings, _ = scan_inventory(FIX)
        self.assertTrue(findings)
        for f in findings:
            self.assertTrue(f.service_id_basis)
            self.assertIn(f.service_id_confidence, ("high", "medium", "low", "none"))
            if f.service_id == "unknown":
                self.assertEqual(f.service_id_confidence, "none")


class Relationships(unittest.TestCase):
    def test_observed_edges_and_unknowns(self) -> None:
        r = extract_relationships(FIX)
        edges = {(e["source"], e["target"], e["kind"]) for e in r["edges"]}
        self.assertEqual(edges, {
            ("gateway", "payments", "compose_depends_on"), ("gateway", "ledger", "compose_depends_on"),
            ("edge", "gateway", "compose_links"), ("payments", "ledger", "compose_depends_on"),
            ("edge", "gateway", "haproxy_server"), ("gateway", "payments", "nginx_upstream"),
            ("gateway", "ledger", "nginx_proxy_pass"), ("payments", "ledger", "config_url"),
            ("payments", "ledger", "python_import")})
        self.assertTrue(all(e["provenance"] == "OBSERVED" and e["file"] and e["line"] > 0 for e in r["edges"]))
        refs = {u["reference"] for u in r["unknown_references"]}
        self.assertEqual(refs, {"10.20.30.40", "fraud-scoring.partner.example"})
        self.assertNotIn("127.0.0.1", json.dumps(r))  # loopback ignored

    def test_no_invented_edges_without_known_target(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "alpha.yaml"
            p.write_text("service_id: alpha\nupstream_url: https://beta.internal:8443\n")
            r = extract_relationships(Path(d))
            self.assertEqual(r["edges"], [])
            self.assertEqual([u["reference"] for u in r["unknown_references"]], ["beta.internal"])


class RedactionAndSafety(unittest.TestCase):
    def test_redact_snippet(self) -> None:
        marker = "-----" + "BEGIN " + "PRIVATE KEY" + "-----"
        self.assertEqual(redact_snippet(marker), "[REDACTED: key/certificate material]")
        self.assertNotIn("hunter2", redact_snippet('db_password = "hunter2"'))
        token = "A" * 20 + "b9" * 10
        self.assertNotIn(token, redact_snippet(f"x = {token}"))
        self.assertIn("TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256", redact_snippet("TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256"))

    def test_sensitive_files_never_opened(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / ".env").write_text("SECRET_ALG=RS256\n")
            (root / "svc.key").write_text("not really a key\n")
            (root / "app.yaml").write_text("jwt:\n  algorithm: RS256\n")
            findings, stats = scan_inventory(root)
            self.assertEqual(stats["skipped_sensitive"], 2)
            self.assertEqual({f.file_path for f in findings}, {"app.yaml"})

    def test_inventory_output_has_no_secret_values(self) -> None:
        findings, stats = scan_inventory(FIX)
        cbom = build_cbom_like(findings, stats, "multiservice_bank", relationships=extract_relationships(FIX))
        blob = json.dumps(cbom)
        for bad in ("not-a-real-passphrase", "PRIVATE KEY", ":\\Users\\", "/home/"):
            self.assertNotIn(bad, blob)


class CycloneDxSubset(unittest.TestCase):
    def test_structure_and_optional_schema_validation(self) -> None:
        findings, stats = scan_inventory(FIX)
        cbom = build_cbom_like(findings, stats, "multiservice_bank", relationships=extract_relationships(FIX))
        doc = to_cyclonedx(cbom)
        self.assertEqual((doc["bomFormat"], doc["specVersion"]), ("CycloneDX", "1.6"))
        self.assertTrue(any(c["type"] == "cryptographic-asset" for c in doc["components"]))
        schema = ROOT / "scratch" / "derived" / "cyclonedx-schema"
        if not (schema / "bom-1.6.schema.json").is_file():
            self.skipTest("CycloneDX schema not fetched (scripts/fetch_cyclonedx_schema.py)")
        self.assertEqual(validate(doc, schema), [])


class OutputSchemas(unittest.TestCase):
    def test_live_output_matches_schemas(self) -> None:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource

        rel_schema = json.loads((ROOT / "schemas" / "relationships.schema.json").read_text(encoding="utf-8"))
        inv_schema = json.loads((ROOT / "schemas" / "inventory-cbom-like-1.1.schema.json").read_text(encoding="utf-8"))
        reg = Registry().with_resource(rel_schema["$id"], Resource.from_contents(rel_schema))
        findings, stats = scan_inventory(FIX)
        rels = extract_relationships(FIX, catalog=stats["_catalog"])
        cbom = build_cbom_like(findings, stats, "multiservice_bank", relationships=rels)
        for schema, doc in ((rel_schema, rels), (inv_schema, cbom)):
            errors = [e.message for e in Draft202012Validator(schema, registry=reg).iter_errors(doc)]
            self.assertEqual(errors, [])


class LegacyScanConsole(unittest.TestCase):
    def test_scan_prints_no_absolute_paths(self) -> None:
        target = str((ROOT / "data" / "fixtures" / "synthetic").resolve())
        out = subprocess.run([sys.executable, str(ROOT / "cryptoshift_cli.py"), "scan", "--path", target],
                             capture_output=True, text=True, cwd=ROOT, timeout=120).stdout
        self.assertIn("data/fixtures/synthetic/", out.replace("\\", "/"))
        self.assertNotIn(str(ROOT), out)


if __name__ == "__main__":
    unittest.main()
