#!/usr/bin/env python3
"""Parse benchmark results from JSON and display summary."""

import json

with open("benchmark.json") as f:
    data = json.load(f)

print("| Test | Min | Mean | Max | Stddev |")
print("|------|-----|------|-----|--------|")
for bench in data["benchmarks"]:
    print(
        f"| {bench['name']} | "
        f"{bench['stats']['min']:.3f}s | "
        f"{bench['stats']['mean']:.3f}s | "
        f"{bench['stats']['max']:.3f}s | "
        f"{bench['stats']['stddev']:.3f}s |"
    )
