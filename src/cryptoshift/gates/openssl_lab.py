"""Loopback TLS / PQC lab driven by an OpenSSL 3.5+ binary (Member 3).

TEST SCENARIO only: 127.0.0.1, throw-away keys and certificates generated at runtime in a temporary directory
that is deleted afterwards. Nothing here contacts another host. Results are raw observations; gates in
`gates.verification_gates` decide pass/fail.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import socket
import statistics
import subprocess
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

DEFAULT_OPENSSL = Path(r"C:\Program Files\Git\usr\bin\openssl.exe")
LOOPBACK = "127.0.0.1"


_LAB_RE = re.compile(r"[A-Za-z]:[/\\][^\s\"']*?cs_m3_lab_[A-Za-z0-9_]+")
_USER_RE = re.compile(r"[A-Za-z]:[/\\]Users[/\\][^/\\\s]+")


def redact_paths(text: str) -> str:
    """Replace the temporary lab directory and any user-profile path in recorded command lines."""
    return _USER_RE.sub("~", _LAB_RE.sub("<lab>", text))


def openssl_path() -> Optional[Path]:
    env = os.environ.get("CRYPTOSHIFT_OPENSSL")
    for cand in (Path(env) if env else None, DEFAULT_OPENSSL, Path(shutil.which("openssl") or "")):
        if cand and cand.is_file():
            return cand
    return None


def _run(args: List[str], input_bytes: bytes = b"", timeout: float = 30) -> subprocess.CompletedProcess:
    exe = openssl_path()
    if exe is None:
        raise FileNotFoundError("OpenSSL 3.5+ binary not found (set CRYPTOSHIFT_OPENSSL)")
    return subprocess.run([str(exe), *args], input=input_bytes, capture_output=True, timeout=timeout)


def capabilities() -> Dict[str, Any]:
    exe = openssl_path()
    if exe is None:
        return {"available": False}
    version = _run(["version"]).stdout.decode().strip()
    groups = _run(["list", "-tls1_3", "-tls-groups"]).stdout.decode().strip()
    sigs = _run(["list", "-signature-algorithms"]).stdout.decode()
    kems = _run(["list", "-kem-algorithms"]).stdout.decode()
    return {
        "available": True, "binary": exe.name, "version": version,
        "x25519mlkem768_tls_group": "X25519MLKEM768" in groups, "ml_kem_768": "ML-KEM-768" in kems,
        "ml_dsa_65": "ML-DSA-65" in sigs,
    }


@contextmanager
def lab_dir() -> Iterator[Path]:
    d = Path(tempfile.mkdtemp(prefix="cs_m3_lab_"))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


def make_cert(d: Path, name: str, key_alg: str = "EC-P256", expired: bool = False, cn: str = "localhost") -> Dict[str, str]:
    key, cert = d / f"{name}.key.pem", d / f"{name}.cert.pem"
    args = ["req", "-x509", "-nodes", "-subj", f"/CN={cn}", "-keyout", key.as_posix(), "-out", cert.as_posix()]
    if key_alg == "EC-P256":
        args += ["-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256"]
    else:
        args += ["-newkey", key_alg]
    args += ["-not_before", "20200101000000Z", "-not_after", "20200102000000Z"] if expired else ["-days", "1"]
    r = _run(args)
    if r.returncode != 0:
        raise RuntimeError(f"cert generation failed for {key_alg}: {r.stderr.decode(errors='replace')[:200]}")
    return {"key": key.as_posix(), "cert": cert.as_posix(), "key_alg": key_alg, "expired": str(expired)}


def _free_port() -> int:
    with socket.socket() as s:
        s.bind((LOOPBACK, 0))
        return s.getsockname()[1]


@contextmanager
def tls_server(cert: Dict[str, str], groups: str, extra: Optional[List[str]] = None, naccept: int = 1) -> Iterator[Dict[str, Any]]:
    port = _free_port()
    exe = openssl_path()
    args = [str(exe), "s_server", "-accept", f"{LOOPBACK}:{port}", "-cert", cert["cert"], "-key", cert["key"],
            "-groups", groups, "-naccept", str(naccept), "-quiet", *(extra or [])]
    proc = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            with socket.create_connection((LOOPBACK, port), timeout=0.2):
                break
        except OSError:
            if proc.poll() is not None:
                break
            time.sleep(0.05)
    # The probe connection above consumed one accept slot; callers size naccept accordingly.
    try:
        yield {"port": port, "args": " ".join(["openssl"] + args[1:]), "proc": proc}
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=10)
        if proc.stdout:
            proc.stdout.close()


def client_handshake(port: int, groups: Optional[str] = None, extra: Optional[List[str]] = None,
                     ca_file: Optional[str] = None, verify: bool = False) -> Dict[str, Any]:
    args = ["s_client", "-connect", f"{LOOPBACK}:{port}", "-servername", "localhost"]
    if groups:
        args += ["-groups", groups]
    if verify and ca_file:
        args += ["-CAfile", ca_file, "-verify_return_error", "-verify_hostname", "localhost"]
    args += extra or []
    t0 = time.perf_counter()
    r = _run(args, input_bytes=b"", timeout=30)
    elapsed = time.perf_counter() - t0
    out = (r.stdout + r.stderr).decode(errors="replace")
    return parse_client_output(out, r.returncode, elapsed, "openssl " + " ".join(args))


def parse_client_output(out: str, rc: int, elapsed: float, cmd: str) -> Dict[str, Any]:
    def grab(pat: str) -> Optional[str]:
        m = re.search(pat, out)
        return m.group(1).strip() if m else None

    proto = grab(r"Protocol\s*:\s*(\S+)") or grab(r"New, (TLSv[\d.]+)")
    cipher = grab(r"Cipher is (\S+)")
    m =re.search(r"handshake has read (\d+) bytes and written (\d+) bytes", out)
    group = (grab(r"Negotiated TLS1\.3 group:\s*(\S+)") or grab(r"Peer Temp Key:\s*([^,\n]+)")
             or grab(r"Server Temp Key:\s*([^,\n]+)"))
    ok = bool(cipher) and cipher != "(NONE)" and rc == 0
    errors = [l.strip() for l in out.splitlines() if re.search(r"error|alert|failure", l, re.I)][:5]
    return {
        "handshake_ok": ok, "returncode": rc, "protocol": proto, "group": group, "cipher": cipher,
        "bytes_read": int(m.group(1)) if m else None, "bytes_written": int(m.group(2)) if m else None,
        "peer_signature_type": grab(r"Peer signature type:\s*(\S+)"),
        "verify_return_code": grab(r"Verify return code:\s*(.+)"),
        "errors": errors, "elapsed_seconds": round(elapsed, 5), "command": redact_paths(cmd),
    }


def handshake(cert: Dict[str, str], server_groups: str, client_groups: Optional[str],
              server_extra: Optional[List[str]] = None, client_extra: Optional[List[str]] = None,
              verify: bool = False, ca_file: Optional[str] = None) -> Dict[str, Any]:
    with tls_server(cert, server_groups, server_extra, naccept=2) as srv:
        res = client_handshake(srv["port"], client_groups, client_extra, ca_file=ca_file, verify=verify)
        res["server_command"] = redact_paths(srv["args"])
    res["server_groups"], res["client_groups"] = server_groups, client_groups
    return res


# ------------------------------------------------------------------ self-tests ----------------------------------

def mlkem_roundtrip_openssl(d: Path) -> Dict[str, Any]:
    priv, pub, ct, s1, s2 = (d / n for n in ("kem.pem", "kem_pub.pem", "ct.bin", "ss1.bin", "ss2.bin"))
    steps = [
        ["genpkey", "-algorithm", "ML-KEM-768", "-out", priv.as_posix()],
        ["pkey", "-in", priv.as_posix(), "-pubout", "-out", pub.as_posix()],
        ["pkeyutl", "-encap", "-pubin", "-inkey", pub.as_posix(), "-out", ct.as_posix(), "-secret", s1.as_posix()],
        ["pkeyutl", "-decap", "-inkey", priv.as_posix(), "-in", ct.as_posix(), "-secret", s2.as_posix()],
    ]
    for s in steps:
        r = _run(s)
        if r.returncode != 0:
            return {"status": "FAIL", "step": s[0], "error": r.stderr.decode(errors="replace")[:200]}
    a, b = s1.read_bytes(), s2.read_bytes()
    return {"status": "PASS" if a == b and len(a) == 32 else "FAIL", "implementation": "OpenSSL CLI",
            "algorithm": "ML-KEM-768", "ciphertext_bytes": ct.stat().st_size, "shared_secret_bytes": len(a),
            "secrets_equal": a == b, "commands": [redact_paths(" ".join(["openssl", *s])) for s in steps],
            "note": "round-trip self-test with a fresh key pair; NOT a NIST known-answer test"}


def mlkem_roundtrip_cryptography() -> Dict[str, Any]:
    from cryptography.hazmat.primitives.asymmetric import mlkem

    k = mlkem.MLKEM768PrivateKey.generate()
    ss1, ct = k.public_key().encapsulate()
    ss2 = k.decapsulate(ct)
    return {"status": "PASS" if ss1 == ss2 else "FAIL", "implementation": "python cryptography",
            "algorithm": "ML-KEM-768", "ciphertext_bytes": len(ct), "shared_secret_bytes": len(ss1),
            "secrets_equal": ss1 == ss2, "note": "round-trip self-test; NOT a NIST known-answer test"}


def mldsa_sign_verify_openssl(d: Path) -> Dict[str, Any]:
    priv, pub, msg, sig = (d / n for n in ("dsa.pem", "dsa_pub.pem", "msg.txt", "sig.bin"))
    msg.write_bytes(b"CryptoShift ML-DSA-65 self-test message")
    steps = [
        ["genpkey", "-algorithm", "ML-DSA-65", "-out", priv.as_posix()],
        ["pkey", "-in", priv.as_posix(), "-pubout", "-out", pub.as_posix()],
        ["pkeyutl", "-sign", "-inkey", priv.as_posix(), "-rawin", "-in", msg.as_posix(), "-out", sig.as_posix()],
    ]
    for s in steps:
        r = _run(s)
        if r.returncode != 0:
            return {"status": "BLOCKED", "step": s[0], "error": r.stderr.decode(errors="replace")[:200]}
    ok = _run(["pkeyutl", "-verify", "-pubin", "-inkey", pub.as_posix(), "-rawin", "-in", msg.as_posix(),
               "-sigfile", sig.as_posix()])
    msg.write_bytes(b"tampered")
    bad = _run(["pkeyutl", "-verify", "-pubin", "-inkey", pub.as_posix(), "-rawin", "-in", msg.as_posix(),
                "-sigfile", sig.as_posix()])
    return {"status": "PASS" if ok.returncode == 0 and bad.returncode != 0 else "FAIL", "implementation": "OpenSSL CLI",
            "algorithm": "ML-DSA-65", "signature_bytes": sig.stat().st_size, "valid_signature_verified": ok.returncode == 0,
            "tampered_message_rejected": bad.returncode != 0, "note": "sign/verify self-test; NOT a NIST known-answer test"}


def mldsa_sign_verify_cryptography() -> Dict[str, Any]:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric import mldsa

    k = mldsa.MLDSA65PrivateKey.generate()
    m = b"CryptoShift ML-DSA-65 self-test message"
    sig = k.sign(m)
    k.public_key().verify(sig, m)
    try:
        k.public_key().verify(sig, b"tampered")
        rejected = False
    except InvalidSignature:
        rejected = True
    return {"status": "PASS" if rejected else "FAIL", "implementation": "python cryptography", "algorithm": "ML-DSA-65",
            "signature_bytes": len(sig), "tampered_message_rejected": rejected,
            "note": "sign/verify self-test; NOT a NIST known-answer test"}


# ------------------------------------------------------------------ experiments ---------------------------------

CLASSICAL, HYBRID = "X25519", "X25519MLKEM768"


def traces(d: Path) -> Dict[str, Any]:
    ec = make_cert(d, "ec")
    before = handshake(ec, CLASSICAL, CLASSICAL)
    after = handshake(ec, HYBRID, HYBRID)
    out = {"label": "TEST SCENARIO, loopback, test keys", "certificate": "self-signed EC P-256 (throw-away)",
           "before_classical": before, "after_hybrid": after}
    try:
        md = make_cert(d, "mldsa", key_alg="ML-DSA-65")
        out["after_hybrid_mldsa_cert"] = handshake(md, HYBRID, HYBRID)
        out["after_hybrid_mldsa_cert"]["certificate"] = "self-signed ML-DSA-65 (throw-away)"
    except RuntimeError as exc:
        out["after_hybrid_mldsa_cert"] = {"handshake_ok": False, "status": "BLOCKED", "reason": str(exc)}
    return out


def compatibility_matrix(d: Path) -> List[Dict[str, Any]]:
    ec = make_cert(d, "ec")
    expired = make_cert(d, "expired", expired=True)
    other = make_cert(d, "other", cn="not-localhost")
    cases = [
        # name, server_groups, client_groups, client_extra, cert, verify, ca, expect_ok, expect_group, category
        ("classical client -> classical server", CLASSICAL, CLASSICAL, None, ec, False, None, True, CLASSICAL, "positive"),
        ("hybrid client -> hybrid server", HYBRID, HYBRID, None, ec, False, None, True, HYBRID, "positive"),
        ("classical client -> hybrid-capable server (fallback)", f"{HYBRID}:{CLASSICAL}", CLASSICAL, None, ec, False, None, True, CLASSICAL, "fallback"),
        ("hybrid-preferring client -> classical-only server (fallback)", CLASSICAL, f"{HYBRID}:{CLASSICAL}", None, ec, False, None, True, CLASSICAL, "fallback"),
        ("classical-only client -> hybrid-required server", HYBRID, CLASSICAL, None, ec, False, None, False, None, "negative"),
        ("TLS 1.2-only client -> hybrid-required server", HYBRID, None, ["-tls1_2"], ec, False, None, False, None, "negative"),
        ("mismatched group (SecP256r1MLKEM768 vs X25519MLKEM768-only)", HYBRID, "SecP256r1MLKEM768", None, ec, False, None, False, None, "negative"),
        ("no common group (ffdhe2048 vs X25519MLKEM768-only)", HYBRID, "ffdhe2048", None, ec, False, None, False, None, "negative"),
        ("expired certificate, verifying client", f"{HYBRID}:{CLASSICAL}", HYBRID, None, expired, True, expired["cert"], False, None, "negative"),
        ("wrong certificate (untrusted CA), verifying client", f"{HYBRID}:{CLASSICAL}", HYBRID, None, ec, True, other["cert"], False, None, "negative"),
        ("correct trusted certificate, verifying client", f"{HYBRID}:{CLASSICAL}", HYBRID, None, ec, True, ec["cert"], True, HYBRID, "positive"),
    ]
    rows = []
    for name, sg, cg, cx, cert, ver, ca, exp_ok, exp_group, cat in cases:
        r = handshake(cert, sg, cg, client_extra=cx, verify=ver, ca_file=ca)
        observed_ok = r["handshake_ok"]
        passed = observed_ok == exp_ok and (exp_group is None or not observed_ok or r["group"] == exp_group)
        rows.append({"case": name, "category": cat, "server_groups": sg, "client_groups": cg or "(default)",
                     "client_extra": cx or [], "verify": ver, "expected": "handshake OK" + (f", group {exp_group}" if exp_group else "") if exp_ok else "handshake REJECTED",
                     "observed": (f"OK, {r['protocol']}, group {r['group']}" if observed_ok else f"REJECTED ({'; '.join(r['errors'][:2]) or 'rc=' + str(r['returncode'])})"),
                     "pass": passed, "protocol": r["protocol"], "group": r["group"],
                     "verify_return_code": r["verify_return_code"], "command": r["command"], "server_command": r["server_command"]})
    return rows


def overhead(d: Path, n: int = 30, warmup: int = 5) -> Dict[str, Any]:
    """Interleaved handshakes (fixed order A,B,A,B...) against one long-lived server per configuration."""
    ec = make_cert(d, "ec")
    configs = {"classical_X25519": CLASSICAL, "hybrid_X25519MLKEM768": HYBRID}
    samples: Dict[str, List[Dict[str, Any]]] = {k: [] for k in configs}
    servers = {}
    stack = []
    try:
        for name, grp in configs.items():
            cm = tls_server(ec, grp, naccept=n + warmup + 2)
            servers[name] = cm.__enter__()
            stack.append(cm)
        for i in range(warmup + n):
            for name, grp in configs.items():
                r = client_handshake(servers[name]["port"], grp)
                if i >= warmup:
                    samples[name].append(r)
    finally:
        for cm in reversed(stack):
            cm.__exit__(None, None, None)

    def summary(rs: List[Dict[str, Any]]) -> Dict[str, Any]:
        t = sorted(x["elapsed_seconds"] * 1000 for x in rs if x["handshake_ok"])
        p95 = t[min(len(t) - 1, int(round(0.95 * (len(t) - 1))))] if t else None
        return {"n_ok": len(t), "n_total": len(rs), "samples_ms": [round(x, 3) for x in t],
                "median_ms": round(statistics.median(t), 3) if t else None,
                "p95_ms": round(p95, 3) if p95 else None, "min_ms": round(t[0], 3) if t else None,
                "bytes_read": sorted({x["bytes_read"] for x in rs}), "bytes_written": sorted({x["bytes_written"] for x in rs}),
                "groups": sorted({str(x["group"]) for x in rs})}

    import multiprocessing

    return {
        "label": "TEST SCENARIO, loopback, test keys; NOT a network benchmark",
        "method": f"{warmup} warm-up + {n} measured handshakes per config, interleaved fixed order; time = wall clock of one "
                  "`openssl s_client` process (includes process start-up, which dominates)",
        "environment": {"os": platform.platform(), "cpu": platform.processor(), "logical_cpus": multiprocessing.cpu_count(),
                        "python": platform.python_version(), "openssl": capabilities().get("version")},
        "results": {k: summary(v) for k, v in samples.items()},
    }
