# Lessons Learned

This document catalogs bugs and design mistakes encountered during development, along with their root causes and fixes.

---

## 1. `PULSE_SOURCE` env var ignored by `sounddevice` on PipeWire

**Symptom**: Live capture produced all-zero audio chunks (level = 0.0). No transcription appeared.

**Root cause**: Setting `os.environ["PULSE_SOURCE"]` before creating a `sounddevice.InputStream(device="pulse")` does NOT route audio through the monitor source. The PulseAudio backend in PortAudio/sounddevice uses PulseAudio's internal default source override mechanism, which doesn't work reliably with PipeWire's PulseAudio compatibility layer.

**Fix**: Replace `sounddevice` with an `ffmpeg` subprocess that captures directly from the monitor source:

```python
subprocess.Popen([
    "ffmpeg",
    "-f", "pulse",
    "-i", monitor_name,       # e.g. alsa_output...sink.monitor
    "-ac", "1",               # mono
    "-ar", "16000",           # 16kHz
    "-f", "f32le",            # raw float32
    "pipe:1",                 # stdout
])
```

This is more reliable because ffmpeg handles PulseAudio directly, and we just read the raw float32 samples from its stdout.

**How to detect**: Add a quick logging check — print `np.abs(chunk).mean()` from the capture callback. If it's consistently 0.0, the capture source isn't delivering audio.

**Note**: The `-sample_fmt f32le` option does not exist in ffmpeg. Use `-f f32le` which sets both the container and sample format.

---

## 2. silero-vad v6 rejects 480-sample chunks

**Symptom**: VAD thread crashed silently with `ValueError: Input audio chunk is too short`. No transcription appeared.

**Root cause**: silero-vad v6 requires `sample_rate / chunk_length > 31.25`. At 16kHz:
- 480 samples → 16000/480 = 33.33 > 31.25 → too short → **crash**
- 512 samples → 16000/512 = 31.25 == 31.25 → **OK**

The condition is **strictly greater than** 31.25, so 512 is the minimum valid frame size at 16kHz.

**Fix**: Changed `FRAME_SIZE` from 480 (30ms) to 512 (32ms).

**How to detect**: Wrap the VAD processing in a `try/except` and log the error. Without this, it crashes silently in a daemon thread.

---

## 3. silero-vad v6 has no `process_chunk()` method

**Symptom**: `AttributeError: 'RecursiveScriptModule' object has no attribute 'process_chunk'` — but only in the daemon thread, so it silently killed the VAD pipeline.

**Root cause**: silero-vad v6 returns a TorchScript `RecursiveScriptModule` from `load_silero_vad()`. The correct API is to call it directly — it's a callable module.

- Wrong: `vad.process_chunk(tensor, sr)` → AttributeError
- Correct: `vad(tensor, sr).item()` → returns float probability

**Fix**: Replaced `vad.process_chunk(tensor, 16000)` with `vad(tensor, 16000).item()`.

**How to detect**: Check the VAD model type with `print(type(vad).__name__)`. If it's `RecursiveScriptModule`, the callable API (`vad(tensor, sr)`) is correct.

---

## 4. Daemon threads swallow exceptions silently

**Symptom**: No error output when VAD or worker threads crash. The application appears to run but produces no results.

**Root cause**: Python daemon threads (`threading.Thread(daemon=True)`) exit silently on unhandled exceptions. The main thread never sees the error because daemon threads don't propagate exceptions and don't block process exit.

**Fix**: Added `try/except` around all thread loop bodies. Errors are:
1. Logged to stderr via `traceback.print_exc()`
2. Pushed to the display queue as error entries (visible in the terminal)

```python
def _thread_loop(self):
    while self.running:
        try:
            # ... work ...
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.display_queue.put({"text": f"[error: {e}]", ...})
```

**How to detect**: Always add error handling in daemon threads. A good practice is to use a `threading.Thread` subclass that captures and re-raises exceptions, or at minimum wrap the loop body in `try/except`.

---

## 5. ffmpeg `-sample_fmt` doesn't exist

**Symptom**: `ffmpeg` returns code 234 with `Invalid sample format 'f32le'`.

**Root cause**: `-sample_fmt` is not a valid ffmpeg option for raw PCM output. The correct way to set the output format is `-f f32le`, which implies both the container and sample format.

**Fix**: Removed `-sample_fmt f32le`. Use only `-f f32le`.

```python
# Wrong
["ffmpeg", ..., "-sample_fmt", "f32le", "-f", "f32le", "pipe:1"]

# Correct  
["ffmpeg", ..., "-f", "f32le", "pipe:1"]
```

---

## 6. torch.Tensor dtype mismatches with silero-vad

**Symptom**: `RuntimeError: expected scalar type Double but found Float` when calling the VAD model.

**Root cause**: silero-vad v6's TorchScript model stores its STFT weights as float32. If the input tensor is float64 (e.g., from `np.sin()` returning float64 by default), the convolution operation fails with a dtype mismatch.

**Fix**: Always convert tensors to `float()` before passing to the VAD model:

```python
tensor = torch.from_numpy(chunk).unsqueeze(0).float()
prob = vad(tensor, 16000).item()
```

**How to detect**: Check the dtype of the input tensor before calling the model. If it's not float32, convert it.
