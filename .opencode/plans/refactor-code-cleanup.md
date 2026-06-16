# Refactor: Code Cleanup

## Branch
`refactor/code-cleanup` (from `feat/windows-support`)

## 10 Fixes

### 1. C3 — current_rms race condition (stream.py)
- Add `threading.Lock` around `self.current_rms` (written by capture thread, read by main thread)
- **Edit 1** (line 92): add `self._rms_lock = threading.Lock()` after `self.current_rms`
- **Edit 2** (line 110): wrap `self.current_rms = np.sqrt(...)` in `with self._rms_lock:`

### 2. H1 — unused dependency (pyproject.toml)
- **Edit** (line 9): remove `"ffmpeg-python>=0.2.0",`

### 3. H7 — skip error segments in SRT (display.py:47)
- **Edit** (line 46-47): add `if seg.get("id", 0) < 0: return` as first line of `_append_srt()`

### 4. H8 — unused import (extractor.py:2)
- **Edit** (line 2): remove `import tempfile`

### 5. H9 — unused import (capture.py:1)
- **Edit** (line 1): remove `import os`, add `import re` alphabetically

### 6. H10 — misplaced re import (capture.py:34,43)
- **Edit** (line 34): remove `stderr=subprocess.PIPE` (redundant with `capture_output=True`)
- **Edit** (line 43): remove `import re` (moved to top in fix #5)

### 7. H11 — unused import (__main__.py:3)
- **Edit** (line 3): remove `import signal`

### 8. H12 — case-sensitive extension (generator.py:68)
- **Edit** (line 68): change `.lstrip(".") != fmt` to `.lstrip(".").lower() != fmt`

### 9. M13 — deprecated config (config.py)
- **Edit** (line 1): add `SettingsConfigDict` to import
- **Edit** (line 12): change `model_config = {"env_prefix": "", "env_file": ".env", "extra": "ignore"}`
  to `model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")`

### 10. M14 — close-before-terminate (capture.py:257-266)
- **Edit** (`_stop_ffmpeg`): reorder to terminate first, then close stdout
  ```
  - self._ffmpeg_process.stdout.close()
  - self._ffmpeg_process.terminate()
  + self._ffmpeg_process.terminate()
    try: self._ffmpeg_process.wait(timeout=2)
    except TimeoutExpired: self._ffmpeg_process.kill(); self._ffmpeg_process.wait()
  + self._ffmpeg_process.stdout.close()
  ```

## Verification
- `python -m py_compile src/audio/capture.py src/transcription/stream.py src/transcription/display.py src/subtitle/generator.py src/config.py src/__main__.py src/audio/extractor.py`
- `python -c "from src.audio.capture import _capture_config; print(_capture_config())"`
- `pip install -e .` (fails if pyproject.toml is wrong)
