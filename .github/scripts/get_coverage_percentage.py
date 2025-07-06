#!/usr/bin/env python3
"""Extract coverage percentage from coverage.json."""

import json

with open("coverage.json") as f:
    data = json.load(f)
print(data["totals"]["percent_covered"])
