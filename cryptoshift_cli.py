#!/usr/bin/env python3
"""Top-level CLI entrypoint for CryptoShift (PQC-01)."""

import sys

from cryptoshift.cli import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
