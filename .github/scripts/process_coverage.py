#!/usr/bin/env python3
"""Process coverage JSON and generate summary report."""

import json
import os

try:
    with open("coverage.json") as f:
        data = json.load(f)

    totals = data["totals"]
    coverage_pct = totals["percent_covered"]

    # Generate summary with emojis based on coverage
    emoji = "🟢" if coverage_pct >= 85 else "🟡" if coverage_pct >= 70 else "🔴"

    summary = f"""### 📊 Coverage Report

{emoji} **Total Coverage: {coverage_pct:.1f}%**

| Metric | Value |
|--------|-------|
| Lines Covered | {totals["covered_lines"]:,} / {totals["num_statements"]:,} |
| Branches | {totals.get("covered_branches", 0):,} / {totals.get("num_branches", 0):,} |
| Missing Lines | {totals["missing_lines"]:,} |
| Excluded Lines | {totals.get("excluded_lines", 0):,} |
"""

    # Write to GitHub summary if available
    if "GITHUB_STEP_SUMMARY" in os.environ:
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(summary)

    print(f"Coverage: {coverage_pct:.1f}%")
except Exception as e:
    print(f"Error processing coverage: {e}")
