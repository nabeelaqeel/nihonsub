# Packaging Plan (Future)

How to distribute nihonsub to end users for easy installation.

## Requirements

Any packaging solution must handle:

- **faster-whisper + torch** — large ML dependencies (~2 GB)
- **ffmpeg** — required for audio extraction, must be on PATH or bundled
- **VoiceMeeter / VB-Cable** — separate install for Windows loopback (can't be bundled)
- **silero-vad** — lightweight, bundled with pip
- **sounddevice** — Windows fallback capture, bundled with pip
- **Whisper model** — downloaded on first run (~2-5 GB depending on model)

## Options

### 1. PyPI (pip install)

Publish to [pypi.org](https://pypi.org/) so users run one command.

```bash
pip install nihonsub
nihonsub listen
```

**Effort:** ~5 minutes setup  
**Users still need:** Python 3.11+, ffmpeg on PATH, VoiceMeeter (Windows)

**How to publish:**
```bash
# One-time: install build tools
pip install build twine

# Per-release:
python -m build
twine upload dist/*
# Enter PyPI API token
```

**Pros:**
- Standard for Python CLI tools
- 5 minutes to set up (PyPI account + API token)
- Auto-handles Python dependencies (torch, sounddevice, etc.)
- Versioning built in (`pip install nihonsub==0.2`)
- Cross-platform (same package everywhere)

**Cons:**
- User needs Python installed
- User needs ffmpeg separately
- User needs VoiceMeeter separately (Windows)
- Large pip download (torch + faster-whisper ~2 GB)

---

### 2. PyInstaller (single .exe)

Bundle Python + all dependencies into a standalone Windows executable.

```bash
# Build on Windows:
pyinstaller --onefile --name nihonsub src/__main__.py
```

**Effort:** Days to weeks (torch + faster-whisper often need manual PyInstaller hooks)  
**Users still need:** VoiceMeeter (Windows), ffmpeg either bundled or separate

**Key challenges with PyInstaller + torch:**
- PyInstaller has known issues with torch — needs hidden imports and custom hooks
- `--onefile` extracts to temp directory on each run — slow for large bundles
- Recommend `--onedir` instead for faster startup
- May need to exclude CUDA binaries to reduce size (CPU-only fallback)

**Pros:**
- No Python installation needed for the user
- All Python deps bundled (.exe can be 500 MB+)
- Familiar to Windows users
- Can bundle ffmpeg binary too

**Cons:**
- Build must happen on Windows (CI/CD needed)
- Large file size (~500 MB+ with torch)
- torch/faster-whisper PyInstaller quirks
- Antivirus false positives
- Updates require new .exe download
- Platform-specific (separate builds for Windows/Linux/macOS)

---

### 3. PyInstaller + Bundled ffmpeg

Same as above, but include ffmpeg binary in the package.

**Additional considerations:**
- ffmpeg adds ~60-100 MB
- ffmpeg is GPL-licensed — include attribution in the distribution
- Can download ffmpeg at build time from gyan.dev or BtbN
- Users still need VoiceMeeter (can't bundle virtual audio drivers)

---

### 4. Docker Image

Container with Python + nihonsub + ffmpeg pre-installed.

```bash
docker pull nihonsub/nihonsub
docker run --rm -v "$PWD/output:/output" nihonsub/nihonsub listen
```

**Pros:**
- No Python or ffmpeg installation
- Works identically across all OS
- Easy CI/CD (just push to Docker Hub)

**Cons:**
- Docker Desktop is ~5 GB install
- **Audio loopback passthrough is very fragile** — PulseAudio/WASAPI/ALSA routing through Docker containers is unreliable
- GPU passthrough for CUDA is complex (nvidia-docker)
- Not user-friendly for non-technical users
- Volume mounts needed for output files

**Verdict:** Not suitable for desktop audio capture. Good for server/CI use only.

---

### 5. Windows Store / Microsoft Store

Package as a Store app (MSIX format).

**Pros:**
- One-click install from Store
- Auto-updates
- Trusted source (no SmartScreen warnings)
- Can bundle ffmpeg as dependency

**Cons:**
- $19/year developer account fee
- Complex MSIX packaging requirements
- Store certification takes days
- Can't easily bundle PyTorch (MSIX has size limits and the store has package size limits around 10 GB for unpacked, 25 GB for packages; PyTorch alone is ~2 GB)
- VoiceMeeter still needs separate install
- Windows-only

**Verdict:** Overkill for this project's stage. Reconsider if nihonsub gains significant non-technical user base.

---

### 6. pipx

```bash
pipx install nihonsub
nihonsub listen
```

Same as PyPI but with automatic isolated environment management.

**Pros:** No venv management. Clean uninstall. Comes with modern Python on Windows.
**Cons:** Same as PyPI (needs Python, ffmpeg, VoiceMeeter). pipx is less known than pip.

---

## Recommendation

### Now
- Stick with `pip install -e .` from git

### When ready (Phase 1)
- **PyPI** — cheap, standard, removes biggest user friction (clone + venv)
- Add a `[project.scripts]` entry in `pyproject.toml` (already partially done)
- Create CI workflow to publish on tag push

### When ready (Phase 2)
- **PyInstaller** — for truly non-technical users
- Use `--onedir` (not `--onefile`) for torch compatibility
- Build in CI on Windows using GitHub Actions
- Distribute .exe via GitHub Releases
- Bundle ffmpeg from gyan.dev at build time

### Decision matrix

| Criterion | PyPI | PyInstaller | Docker | pipx |
|-----------|------|-------------|--------|------|
| Setup effort | 5 min | Days | Hours | 5 min |
| User needs Python | ✅ | ❌ | ❌ | ✅ |
| User needs ffmpeg | ✅ | 🟡 Can bundle | ❌ Bundled | ✅ |
| File size | 50 KB (pkg) | ~500 MB | ~5 GB | 50 KB |
| Cross-platform | ✅ | ❌ Per-OS | ✅ | ✅ |
| Normal-user friendly | 🟡 | ✅ | ❌ | 🟡 |
| Maintenance burden | Low | High | Medium | Low |

**Bottom line:** Start with PyPI. Add PyInstaller if/when there's demand from non-technical users.
