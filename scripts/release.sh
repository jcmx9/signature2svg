#!/usr/bin/env bash
# Dev release:  ./scripts/release.sh dev
# Prod release: ./scripts/release.sh prod
# New month:    ./scripts/release.sh prod --new-month
set -euo pipefail

MODE="${1:?Usage: $0 dev | prod [--new-month]}"

ensure_branch() {
    local branch
    branch="$(git branch --show-current)"
    if [[ "$branch" != "dev" ]]; then
        echo "Error: Must be on dev branch (currently on $branch)" >&2
        exit 1
    fi
}

if [[ "$MODE" == "dev" ]]; then
    ensure_branch

    # Dev bump: increment .devN, commit, no tag
    uv run bump-my-version bump dev --no-tag
    git push origin dev

    version="$(grep '^current_version' pyproject.toml | head -1 | sed 's/.*= "\(.*\)"/\1/')"
    echo "Dev release: v$version"

elif [[ "$MODE" == "prod" ]]; then
    ensure_branch

    # Determine bump type: new month or patch
    if [[ "${2:-}" == "--new-month" ]]; then
        uv run bump-my-version bump release
    else
        uv run bump-my-version bump patch
    fi

    version="$(grep '^current_version' pyproject.toml | head -1 | sed 's/.*= "\(.*\)"/\1/')"

    # Merge dev → main
    git checkout main
    git merge dev --no-edit
    git push origin main --tags

    # Back to dev
    git checkout dev
    git push origin dev

    # GitHub release
    gh release create "v$version" --title "v$version" --target main --generate-notes
    echo "Production release: v$version"

else
    echo "Usage: $0 dev | prod [--new-month]" >&2
    exit 1
fi
