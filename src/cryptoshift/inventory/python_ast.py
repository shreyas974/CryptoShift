"""Python AST detector: cryptography, hashlib, ssl, PyCryptodome and JWT-style libraries.

Only names that resolve through real imports are matched, so comments, docstrings, local variables named
`rsa`, or functions like `generate_rsa_report` are not reported. String literals are inspected only where
they configure an algorithm (`hashlib.new("sha1")`, `jwt.encode(..., algorithm="RS256")`, `set_ciphers(...)`).
"""

from __future__ import annotations

import ast
from typing import Any, Dict, List, Optional, Tuple

from cryptoshift.inventory.algorithm_ids import classify_identifier
from cryptoshift.inventory.tls_config import analyse_cipher_string

VERSION = "python_ast/1.1 (adds scoped algorithm-constant rule)"
ALGORITHM_NAME_KEYWORDS = {"ALG", "ALGO", "ALGORITHM", "ALGORITHMS", "CIPHER", "SCHEME", "KEX", "KEM", "SIGNING",
                           "SIGNATURE", "SIG", "WRAP", "WRAPPING", "HASH", "DIGEST", "CURVE", "GROUP", "PADDING", "JWS", "JWE"}
_CRYPTO = "cryptography.hazmat.primitives"
_ASYM = f"{_CRYPTO}.asymmetric"

# qualified name -> (family, purpose, ambiguity, confidence, reason)
API_RULES: Dict[str, Tuple[str, str, str, str, str]] = {
    f"{_ASYM}.rsa.generate_private_key": ("RSA", "unknown", "ambiguous", "high", "RSA key generation; signing vs key transport not determined at this call"),
    f"{_ASYM}.rsa.RSAPublicNumbers": ("RSA", "unknown", "ambiguous", "medium", "RSA public key construction; purpose not determined here"),
    f"{_ASYM}.rsa.RSAPrivateNumbers": ("RSA", "unknown", "ambiguous", "medium", "RSA private key construction; purpose not determined here"),
    f"{_ASYM}.padding.OAEP": ("RSA", "key_establishment", "none", "high", "RSA-OAEP padding is used for RSA encryption / key transport"),
    f"{_ASYM}.padding.PSS": ("RSA", "digital_signature", "none", "high", "RSA-PSS padding is used for RSA signatures"),
    f"{_ASYM}.padding.PKCS1v15": ("RSA", "unknown", "ambiguous", "medium", "PKCS#1 v1.5 padding is used for both RSA signatures and RSA encryption"),
    f"{_ASYM}.ec.generate_private_key": ("EC", "unknown", "ambiguous", "high", "EC key generation; ECDSA vs ECDH not determined at this call"),
    f"{_ASYM}.ec.derive_private_key": ("EC", "unknown", "ambiguous", "medium", "EC private key derivation; purpose not determined here"),
    f"{_ASYM}.ec.EllipticCurvePublicKey.from_encoded_point": ("EC", "unknown", "ambiguous", "medium", "EC public key decoding; purpose not determined here"),
    f"{_ASYM}.ec.EllipticCurvePublicNumbers": ("EC", "unknown", "ambiguous", "medium", "EC public key construction; purpose not determined here"),
    f"{_ASYM}.ec.EllipticCurvePrivateNumbers": ("EC", "unknown", "ambiguous", "medium", "EC private key construction; purpose not determined here"),
    f"{_ASYM}.rsa.rsa_recover_prime_factors": ("RSA", "unknown", "ambiguous", "medium", "RSA private key reconstruction"),
    f"{_ASYM}.rsa.rsa_crt_dmp1": ("RSA", "unknown", "ambiguous", "medium", "RSA CRT parameter computation"),
    f"{_ASYM}.rsa.rsa_crt_dmq1": ("RSA", "unknown", "ambiguous", "medium", "RSA CRT parameter computation"),
    f"{_ASYM}.rsa.rsa_crt_iqmp": ("RSA", "unknown", "ambiguous", "medium", "RSA CRT parameter computation"),
    **{f"{_ASYM}.ec.{c}": ("EC", "unknown", "ambiguous", "medium", f"elliptic curve {c} selected; ECDSA vs ECDH not determined here")
       for c in ("SECP192R1", "SECP224R1", "SECP256R1", "SECP384R1", "SECP521R1", "SECP256K1",
                 "BrainpoolP256R1", "BrainpoolP384R1", "BrainpoolP512R1")},
    f"{_ASYM}.ec.ECDSA": ("ECDSA", "digital_signature", "none", "high", "ECDSA signature algorithm object"),
    f"{_ASYM}.ec.ECDH": ("ECDH", "key_establishment", "none", "high", "ECDH key agreement"),
    f"{_ASYM}.dh.generate_parameters": ("DH", "key_establishment", "none", "high", "Finite-field Diffie-Hellman parameters"),
    f"{_ASYM}.dh.DHParameterNumbers": ("DH", "key_establishment", "none", "medium", "Finite-field Diffie-Hellman parameters"),
    f"{_ASYM}.dsa.generate_private_key": ("DSA", "digital_signature", "none", "high", "DSA key generation (signature-only algorithm)"),
    f"{_ASYM}.dsa.DSAPublicNumbers": ("DSA", "digital_signature", "none", "medium", "DSA public key (signature-only algorithm)"),
    f"{_ASYM}.x25519.X25519PrivateKey": ("X25519", "key_establishment", "none", "high", "X25519 key agreement"),
    f"{_ASYM}.x25519.X25519PublicKey": ("X25519", "key_establishment", "none", "high", "X25519 key agreement"),
    f"{_ASYM}.x448.X448PrivateKey": ("X448", "key_establishment", "none", "high", "X448 key agreement"),
    f"{_ASYM}.x448.X448PublicKey": ("X448", "key_establishment", "none", "high", "X448 key agreement"),
    f"{_ASYM}.ed25519.Ed25519PrivateKey": ("Ed25519", "digital_signature", "none", "high", "Ed25519 signatures"),
    f"{_ASYM}.ed25519.Ed25519PublicKey": ("Ed25519", "digital_signature", "none", "high", "Ed25519 signatures"),
    f"{_ASYM}.ed448.Ed448PrivateKey": ("Ed448", "digital_signature", "none", "high", "Ed448 signatures"),
    f"{_ASYM}.ed448.Ed448PublicKey": ("Ed448", "digital_signature", "none", "high", "Ed448 signatures"),
    f"{_CRYPTO}.ciphers.algorithms.TripleDES": ("3DES", "symmetric_encryption", "none", "high", "Triple-DES block cipher"),
    "cryptography.hazmat.decrepit.ciphers.algorithms.TripleDES": ("3DES", "symmetric_encryption", "none", "high", "Triple-DES block cipher"),
    f"{_CRYPTO}.ciphers.algorithms.ARC4": ("RC4", "symmetric_encryption", "none", "high", "RC4 stream cipher"),
    "cryptography.hazmat.decrepit.ciphers.algorithms.ARC4": ("RC4", "symmetric_encryption", "none", "high", "RC4 stream cipher"),
    f"{_CRYPTO}.ciphers.algorithms.Blowfish": ("Blowfish", "symmetric_encryption", "none", "high", "64-bit block cipher"),
    f"{_CRYPTO}.hashes.SHA1": ("SHA-1", "message_digest", "none", "high", "SHA-1 hash"),
    f"{_CRYPTO}.hashes.MD5": ("MD5", "message_digest", "none", "high", "MD5 hash"),
    "hashlib.sha1": ("SHA-1", "message_digest", "none", "high", "SHA-1 hash"),
    "hashlib.md5": ("MD5", "message_digest", "none", "high", "MD5 hash"),
    "ssl.PROTOCOL_SSLv2": ("TLS-protocol", "transport_protocol", "none", "high", "SSLv2 protocol constant"),
    "ssl.PROTOCOL_SSLv3": ("TLS-protocol", "transport_protocol", "none", "high", "SSLv3 protocol constant"),
    "ssl.PROTOCOL_TLSv1": ("TLS-protocol", "transport_protocol", "none", "high", "TLS 1.0 protocol constant"),
    "ssl.PROTOCOL_TLSv1_1": ("TLS-protocol", "transport_protocol", "none", "high", "TLS 1.1 protocol constant"),
    "ssl.TLSVersion.TLSv1": ("TLS-protocol", "transport_protocol", "none", "high", "TLS 1.0 version constant"),
    "ssl.TLSVersion.TLSv1_1": ("TLS-protocol", "transport_protocol", "none", "high", "TLS 1.1 version constant"),
    # PyCryptodome / PyCrypto (`Cryptodome.` is normalised to `Crypto.`)
    "Crypto.PublicKey.RSA.generate": ("RSA", "unknown", "ambiguous", "high", "RSA key generation; purpose not determined at this call"),
    "Crypto.PublicKey.RSA.construct": ("RSA", "unknown", "ambiguous", "medium", "RSA key construction; purpose not determined here"),
    "Crypto.PublicKey.RSA.import_key": ("RSA", "unknown", "ambiguous", "medium", "RSA key import; purpose not determined here"),
    "Crypto.PublicKey.RSA.importKey": ("RSA", "unknown", "ambiguous", "medium", "RSA key import; purpose not determined here"),
    "Crypto.PublicKey.ECC.generate": ("EC", "unknown", "ambiguous", "high", "EC key generation; purpose not determined at this call"),
    "Crypto.PublicKey.ECC.import_key": ("EC", "unknown", "ambiguous", "medium", "EC key import; purpose not determined here"),
    "Crypto.PublicKey.DSA.generate": ("DSA", "digital_signature", "none", "high", "DSA key generation (signature-only algorithm)"),
    "Crypto.Cipher.PKCS1_OAEP.new": ("RSA", "key_establishment", "none", "high", "RSA-OAEP encryption / key transport"),
    "Crypto.Cipher.PKCS1_v1_5.new": ("RSA", "key_establishment", "none", "high", "RSA PKCS#1 v1.5 encryption / key transport"),
    "Crypto.Signature.pkcs1_15.new": ("RSA", "digital_signature", "none", "high", "RSA PKCS#1 v1.5 signature"),
    "Crypto.Signature.PKCS1_v1_5.new": ("RSA", "digital_signature", "none", "high", "RSA PKCS#1 v1.5 signature"),
    "Crypto.Signature.pss.new": ("RSA", "digital_signature", "none", "high", "RSA-PSS signature"),
    "Crypto.Signature.PKCS1_PSS.new": ("RSA", "digital_signature", "none", "high", "RSA-PSS signature"),
    "Crypto.Signature.DSS.new": ("ECDSA/DSA", "digital_signature", "none", "high", "DSS (ECDSA or DSA) signature"),
    "Crypto.Signature.eddsa.new": ("EdDSA", "digital_signature", "none", "high", "EdDSA signature"),
    "Crypto.Cipher.DES3.new": ("3DES", "symmetric_encryption", "none", "high", "Triple-DES block cipher"),
    "Crypto.Cipher.DES.new": ("DES", "symmetric_encryption", "none", "high", "Single DES block cipher"),
    "Crypto.Cipher.ARC4.new": ("RC4", "symmetric_encryption", "none", "high", "RC4 stream cipher"),
    "Crypto.Cipher.Blowfish.new": ("Blowfish", "symmetric_encryption", "none", "high", "64-bit block cipher"),
    "Crypto.Hash.SHA1.new": ("SHA-1", "message_digest", "none", "high", "SHA-1 hash"),
    "Crypto.Hash.SHA.new": ("SHA-1", "message_digest", "none", "high", "SHA-1 hash"),
    "Crypto.Hash.MD5.new": ("MD5", "message_digest", "none", "high", "MD5 hash"),
}

# Ambiguous padding -> purpose resolved by the enclosing call's method name
CONTEXT_PURPOSE = {"sign": "digital_signature", "verify": "digital_signature",
                   "encrypt": "key_establishment", "decrypt": "key_establishment"}

JWT_ENCODE_FUNCS = {"jwt.encode", "jose.jwt.encode", "jose.jws.sign", "jwt.api_jwt.encode", "jwt.api_jws.encode"}
JWT_DECODE_FUNCS = {"jwt.decode", "jose.jwt.decode", "jose.jws.verify", "jwt.api_jwt.decode", "jwt.api_jws.decode"}


def jwt_alg_family(alg: str) -> Optional[str]:
    """Map a JWS `alg` value to an asymmetric family; HMAC (`HS*`) and `none` return None."""
    a = alg.upper()
    if a.startswith(("RS", "PS")):
        return "RSA"
    if a.startswith("ES"):
        return "ECDSA"
    if a in ("EDDSA", "ED25519", "ED448"):
        return "EdDSA"
    return None


def _normalise(qual: str) -> str:
    return "Crypto." + qual[len("Cryptodome."):] if qual.startswith("Cryptodome.") else qual


def _match_rule(qual: str) -> Optional[Tuple[str, Tuple[str, str, str, str, str]]]:
    qual = _normalise(qual)
    if qual in API_RULES:
        return qual, API_RULES[qual]
    # Class references followed by a method, e.g. X25519PrivateKey.generate
    parts = qual.split(".")
    for cut in range(len(parts) - 1, 0, -1):
        prefix = ".".join(parts[:cut])
        if prefix in API_RULES and API_RULES[prefix][0] in ("X25519", "X448", "Ed25519", "Ed448"):
            return prefix, API_RULES[prefix]
    return None


def _type_only(node: ast.AST) -> bool:
    """True when a reference only names a type: annotations, isinstance/issubclass, Union[...], class tuples."""
    child, parent = node, getattr(node, "_cs_parent", None)
    if isinstance(parent, (ast.Tuple, ast.List, ast.Set)):
        return True
    while parent is not None and not isinstance(parent, ast.stmt):
        if isinstance(parent, ast.Subscript) and child is parent.slice:
            return True
        if isinstance(parent, ast.arg) and child is parent.annotation:
            return True
        if (isinstance(parent, ast.Call) and isinstance(parent.func, ast.Name)
                and parent.func.id in ("isinstance", "issubclass", "cast") and child is not parent.func):
            return True
        child, parent = parent, getattr(parent, "_cs_parent", None)
    if isinstance(parent, ast.AnnAssign) and child is parent.annotation:
        return True
    if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)) and child is parent.returns:
        return True
    return False


class _Visitor(ast.NodeVisitor):
    def __init__(self, lines: List[str]) -> None:
        self.lines = lines
        self.aliases: Dict[str, str] = {}
        self.ssl_imported = False
        self.call_stack: List[str] = []
        self.hits: List[Dict[str, Any]] = []
        self._seen: set[Tuple[int, str, str]] = set()
        self._chain_inner: set[int] = set()

    # --- imports ---------------------------------------------------------
    def visit_Import(self, node: ast.Import) -> None:
        for a in node.names:
            if a.asname:
                self.aliases[a.asname] = a.name
            else:
                self.aliases[a.name.split(".")[0]] = a.name.split(".")[0]
            if a.name == "ssl":
                self.ssl_imported = True

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level or not node.module:
            return
        for a in node.names:
            self.aliases[a.asname or a.name] = f"{node.module}.{a.name}"
        if node.module == "ssl":
            self.ssl_imported = True

    # --- resolution ------------------------------------------------------
    def _resolve(self, node: ast.AST) -> Optional[str]:
        attrs: List[str] = []
        while isinstance(node, ast.Attribute):
            attrs.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name) and node.id in self.aliases:
            return ".".join([self.aliases[node.id]] + list(reversed(attrs)))
        return None

    def _add(self, line: int, family: str, purpose: str, ambiguity: str, confidence: str,
             value: str, reason: str, library: str) -> None:
        key = (line, family, purpose)
        if key in self._seen:
            return
        self._seen.add(key)
        self.hits.append({
            "line": line, "family": family, "purpose": purpose, "ambiguity": ambiguity,
            "confidence": confidence, "detected_value": value, "reason": reason,
            "library_or_protocol": library,
            "snippet": self.lines[line - 1] if 0 < line <= len(self.lines) else "",
        })

    def _check_ref(self, node: ast.AST) -> None:
        if _type_only(node):
            return
        qual = self._resolve(node)
        if not qual:
            return
        matched = _match_rule(qual)
        if not matched:
            return
        key, (family, purpose, ambiguity, confidence, reason) = matched
        if ambiguity == "ambiguous" and key.endswith("PKCS1v15"):
            for meth in reversed(self.call_stack):
                if meth in CONTEXT_PURPOSE:
                    purpose, ambiguity = CONTEXT_PURPOSE[meth], "none"
                    reason = f"PKCS#1 v1.5 padding passed to .{meth}()"
                    break
        self._add(node.lineno, family, purpose, ambiguity, confidence, _normalise(qual), reason, key.split(".")[0])

    # --- node visitors ---------------------------------------------------
    def visit_Attribute(self, node: ast.Attribute) -> None:
        if id(node) not in self._chain_inner:
            inner = node.value
            while isinstance(inner, ast.Attribute):
                self._chain_inner.add(id(inner))
                inner = inner.value
            self._check_ref(node)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load) and node.id in self.aliases and "." in self.aliases[node.id]:
            self._check_ref(node)

    def visit_Call(self, node: ast.Call) -> None:
        qual = self._resolve(node.func)
        if qual:
            self._check_call_literals(node, _normalise(qual))
        meth = node.func.attr if isinstance(node.func, ast.Attribute) else ""
        if meth in ("set_ciphers", "set_ecdh_curve") and self.ssl_imported:
            self._check_ssl_method(node, meth)
        self.call_stack.append(meth)
        self.generic_visit(node)
        self.call_stack.pop()

    def _check_call_literals(self, node: ast.Call, qual: str) -> None:
        if qual == "hashlib.new" and node.args and isinstance(node.args[0], ast.Constant):
            name = str(node.args[0].value).lower().replace("-", "")
            fam = {"sha1": "SHA-1", "md5": "MD5"}.get(name)
            if fam:
                self._add(node.lineno, fam, "message_digest", "none", "high", f"hashlib.new('{node.args[0].value}')",
                          f"{fam} selected by name in hashlib.new", "hashlib")
            return
        if qual in JWT_ENCODE_FUNCS or qual in JWT_DECODE_FUNCS:
            kw = {k.arg: k.value for k in node.keywords if k.arg}
            alg_node = kw.get("algorithm") or kw.get("algorithms")
            if alg_node is None and qual in JWT_ENCODE_FUNCS and len(node.args) >= 3:
                alg_node = node.args[2]
            values: List[str] = []
            if isinstance(alg_node, ast.Constant) and isinstance(alg_node.value, str):
                values = [alg_node.value]
            elif isinstance(alg_node, (ast.List, ast.Tuple)):
                values = [e.value for e in alg_node.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            for alg in values:
                fam = jwt_alg_family(alg)
                if fam:
                    self._add(node.lineno, fam, "digital_signature", "none", "high", f"{qual}(alg={alg})",
                              f"JWT/JWS signed with {alg} ({fam} signature)", qual.split(".")[0])

    def _check_ssl_method(self, node: ast.Call, meth: str) -> None:
        if not node.args or not isinstance(node.args[0], ast.Constant) or not isinstance(node.args[0].value, str):
            return
        value = node.args[0].value
        if meth == "set_ecdh_curve":
            self._add(node.lineno, "ECDH", "key_establishment", "none", "high", f"set_ecdh_curve('{value}')",
                      f"TLS ECDHE curve {value} configured", "ssl")
            return
        for fam, purpose, ambiguity, conf, why in analyse_cipher_string(value):
            self._add(node.lineno, fam, purpose, ambiguity, conf, f"set_ciphers('{value}')", why, "ssl")


def _constant_assignments(body: List[ast.stmt]) -> List[Tuple[int, str, str]]:
    """(line, NAME, value) for `NAME = "literal"` at module or class level (recursing into class bodies only)."""
    out: List[Tuple[int, str, str]] = []
    for stmt in body:
        if isinstance(stmt, ast.ClassDef):
            out += _constant_assignments(stmt.body)
            continue
        targets: List[ast.expr] = []
        value: Optional[ast.expr] = None
        if isinstance(stmt, ast.Assign):
            targets, value = stmt.targets, stmt.value
        elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
            targets, value = [stmt.target], stmt.value
        if not (isinstance(value, ast.Constant) and isinstance(value.value, str)):
            continue
        for t in targets:
            if isinstance(t, ast.Name):
                out.append((stmt.lineno, t.id, value.value))
    return out


def _algorithm_constant_hits(tree: ast.Module, lines: List[str]) -> List[Dict[str, Any]]:
    """Scoped 'algorithm constant' rule (see docs/member2/README.md): UPPER_CASE name with an algorithm keyword AND an
    exact identifier from the closed vocabulary. Confidence is low: the constant may never be used."""
    hits: List[Dict[str, Any]] = []
    for line, name, value in _constant_assignments(tree.body):
        if name != name.upper() or not (set(name.split("_")) & ALGORITHM_NAME_KEYWORDS):
            continue
        for fam, purpose, ambiguity, _conf, why in classify_identifier(value, context=name):
            hits.append({
                "line": line, "family": fam, "purpose": purpose, "ambiguity": ambiguity, "confidence": "low",
                "detected_value": f"{name} = {value!r}"[:200],
                "reason": f"algorithm constant {name}: {why} (constant rule; usage not traced)",
                "library_or_protocol": "constant", "snippet": lines[line - 1] if 0 < line <= len(lines) else "",
            })
    return hits


def scan_python_source(text: str) -> List[Dict[str, Any]]:
    """Return raw detection dicts for one Python source text. Raises SyntaxError for unparsable code."""
    tree = ast.parse(text)
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child._cs_parent = parent  # type: ignore[attr-defined]
    v = _Visitor(text.splitlines())
    # Collect imports first so uses that appear before a late import still resolve.
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            v.visit_Import(node)
        elif isinstance(node, ast.ImportFrom):
            v.visit_ImportFrom(node)
    v.visit(tree)
    seen = {(h["line"], h["family"]) for h in v.hits}
    v.hits += [h for h in _algorithm_constant_hits(tree, v.lines) if (h["line"], h["family"]) not in seen]
    return sorted(v.hits, key=lambda h: (h["line"], h["family"]))
