# GitHub Workflow & Release Process

## Branches

| Branch | Purpose | Commits |
|--------|---------|---------|
| `main` | Stable production releases | Only via `./scripts/release.sh prod` |
| `dev` | Development, default working branch | All regular commits |

**Default commit target is always `dev`.** Never commit directly to `main`.

## Versioning

CalVer `YY.M.x` with PEP 440 dev suffix, managed by **bump-my-version**:

- Production: `26.4.1`, `26.5.0`, `26.12.3`
- Development: `26.4.1.dev0`, `26.4.1.dev1`, ...

Version is stored in three places (all updated automatically):
- `pyproject.toml` → `current_version` (bumpversion config)
- `pyproject.toml` → `version` (project metadata)
- `src/signature2svg/__init__.py` → `__version__`

## Release Commands

### Dev Release

```bash
./scripts/release.sh dev
```

Increments `.devN` counter, commits on `dev`, pushes. No tag, no GitHub release.

```
26.4.1 → 26.4.1.dev0 → 26.4.1.dev1 → ...
```

### Production Release (patch)

```bash
./scripts/release.sh prod
```

Strips `.devN`, bumps patch, commits, merges dev → main, tags, pushes, creates GitHub release.

```
26.4.1.dev3 → 26.4.2 (on main)
```

### Production Release (new month)

```bash
./scripts/release.sh prod --new-month
```

Advances to next CalVer month, resets patch to 0.

```
26.4.2 → 26.5.0 (on main)
```

## Typical Workflow

```bash
# 1. Work on dev
git commit -m "feat: ..."

# 2. Dev release for testing
./scripts/release.sh dev          # → 26.4.2.dev0

# 3. More work
git commit -m "fix: ..."
./scripts/release.sh dev          # → 26.4.2.dev1

# 4. Production release
./scripts/release.sh prod         # → 26.4.2 on main

# 5. Update installed tool
uv tool install --force git+https://github.com/jcmx9/signature2svg.git
```

## Manual bump-my-version Commands

```bash
# Preview what would happen
bump-my-version show-bump

# Dry run
bump-my-version bump patch --dry-run --verbose

# Direct bump without release script
bump-my-version bump dev --no-tag     # dev increment
bump-my-version bump patch            # prod patch
bump-my-version bump release          # new month
```
