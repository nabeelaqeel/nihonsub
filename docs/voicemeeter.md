# VoiceMeeter Setup for nihonsub (Windows)

This guide explains how to use [VoiceMeeter](https://vb-audio.com/Voicemeeter/) (free virtual audio mixer) to capture system audio with nihonsub on Windows, especially when your hardware (e.g. Bluetooth speakers) doesn't support standard WASAPI loopback.

## Why VoiceMeeter?

On Windows, nihonsub needs to **hear** your system audio and **capture** it for transcription simultaneously. Most audio devices can only do one or the other:

| Setup | Can hear? | Can capture? |
|---|---|---|
| Speakers/headphones directly | Yes | No |
| WASAPI loopback (standard) | No (muted) | Yes |
| **VoiceMeeter** (this guide) | **Yes** | **Yes** |

VoiceMeeter acts as a virtual mixing desk: your audio goes into it, and it sends the audio to **both** your speakers (so you can hear) **and** a virtual output device (so nihonsub can capture).

## Prerequisites

- Windows 10 or 11
- [VoiceMeeter](https://vb-audio.com/Voicemeeter/) (free) or [VoiceMeeter Banana](https://vb-audio.com/Voicemeeter/banana.htm) (donationware)
- nihonsub installed (`pip install -e .`)
- Python and sounddevice installed (included with nihonsub)

## Installation

1. Download the **standard VoiceMeeter** (free) from [vb-audio.com/Voicemeeter](https://vb-audio.com/Voicemeeter/)
2. Run the installer and follow the prompts
3. **Restart Windows** — this ensures the virtual audio drivers register correctly

After restart, VoiceMeeter adds two virtual audio devices to your system:
- **VoiceMeeter Input** (VB-Audio VoiceMeeter VAIO) — a playback device. Set this as your default.
- **VoiceMeeter Output** (VB-Audio VoiceMeeter VAIO) — a recording/capture device. nihonsub captures from this.

## Configuration

### Step 1: Set VoiceMeeter Input as your default playback device

1. Right-click the **speaker icon** in your system tray → **Sound settings**
2. Under **Output**, select **"VoiceMeeter Input (VB-Audio VoiceMeeter VAIO)"**
3. *(Optional)* Do the same under **App volume and device preferences** for individual apps

Now all system audio routes through VoiceMeeter.

### Step 2: Configure VoiceMeeter routing

1. Launch **VoiceMeeter** from the Start Menu
2. You'll see a mixing console with several sections. The key routing:

```
[Virtual Input]  ← system audio comes in here (from VoiceMeeter Input)
     ↓
[Hardware Out A1]  → your speakers/headphones  ← you hear audio
[Virtual Out B1]   → VoiceMeeter Output device  ← nihonsub captures from here
```

3. Make sure **B1** is enabled (click the **B1** button under the Virtual Input channel strip)
4. Make sure **A1** is enabled and shows your physical audio device (select it from the dropdown if needed)

Your VoiceMeeter window should look roughly like:
```
┌─────────────────────────────────────────┐
│  Virtual Input  │   Hardware Input 1    │
│  [A1] [B1]      │   [A1] [B2]          │
│  ───█───         │   ───█───            │
│  M S    ◄        │   M S    ◄           │
└─────────────────────────────────────────┘
         │                    │
         ▼                    ▼
   [Physical Out A1]    [Virtual Out B1]
     (your speakers)     (for nihonsub)
```

### Step 3: Test audio flow

1. Play something — YouTube, a music player, an anime episode
2. In VoiceMeeter, you should see the **Virtual Input** VU meter moving (green bars)
3. You should hear audio through your speakers
4. If both work, VoiceMeeter is correctly routing audio

## Using with nihonsub

Run live listen normally — it should auto-detect the VoiceMeeter Output device:

```bash
python -m src listen
```

You should see output like:
```
Initializing live listening (model: small)...
Capture engine: sounddevice (device 2)
Using sounddevice capture device: VoiceMeeter Output (VB-Audio VoiceMeeter VAIO) (index 2)
Listening... (Ctrl+C to stop)
```

The audio level meter in the header (`Audio: [██████░░░░] 50%`) should move when audio plays.

## Troubleshooting

### "No audio capture device found"
Run this to list available input devices:
```bash
python -c "import sounddevice as sd; [print(f'{i}: {d[\"name\"]}') for i, d in enumerate(sd.query_devices()) if d['max_input_channels'] > 0]"
```
If VoiceMeeter Output doesn't appear, try reinstalling VoiceMeeter and restarting.

### Audio meter shows 0% even with audio playing
- Verify VoiceMeeter is running and shows VU meter movement on Virtual Input
- Check that **B1** is enabled (clicked/lit up) on the Virtual Input channel
- Check Windows Sound settings → VoiceMeeter Input is set as the default device
- Restart nihonsub after changing VoiceMeeter settings

### Hearing audio but no transcription
- The audio meter should show movement. If it does, VAD or whisper may need tuning
- Try a louder source (higher volume = higher VAD detection rate)
- Check if the language being spoken is Japanese (faster-whisper is configured for `ja`)

### Audio crackling or stuttering
VoiceMeeter adds a small buffer delay. If you hear crackling:
- In VoiceMeeter: **Menu** → **System Settings / Options** → increase **Buffer size** (e.g. 512 → 1024)
- This may increase latency but reduces crackling

## Alternative: VB-Cable (simpler)

If you don't need the mixing features of VoiceMeeter, [VB-Cable](https://vb-audio.com/Cable/) is a simpler alternative:

1. Install VB-Cable
2. Set **CABLE Input** as your Windows default playback device
3. nihonsub auto-detects **CABLE Output** as the capture source
4. **Downside**: You won't hear audio (CABLE is purely virtual, no speaker output)

To hear audio with VB-Cable, use Windows **Sound Control Panel** → **Recording** tab → **Stereo Mix** (if available) instead.

---

**Introduced in:** v0.2 (`feat/windows-support` branch)  
**See also:** [features/windows-support.md](features/windows-support.md), [releases/v0.2.md](releases/v0.2.md)
