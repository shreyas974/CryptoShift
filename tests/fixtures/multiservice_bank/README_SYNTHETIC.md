# SYNTHETIC multi-service bank fixture (test data, not a real system)

Small, invented repository used by `tests/test_member2_detectors.py` and as an example input for Member 3's
dependency graph. It contains no keys or certificates; all hosts are fictional compose service names.

| Path | Exercises |
|---|---|
| `docker-compose.yml` | compose services, build contexts, volume mounts, `depends_on`, `links` |
| `gateway/nginx.conf` | nginx TLS directives, `upstream` + `proxy_pass`, an unresolvable host (UNKNOWN reference) |
| `edge/haproxy.cfg` | HAProxy `ssl-default-*`, `bind` options, backend `server` lines |
| `services/payments/` | Python service: AST detector, algorithm constants, cross-service import, `application.properties` |
| `services/ledger/` | Python package, `Dockerfile` with `openssl`, Java JCA calls, `application.yaml` |
| `scripts/rotate_keys.sh` | `openssl` / `ssh-keygen` commands plus hard negatives |

Hard negatives are marked with `# HN` (or `// HN`) comments where the syntax allows.
