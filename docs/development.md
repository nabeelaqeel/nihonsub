# Development

## Setup

```bash
git clone https://github.com/nabeelaqeel/nihonsub.git
cd nihonsub

python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Adding Dependencies

Add the package to `pyproject.toml` under `[project] dependencies`, then:

```bash
pip install -e .
```

## Code Conventions

- **Type hints** everywhere
- **Threading** for live pipeline (capture / VAD / transcription / display)
- **Pydantic models** for all data schemas
- **Absolute imports** within the package (`from src.audio.capture import ...`)
- **Conventional Commits** for git messages (`feat:`, `fix:`, `docs:`, `refactor:`, etc.)

## Running Tests

```bash
pytest tests/
```

## Making Changes

1. Branch from `main`: `git checkout -b feat/my-feature`
2. Make changes, commit with conventional commit messages
3. Open a pull request back to `main`
4. Tag releases: `git tag v0.2 && git push origin v0.2`

## Pull Request Checklist

- [ ] Code compiles and imports without errors
- [ ] Type hints present on all new functions
- [ ] Tests pass (if applicable)
- [ ] `AGENTS.md` updated if architecture has changed
- [ ] `docs/` updated if user-facing behavior has changed
