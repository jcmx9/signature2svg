#!/usr/bin/env bash
# Usage: ./scripts/release.sh 26.5.0
# Sets version in pyproject.toml + __init__.py, commits, tags, pushes, creates GitHub release.

set -euo pipefail

VERSION="${1:?Usage: $0 <version> (e.g. 26.5.0)}"

if [[ ! "$VERSION" =~ ^[0-9]{2}\.[0-9]{1,2}\.[0-9]+$ ]]; then
    echo "Error: Version must match CalVer YY.M.x (e.g. 26.5.0)" >&2
    exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
    echo "Error: Working tree not clean. Commit or stash changes first." >&2
    exit 1
fi

# Update version in both files
sed -i '' "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml
sed -i '' "s/^__version__ = \".*\"/__version__ = \"$VERSION\"/" src/signature2svg/__init__.py

# Commit, tag, push
git add pyproject.toml src/signature2svg/__init__.py
git commit -m "release: v$VERSION"
git tag "v$VERSION"
git push origin master --tags

# Create GitHub release
gh release create "v$VERSION" --title "v$VERSION" --generate-notes

echo "Released v$VERSION"
