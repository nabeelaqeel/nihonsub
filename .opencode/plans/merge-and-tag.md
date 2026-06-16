# Merge + Tag v0.2 Execution Plan

## Current state
- On branch `refactor/code-cleanup` (uncommitted)
- `feat/windows-support` is complete and working

## Steps

### 1. Update release doc and tag v0.2

```bash
git checkout feat/windows-support

# Edit docs/releases/v0.2.md:
#   Tag: (pending) → Tag: v0.2
#   Branch: feat/windows-support → Branch: feat/windows-support (merged to main)

git add docs/releases/v0.2.md
git commit -m "release: mark v0.2"
git tag v0.2
git push origin feat/windows-support --tags
```

### 2. Merge to main

```bash
git checkout main
git merge feat/windows-support --no-ff
git push origin main
```

### 3. Create cleanup branch from main

```bash
git checkout -b refactor/code-cleanup main
```

### 4. Apply 10 cleanup fixes

| # | File | Change |
|---|------|--------|
| 1 | `src/transcription/stream.py:92` | Add `self._rms_lock = threading.Lock()` |
| 2 | `src/transcription/stream.py:110` | Wrap `self.current_rms = ...` in `with self._rms_lock:` |
| 3 | `pyproject.toml:9` | Remove `"ffmpeg-python>=0.2.0",` |
| 4 | `src/transcription/display.py:47` | Add `if seg.get("id", 0) < 0: return` |
| 5 | `src/audio/extractor.py:2` | Remove `import tempfile` |
| 6 | `src/audio/capture.py:1` | Remove `import os`, add `import re` |
| 7 | `src/audio/capture.py:34` | Remove `stderr=subprocess.PIPE` |
| 8 | `src/audio/capture.py:43` | Remove `import re` (now at top) |
| 9 | `src/__main__.py:3` | Remove `import signal` |
| 10 | `src/subtitle/generator.py:68` | `.lower()` on extension |
| 11 | `src/config.py:1` | Add `SettingsConfigDict` to import |
| 12 | `src/config.py:12` | Use `SettingsConfigDict(...)` |
| 13 | `src/audio/capture.py:257-266` | Reorder: terminate → wait → close stdout |

```bash
git commit -m "refactor: apply code cleanup fixes"
git push origin refactor/code-cleanup
```

### 5. Verify

```bash
python -m py_compile src/audio/capture.py src/transcription/stream.py \
  src/transcription/display.py src/subtitle/generator.py src/config.py \
  src/__main__.py src/audio/extractor.py

python -c "from src.audio.capture import _capture_config; print(_capture_config())"
```
