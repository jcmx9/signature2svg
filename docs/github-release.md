# GitHub Workflow & Release Process

## Branches

| Branch | Purpose | Commits |
|--------|---------|---------|
| `main` | Stable production releases | Only via `./scripts/release.sh prod` |
| `dev` | Development, default working branch | All regular commits |

**Default commit target is always `dev`.** Never commit directly to `main`.

## Versioning

CalVer `YY.M.x` with PEP 440 dev suffix:

- Production: `26.4.1`, `26.5.0`, `26.12.3`
- Development: `26.4.1.dev1`, `26.4.1.dev2`, ...

Version is stored in two files (updated automatically by the release script):
- `pyproject.toml` → `version = "..."`
- `src/signature2svg/__init__.py` → `__version__ = "..."`

Check current version:
```bash
python -c "import signature2svg; print(signature2svg.__version__)"
```

## Release Commands

### Dev Release

Creates a pre-release on the `dev` branch. Auto-increments the `.devN` counter.

```bash
./scripts/release.sh dev
```

What it does:
1. Verifies you're on `dev` branch with clean working tree
2. Finds the next `.devN` number from existing tags
3. Sets version in `pyproject.toml` + `__init__.py`
4. Commits, tags, pushes to `dev`
5. Creates GitHub pre-release

### Production Release

Merges `dev` → `main`, sets a clean version, tags on `main`.

```bash
./scripts/release.sh prod 26.5.0
```

What it does:
1. Verifies you're on `dev` branch with clean working tree
2. Sets version to `26.5.0` in both files
3. Commits on `dev`
4. Merges `dev` → `main`
5. Tags `v26.5.0` on `main`, pushes
6. Switches back to `dev`, pushes
7. Creates GitHub release on `main`

## Typical Workflow

```bash
# 1. Work on dev (default branch)
git add ...
git commit -m "feat: ..."

# 2. Dev release for testing
./scripts/release.sh dev
# → v26.4.1.dev1

# 3. More work, another dev release
git commit -m "fix: ..."
./scripts/release.sh dev
# → v26.4.1.dev2

# 4. Ready for production
./scripts/release.sh prod 26.4.2
# → v26.4.2 on main

# 5. Update installed tool
uv tool install --force git+https://github.com/jcmx9/signature2svg.git
```

## Version Number Convention

| When | Example | Rule |
|------|---------|------|
| New month | `26.5.0` | x resets to 0 |
| Patch in same month | `26.4.2` | Increment x |
| Dev release | `26.4.2.dev1` | Auto-incremented |
