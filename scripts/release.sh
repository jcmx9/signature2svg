#!/usr/bin/env bash
# Dev release:  ./scripts/release.sh dev
# Prod release: ./scripts/release.sh prod 26.5.0
set -euo pipefail

MODE="${1:?Usage: $0 dev | prod <version>}"
TOML="pyproject.toml"
INIT="src/signature2svg/__init__.py"

current_version() {
    grep '^version = ' "$TOML" | sed 's/version = "\(.*\)"/\1/'
}

set_version() {
    local v="$1"
    sed -i '' "s/^version = \".*\"/version = \"$v\"/" "$TOML"
    sed -i '' "s/^__version__ = \".*\"/__version__ = \"$v\"/" "$INIT"
}

ensure_clean() {
    if [[ -n "$(git status --porcelain)" ]]; then
        echo "Error: Working tree not clean. Commit or stash first." >&2
        exit 1
    fi
}

if [[ "$MODE" == "dev" ]]; then
    # Must be on dev branch
    branch="$(git branch --show-current)"
    if [[ "$branch" != "dev" ]]; then
        echo "Error: Must be on dev branch (currently on $branch)" >&2
        exit 1
    fi
    ensure_clean

    cur="$(current_version)"
    base="${cur%.dev*}"  # strip any existing .devN

    # Find next dev number
    last=$(git tag -l "v${base}.dev*" | sed "s/v${base}\.dev//" | sort -n | tail -1)
    next=$(( ${last:-0} + 1 ))
    version="${base}.dev${next}"

    set_version "$version"
    git add "$TOML" "$INIT"
    git commit -m "release: v$version"
    git tag "v$version"
    git push origin dev --tags

    gh release create "v$version" --title "v$version" --target dev --prerelease --generate-notes
    echo "Dev release: v$version"

elif [[ "$MODE" == "prod" ]]; then
    VERSION="${2:?Usage: $0 prod <version> (e.g. 26.5.0)}"

    if [[ ! "$VERSION" =~ ^[0-9]{2}\.[0-9]{1,2}\.[0-9]+$ ]]; then
        echo "Error: Version must match CalVer YY.M.x (e.g. 26.5.0)" >&2
        exit 1
    fi

    # Must be on dev branch, merge to main
    branch="$(git branch --show-current)"
    if [[ "$branch" != "dev" ]]; then
        echo "Error: Must be on dev branch (currently on $branch)" >&2
        exit 1
    fi
    ensure_clean

    # Set version on dev, commit
    set_version "$VERSION"
    git add "$TOML" "$INIT"
    git commit -m "release: v$VERSION"

    # Merge dev → main
    git checkout main
    git merge dev --no-edit
    git tag "v$VERSION"
    git push origin main --tags

    # Back to dev
    git checkout dev
    git push origin dev

    gh release create "v$VERSION" --title "v$VERSION" --target main --generate-notes
    echo "Production release: v$VERSION"

else
    echo "Usage: $0 dev | prod <version>" >&2
    exit 1
fi
