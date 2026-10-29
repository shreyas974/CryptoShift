"""Focused tests for the Stage 1 inventory detectors: parsing, line numbers, redaction, ambiguity, safety."""

from __future__ import annotations

import json
import sys
import tempfile
import textwrap
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cryptoshift.inventory import build_cbom_like, scan_inventory  # noqa: E402
from cryptoshift.inventory.common import redact_snippet  # noqa: E402
from cryptoshift.inventory.manifests import scan_package_json, scan_pom, scan_requirements  # noqa: E402
from cryptoshift.inventory.python_ast import scan_python_source  # noqa: E402
from cryptoshift.inventory.tls_config import analyse_cipher_string, scan_tls_config_text  # noqa: E402
from cryptoshift.models import CryptoFinding  # noqa: E402

PY_SAMPLE = textwrap.dedent('''\
    """Module docstring mentioning RSA, ECDSA and hashlib.sha1 must not be flagged."""
    import hashlib
    import jwt
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa, padding as pad, ec
    from Cryptodome.Cipher import DES3

    # rsa.generate_private_key(...) in a comment is ignored

    def generate_rsa_report(md5_total):
        return "rsa" + str(md5_total)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ct = key.public_key().encrypt(b"k", pad.OAEP(mgf=pad.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    sig = key.sign(b"m", pad.PKCS1v15(), hashes.SHA256())
    sig2 = ec.generate_private_key(ec.SECP256R1()).sign(b"m", ec.ECDSA(hashes.SHA256()))
    d = hashlib.new("sha1", b"x")
    tok = jwt.encode({"a": 1}, "k", algorithm="RS256")
    mac = jwt.encode({"a": 1}, "k", algorithm="HS256")
    c = DES3.new(b"0" * 24, DES3.MODE_ECB)
''')


class PythonAstDetectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.hits = scan_python_source(PY_SAMPLE)
        self.by_line = {}
        for h in self.hits:
            self.by_line.setdefault(h["line"], []).append(h)

    def test_comments_docstrings_and_lookalikes_ignored(self) -> None:
        self.assertNotIn(1, self.by_line)   # docstring
        self.assertNotIn(8, self.by_line)   # comment
        self.assertNotIn(10, self.by_line)  # def generate_rsa_report
        self.assertNotIn(11, self.by_line)  # "rsa" string literal
        self.assertNotIn(19, self.by_line)  # HS256 is a symmetric MAC, not flagged

    def test_keygen_is_ambiguous_with_exact_line(self) -> None:
        h = self.by_line[13][0]
        self.assertEqual((h["family"], h["purpose"], h["ambiguity"]), ("RSA", "unknown", "ambiguous"))

    def test_purpose_from_api(self) -> None:
        self.assertIn(("RSA", "key_establishment"), {(h["family"], h["purpose"]) for h in self.by_line[14]})
        self.assertIn(("RSA", "digital_signature"), {(h["family"], h["purpose"]) for h in self.by_line[15]})  # PKCS1v15 in .sign()
        self.assertIn(("ECDSA", "digital_signature"), {(h["family"], h["purpose"]) for h in self.by_line[16]})
        self.assertEqual(self.by_line[17][0]["family"], "SHA-1")
        self.assertEqual((self.by_line[18][0]["family"], self.by_line[18][0]["purpose"]), ("RSA", "digital_signature"))
        self.assertEqual(self.by_line[20][0]["family"], "3DES")  # Cryptodome normalised to Crypto
        self.assertEqual(self.by_line[20][0]["detected_value"], "Crypto.Cipher.DES3.new")

    def test_unparsable_python_raises_syntax_error(self) -> None:
        with self.assertRaises(SyntaxError):
            scan_python_source("def broken(:\n")


class TlsConfigDetectorTests(unittest.TestCase):
    NGINX = textwrap.dedent('''\
        server {
            # ssl_protocols TLSv1;   (commented out, ignored)
            ssl_protocols TLSv1 TLSv1.2;
            ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:DES-CBC3-SHA;
            ssl_ecdh_curve X25519MLKEM768:prime256v1;
            ssl_certificate certs/server.crt;
        }
    ''')

    def test_nginx_directives_lines_and_hybrid(self) -> None:
        hits = scan_tls_config_text(self.NGINX, Path("site.conf"))
        got = {(h["line"], h["family"], h["purpose"]) for h in hits}
        self.assertIn((3, "TLS-protocol", "transport_protocol"), got)
        self.assertIn((4, "ECDH", "key_establishment"), got)
        self.assertIn((4, "ECDSA", "digital_signature"), got)
        self.assertIn((4, "RSA", "key_establishment"), got)  # DES-CBC3-SHA is static-RSA key transport
        self.assertIn((4, "3DES", "symmetric_encryption"), got)
        self.assertIn((5, "ECDH", "key_establishment"), got)
        self.assertIn((5, "Hybrid-ML-KEM", "key_establishment"), got)
        cert = [h for h in hits if h["line"] == 6][0]
        self.assertEqual(cert["family"], "X.509-unknown-key")  # file not present -> unknown key
        self.assertFalse(any(h["line"] == 2 for h in hits))

    def test_apache_protocol_all_minus(self) -> None:
        hits = scan_tls_config_text("SSLProtocol all -SSLv3\nSSLCipherSuite HIGH:!aNULL\n", Path("ssl.conf"))
        self.assertEqual(hits[0]["family"], "TLS-protocol")
        self.assertIn("TLSv1", hits[0]["reason"])
        self.assertEqual((hits[1]["family"], hits[1]["ambiguity"]), ("TLS-cipher-policy", "ambiguous"))

    def test_openssl_cnf(self) -> None:
        text = "[system_default_sect]\nMinProtocol = TLSv1\nCipherString = DEFAULT@SECLEVEL=2\n[req]\ndefault_md = sha1\n"
        hits = scan_tls_config_text(text, Path("openssl.cnf"))
        self.assertEqual([(h["line"], h["family"]) for h in hits], [(2, "TLS-protocol"), (3, "TLS-cipher-policy"), (5, "SHA-1")])

    def test_tls13_only_cipher_string_has_no_findings(self) -> None:
        self.assertEqual(analyse_cipher_string("TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256"), [])


class ManifestDetectorTests(unittest.TestCase):
    def test_requirements(self) -> None:
        hits = scan_requirements("# crypto\nrequests==2.0\nPyCryptodome==3.20.0  # pinned\n-r other.txt\nPyJWT[crypto]>=2\n")
        self.assertEqual([(h["line"], h["family"], h["ambiguity"]) for h in hits],
                         [(3, "crypto-library", "unknown"), (5, "JWT", "unknown")])

    def test_package_json_and_pom_lines(self) -> None:
        pj = '{\n  "dependencies": {\n    "express": "4",\n    "jsonwebtoken": "^9.0.0"\n  }\n}\n'
        self.assertEqual(scan_package_json(pj)[0]["line"], 4)
        pom = ('<project xmlns="http://maven.apache.org/POM/4.0.0">\n<dependencies>\n<dependency>\n'
               '<groupId>org.bouncycastle</groupId>\n<artifactId>bcprov-jdk18on</artifactId>\n'
               '<version>1.78</version>\n</dependency>\n</dependencies>\n</project>\n')
        h = scan_pom(pom)[0]
        self.assertEqual((h["line"], h["detected_value"]), (5, "org.bouncycastle:bcprov-jdk18on:1.78"))
        self.assertEqual(scan_pom('<!DOCTYPE x [<!ENTITY a "b">]><project/>'), [])


class RedactionAndSafetyTests(unittest.TestCase):
    def test_redact_snippet(self) -> None:
        s = redact_snippet('password = "not-a-real-secret"; blob="' + "A" * 40 + '" C:\\Users\\alice\\x')
        self.assertNotIn("not-a-real-secret", s)
        self.assertNotIn("A" * 40, s)
        self.assertNotIn("alice", s)
        pem_marker = "-----BEGIN " + "PRIVATE KEY-----"  # built at runtime so the repo secret scan stays strict
        self.assertEqual(redact_snippet(pem_marker), "[REDACTED: key/certificate material]")
        self.assertLessEqual(len(redact_snippet("x" * 500)), 160)

    def test_scan_skips_sensitive_files_and_reports_cert_metadata_only(self) -> None:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID

        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / ".env").write_text("MARKER=should-never-be-read\n", encoding="utf-8")
            (d / "qcloud.env").write_text("X=1\n", encoding="utf-8")
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "unit-test.invalid")])
            now = datetime.now(timezone.utc)
            cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
                    .serial_number(1).not_valid_before(now).not_valid_after(now + timedelta(days=30))
                    .sign(key, hashes.SHA256()))
            (d / "server.crt").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
            (d / "server_key.pem").write_bytes(key.private_bytes(
                serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
            (d / "app").mkdir()
            (d / "app" / "nginx.conf").write_text("ssl_certificate ../server.crt;\n", encoding="utf-8")
            (d / "tests").mkdir()
            (d / "tests" / "test_x.py").write_text("import hashlib\nhashlib.md5(b'')\n", encoding="utf-8")

            findings, stats = scan_inventory(d)
            self.assertEqual(stats["skipped_sensitive"], 2)
            self.assertFalse(any(f.file_path.endswith(".env") for f in findings))
            dump = json.dumps(build_cbom_like(findings, stats, "tmp"))
            self.assertNotIn("BEGIN", dump)
            self.assertNotIn("unit-test.invalid", dump)  # subject never emitted
            self.assertNotIn("should-never-be-read", dump)

            crt = [f for f in findings if f.file_path == "server.crt"][0]
            self.assertEqual((crt.algorithm_family, crt.legacy_algorithm, crt.operation_purpose), ("RSA", "RSA-2048", "digital_signature"))
            self.assertIn("ML-DSA", crt.target_pqc_algorithm)
            pk = [f for f in findings if f.file_path == "server_key.pem"][0]
            self.assertEqual((pk.operation_purpose, pk.ambiguity), ("unknown", "unknown"))
            self.assertIn("HOLD", pk.target_pqc_algorithm)
            ngx = [f for f in findings if f.file_path == "app/nginx.conf"][0]
            self.assertIn("RSA-2048", ngx.rationale)  # certificate referenced by directive was inspected
            md5 = [f for f in findings if f.file_path == "tests/test_x.py"][0]
            self.assertTrue(md5.in_test_file)
            self.assertEqual(md5.line_number, 2)

    def test_cryptofinding_backward_compatible(self) -> None:
        f = CryptoFinding("id", "svc", "a.py", 1, "RSA-2048", "t", "x", "s", "HIGH")
        self.assertEqual((f.detector, f.ambiguity, f.in_test_file), ("legacy", "none", False))


if __name__ == "__main__":
    unittest.main()
