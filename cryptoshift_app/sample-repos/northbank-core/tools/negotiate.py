"""Deterministic TLS negotiation model.

Given the repository's tls_config policy and the peer profiles in peers.json,
emit one JSON trace per peer describing what a handshake would negotiate.
This models capability matching only; it does not open network connections.

Usage: python -m tools.negotiate  (prints JSON to stdout)
"""

import json
import os

from shared.bankcrypto import tls_config

VERSIONS = {"TLSv1.2": 2, "TLSv1.3": 3}


def negotiate(policy, peer):
    events = [{"step": "client_hello", "detail": f"{peer['max_version']}; groups={','.join(peer['groups'])}"}]
    if VERSIONS[peer["max_version"]] < VERSIONS[policy["min_version"]]:
        events.append({"step": "alert", "detail": "protocol_version"})
        return {"peer": peer["id"], "ok": False, "events": events}
    group = next((g for g in policy["groups"] if g in peer["groups"]), None)
    if group is None:
        events.append({"step": "alert", "detail": "handshake_failure: no shared key-exchange group"})
        return {"peer": peer["id"], "ok": False, "events": events}
    events.append({"step": "server_hello", "detail": f"group={group}"})
    if policy["cert_signature"] not in peer["cert_signatures"]:
        events.append({"step": "alert", "detail": f"bad_certificate: peer cannot verify {policy['cert_signature']}"})
        return {"peer": peer["id"], "ok": False, "group": group, "events": events}
    events.append({"step": "certificate", "detail": f"signature={policy['cert_signature']}"})
    events.append({"step": "finished", "detail": "handshake complete"})
    return {"peer": peer["id"], "ok": True, "group": group, "events": events}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "peers.json"), encoding="utf-8") as handle:
        peers = json.load(handle)["peers"]
    policy = tls_config.server_policy()
    print(json.dumps({"policy": policy, "results": [negotiate(policy, p) for p in peers]}))


if __name__ == "__main__":
    main()
