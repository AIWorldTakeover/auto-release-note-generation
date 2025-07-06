#!/usr/bin/env python3
"""Parse pip-audit exclusions from YAML file."""

import sys

import yaml  # type: ignore[import-untyped]

try:
    with open(".pip-audit-exclusions.yaml") as f:
        data = yaml.safe_load(f)
    vulns = []
    if isinstance(data, dict):
        for package, vuln_list in data.items():
            if isinstance(vuln_list, list) and package not in ["#", "comment"]:
                vulns.extend(vuln_list)
    print(" ".join(vulns))
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
