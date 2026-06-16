# Windows Support

How nihonsub captures system audio on Windows for live listen mode.

## Capture Backend Selection

When `python -m src listen` runs on Windows, the system follows this decision tree:

```
Is ffmpeg installed and on PATH?
  ├── Yes → Try ffmpeg WASAPI loopback
  │         ├── Success → Use ffmpeg + WASAPI
  │         └── Fail (no WASAPI input support) →
  │                    ↓
  └── No  →
           ↓
Try sounddevice (PortAudio) 
  ├── Auto-detect loopback device
  │   Device priority:
  │   1. VoiceMeeter Output  (VB-Audio VoiceMeeter VAIO)
  │   2. CABLE Output        (VB-Cable virtual cable)
  │   3. Any device with "loopback" in name
  │   4. Any device with "Stereo Mix" in name
  │   5. First available input device
  │
  ├── Device found → Use sounddevice
  │
  └── No device → Raise error with setup instructions
```

### sounddevice Fallback

The sounddevice engine (PortAudio) is used when:
- ffmpeg is not installed
- ffmpeg was compiled without WASAPI input support (`Unknown input format: 'wasapi'`)

#### How it works
- Opens `sd.InputStream` with the detected device
- Captures in stereo (2 channels), averages to mono
- Resamples to 16 kHz via linear interpolation if needed
- Delivers float32 audio chunks to the VAD pipeline

#### Device Detection (`_find_sounddevice_device()`)
Scans all input devices and prioritizes by name keywords:
- `voicemeeter`, `voice meeter`, `vaio` — VoiceMeeter virtual output
- `cable` — VB-Cable virtual output
- `loopback` — WASAPI loopback devices exposed by PortAudio
- `stereo mix` — legacy stereo mix device

## Virtual Audio Device Options

### Option 1: VoiceMeeter (recommended)
Best for Bluetooth speaker setups. Lets you **hear** audio and **capture** it simultaneously.

- Free download: [vb-audio.com/Voicemeeter/](https://vb-audio.com/Voicemeeter/)
- Full guide: [docs/voicemeeter.md](../voicemeeter.md)

### Option 2: VB-Cable (simpler)
Single-purpose virtual cable. Routes audio from apps to a virtual output device for capture.

- Free download: [vb-audio.com/Cable/](https://vb-audio.com/Cable/)
- Set **CABLE Input** as your default playback device
- nihonsub captures from **CABLE Output**
- Downside: you won't hear audio (CABLE has no speaker output)

## Troubleshooting

### "No audio capture device found"
Check available input devices:
```bash
python -c "import sounddevice as sd; [print(f'{i}: {d[\"name\"]}') for i, d in enumerate(sd.query_devices()) if d['max_input_channels'] > 0]"
```
If nothing useful appears, install VoiceMeeter or VB-Cable.

### Audio meter shows 0% with audio playing
- Verify VoiceMeeter is running and shows VU meter movement
- Check B1 button is enabled on VoiceMeeter's Virtual Input channel
- Confirm Windows default playback device is set to VoiceMeeter Input or CABLE Input
- Restart nihonsub after changing audio devices

### ffmpeg WASAPI fails
If `ffmpeg -f wasapi -list_devices true -i dummy` gives `Unknown input format: 'wasapi'`:
- Your ffmpeg binary lacks WASAPI input support
- This is a build issue, not a code bug
- The tool falls back to sounddevice automatically
- To fix: download a full ffmpeg build from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) or `winget install ffmpeg`

### No transcription, but audio meter moves
- Audio is reaching the capture pipeline
- VAD may need tuning: lower `VAD_THRESHOLD` in `.env`
- Try a smaller model (`--model_size base`) for faster transcription
- Ensure audio content is Japanese (model is configured for `ja` by default)

## Version History

| Version | Changes |
|---------|---------|
| v0.2 | Initial Windows support: WASAPI + sounddevice fallback, VoiceMeeter detection, debug prints, audio meter |
