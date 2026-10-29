"""Stage 1 inventory detectors (additive to `cryptoshift.scanner`; pending Member 2 review).

Detectors: Python AST, TLS configs (nginx/Apache/openssl.cnf), dependency manifests, certificate metadata.
"""

from cryptoshift.inventory.report import build_cbom_like, render_markdown, write_inventory
from cryptoshift.inventory.scan import scan_inventory

__all__ = ["scan_inventory", "build_cbom_like", "render_markdown", "write_inventory"]
