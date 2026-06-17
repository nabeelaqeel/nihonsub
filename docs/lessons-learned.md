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

---

## 7. GTK GtkTextView consumes button-press-event, prevents window drag/resize

**Symptom**: `Gtk.Window` with `set_decorated(False)`, a read-only `Gtk.TextView` inside, and mouse event handlers for drag-move and drag-resize connected to the window: handlers never fire. Move, resize, and edge cursor detection all silently fail.

**Root cause**: `Gtk.TextView` handles `button-press-event` internally to position the cursor (even in non-editable mode). Its handler returns `True`, which **stops event propagation**. The event never reaches the parent `Gtk.Window`, so any handlers connected to the window's `button-press-event`, `button-release-event`, `motion-notify-event`, or `leave-notify-event` never fire.

Event propagation chain:
```
GtkTextView (consumes event, returns True) ✗
  → GtkScrolledWindow (never reached)
    → GtkWindow → handler never fires
```

**Fix**: Wrap the content in a `Gtk.EventBox` with `set_above_child(True)`:

```python
event_box = Gtk.EventBox()
event_box.set_above_child(True)
event_box.add_events(
    Gdk.EventMask.BUTTON_PRESS_MASK
    | Gdk.EventMask.BUTTON_RELEASE_MASK
    | Gdk.EventMask.POINTER_MOTION_MASK
    | Gdk.EventMask.LEAVE_NOTIFY_MASK
)
event_box.add(scroll)         # scroll = ScrolledWindow(text_view)
self.window.add(event_box)

event_box.connect("button-press-event", self._on_click)
event_box.connect("motion-notify-event", self._on_motion)
# etc.
```

`set_above_child(True)` places the EventBox's GDK window **above** all child GdkWindows in the z-order, so it receives all mouse events **first**, before the `GtkTextView` can consume them. The handler fires for every click on the content area.

**How to detect**: Add `print("CLICK:", event.x, event.y)` at the top of your `button-press-event` handler. If nothing prints when clicking the text view area, the event is being consumed by a child widget. Move the handler to a `Gtk.EventBox` parent to verify.

**GTK3 widget cursor inheritance**: When using `Gtk.EventBox` this way, cursors for resize (e.g. `GDK_TOP_SIDE`, `GDK_BOTTOM_RIGHT_CORNER`) are still set on the top-level window's GdkWindow via `window.get_window().set_cursor()`. Child GdkWindows inherit the parent's cursor if they don't set their own — but the EventBox creates its own GdkWindow, which may or may not propagate the cursor. On most setups this works; if it doesn't, set the cursor directly on the EventBox's GdkWindow instead.

---

## 8. GTK auto-scroll on Wayland fails with `scroll_to_iter()` and `scroll_to_mark()`

**Symptom**: Text is inserted into the `Gtk.TextView` correctly, manual scrolling works, but auto-scroll to the end never happens. The view stays showing old content while new text is added off-screen.

**Root cause**: On Wayland, GTK's `Gtk.TextView.scroll_to_iter()` and `Gtk.TextView.scroll_to_mark()` are unreliable:
1. **Timing issue**: The text view may not have re-laid-out when the scroll is called (even from an idle callback), so the iterator/mark points to an unmeasured position
2. **Iterator invalidation**: If called after buffer modifications, iterators become invalid and the scroll silently fails
3. **Platform difference**: X11 has more forgiving behavior; Wayland's compositing model exposes these edge cases

Attempts that failed:
```python
# ❌ Fails: iterator captured at add_caption time, buffer may change before callback fires
GLib.idle_add(self.text_view.scroll_to_iter, self.text_buffer.get_end_iter(), 0.0, True, 0.0, 1.0)

# ❌ Fails: lambda defers get_end_iter(), but scroll_to_iter() still unreliable on Wayland
GLib.idle_add(lambda: self.text_view.scroll_to_iter(
    self.text_buffer.get_end_iter(), 0.0, True, 0.0, 1.0
))

# ❌ Fails: even with place_cursor + scroll_to_mark, still unreliable on Wayland
GLib.idle_add(lambda: (
    self.text_buffer.place_cursor(self.text_buffer.get_end_iter()),
    self.text_view.scroll_to_mark(self.text_buffer.get_insert(), 0.0, True, 0.0, 1.0),
))

# ❌ Fails: using text_view's adjustment (not the ScrolledWindow's)
adj = self.text_view.get_vadjustment()  # Wrong adjustment
```

**Fix**: Use the **ScrolledWindow's adjustment** directly instead of GTK's text-positioning APIs:

```python
def _setup_ui(self):
    # ... create widgets ...
    self.scroll = Gtk.ScrolledWindow()
    self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    self.scroll.add(event_box)
    self.window.add(self.scroll)

def _scroll_to_end(self):
    adj = self.scroll.get_vadjustment()  # ScrolledWindow's adjustment
    if adj:
        # Scroll to bottom: set value to (total_height - visible_height)
        adj.set_value(adj.get_upper() - adj.get_page_size())
    return False

def add_caption(self, text: str):
    # ... insert text and delete old lines ...
    GLib.idle_add(self._scroll_to_end)
```

**Why this works**:
- The `ScrolledWindow` is the widget that actually manages the viewport
- Its `Gtk.Adjustment` is the canonical scroll position
- Setting the adjustment value directly bypasses GTK's text view layout/iterator logic
- This is a **platform-independent, timing-independent** approach
- Works reliably on both X11 and Wayland

**How to detect**: 
1. Add text to the window and watch if it stays at the old position (no auto-scroll)
2. Verify manual scroll works (user can drag scrollbar or use mouse wheel)
3. If auto-scroll fails but manual works, the issue is with the scrolling API, not the widget setup
4. Test on both X11 and Wayland to confirm the platform difference

**Key insight**: Always use the container's adjustment, not the child widget's. The `ScrolledWindow` owns the adjustment; the `TextView` is just a client of that adjustment.
