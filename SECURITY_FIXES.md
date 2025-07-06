# Security Scan Job Fixes Summary

This document summarizes the fixes applied to resolve security scan job failures.

## Issues Fixed

### 1. Bandit SARIF Format Error

**Problem**: Bandit command was failing with error: `argument -f/--format: invalid choice: 'sarif'`

**Root Cause**: The base `bandit` package doesn't include SARIF format support by default.

**Solution**: 
- Updated `pyproject.toml` to use `bandit[sarif]>=1.7.0,<2.0.0` instead of `bandit>=1.7.0,<2.0.0`
- This installs the additional dependencies (`sarif-om`, `jschema-to-python`) needed for SARIF support

**Before**:
```bash
bandit -r src/ -f sarif -o bandit.sarif  # ❌ Fails with "invalid choice: sarif"
```

**After**:
```bash
bandit -r src/ -f sarif -o bandit.sarif  # ✅ Works with bandit[sarif] installed
```

### 2. cyclonedx-py Command Syntax

**Problem**: Invalid command syntax for cyclonedx-py SBOM generation.

**Root Cause**: The command was likely using an old or incorrect syntax like `cyclonedx-py -r --format json`.

**Solution**:
- Added `cyclonedx-bom>=6.0.0,<7.0.0` to dev dependencies in `pyproject.toml`
- Created proper command syntax in the security-scan composite action

**Before** (incorrect):
```bash
cyclonedx-py -r --format json  # ❌ Invalid syntax
```

**After** (correct):
```bash
cyclonedx-py requirements requirements.txt --output-format json --output-file sbom.json  # ✅ Valid syntax
```

## Files Modified

### 1. `pyproject.toml`
- Updated bandit dependency to include SARIF extra: `bandit[sarif]>=1.7.0,<2.0.0`
- Added cyclonedx-bom for SBOM generation: `cyclonedx-bom>=6.0.0,<7.0.0`

### 2. `.github/workflows/ci.yml`
- Replaced inline security audit script with composite action
- Updated artifact upload to include SBOM file

### 3. `.github/actions/security-scan/action.yml` (NEW)
- Created reusable composite action for security scanning
- Includes proper bandit, pip-audit, detect-secrets, and cyclonedx-py commands
- Configurable inputs for source directory, output directory, and behavior options

### 4. `.github/workflows/ci-refactored.yml` (NEW)
- Demonstrates the fixed commands in a separate workflow
- Shows both security scanning and SBOM generation working correctly

## Testing Validation

The fixes have been validated to ensure:

1. ✅ `bandit -r src/ -f sarif -o bandit.sarif` works with `bandit[sarif]` installed
2. ✅ `bandit -r src/ -f json -o bandit-report.json` continues to work (fallback)
3. ✅ `cyclonedx-py requirements` with proper syntax generates SBOM successfully
4. ❌ Old invalid syntax `cyclonedx-py -r --format json` correctly fails with clear error message

## Benefits

1. **SARIF Support**: Security issues can now be properly uploaded to GitHub Security tab
2. **SBOM Generation**: Software Bill of Materials is generated for dependency tracking
3. **Modularity**: Security scanning logic is now in a reusable composite action
4. **Maintainability**: Commands use proper, documented syntax that won't break with updates
5. **Error Handling**: Better error messages and fallback strategies

## Usage

The security scan can now be run using the composite action:

```yaml
- name: 🔒 Run security scan
  uses: ./.github/actions/security-scan
  with:
    source-directory: src/
    output-directory: .
    fail-on-issues: 'true'
    generate-sbom: 'true'
```

This will:
- Run pip-audit for dependency vulnerabilities
- Run bandit for code security issues (with SARIF output)
- Run detect-secrets for secret detection
- Generate SBOM with cyclonedx-py
- Upload all results as artifacts
- Upload SARIF to GitHub Security tab