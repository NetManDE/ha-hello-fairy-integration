# GitHub Actions Workflows

This directory contains automated workflows for the Hello Fairy integration.

## Workflows

### 🚀 Release (`release.yml`)

**Trigger:** When a new release is published on GitHub

**What it does:**
1. Checks out the repository
2. Creates a ZIP file of the `custom_components/hellofairy` directory
3. Uploads the ZIP as a release asset
4. Provides download link in the workflow summary

**Usage:**
1. Create a new tag: `git tag -a v1.0.9 -m "Release v1.0.9"`
2. Push the tag: `git push origin v1.0.9`
3. Create a release on GitHub from that tag
4. The workflow runs automatically and adds `hellofairy.zip` to the release

**For HACS:**
HACS will automatically detect the ZIP asset and use it for installation/updates.

### ✅ Validate (`validate.yml`)

**Trigger:** On push to main branch or pull requests

**What it does:**
1. Validates `manifest.json` syntax
2. Checks Python syntax for all `.py` files
3. Checks for common issues (e.g., print statements)

**Checks performed:**
- ✅ Valid JSON in manifest.json
- ✅ Python syntax correctness
- ✅ No print() statements (should use _LOGGER)

## Local Testing

Before pushing, you can test locally:

```bash
# Validate manifest.json
python -c "import json; json.load(open('custom_components/hellofairy/manifest.json'))"

# Check Python syntax
python -m py_compile custom_components/hellofairy/*.py

# Check for print statements
grep -r "print(" custom_components/hellofairy/*.py
```

## Permissions

The workflows require:
- `contents: write` - To upload release assets
- `GITHUB_TOKEN` - Automatically provided by GitHub Actions
