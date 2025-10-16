# Wispa 🎤

Fast, local voice-to-text for macOS using faster-whisper. Hold a hotkey to record, release to transcribe and inject text into any input field.

## Features

- **Ultra-fast transcription** with faster-whisper small model optimized for Apple Silicon
- **Hold-to-record** interface (Cmd+Shift+Space by default)
- **Local processing** - no internet required, completely private
- **Automatic text injection** into focused input field using AppleScript
- **Voice Activity Detection** to filter out silence

## Requirements

- macOS (Apple Silicon M1/M2/M3)
- Python 3.9+
- Microphone access

## Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Grant permissions:**
   - **Microphone Access**: You'll be prompted on first run
   - **Accessibility Access**: System Settings > Privacy & Security > Accessibility
     - Add Terminal (or your Python IDE) to the list

## Usage

**Run the script:**
```bash
python main.py
```

**To use:**
1. Hold `Cmd+Shift+Space` to start recording
2. Speak your text
3. Release the keys to stop and transcribe
4. Text will be automatically typed into the focused input field

**Exit:** Press `Ctrl+C` in the terminal

## Configuration

Edit `main.py` to customize:

```python
wispa = Wispa(
    model_size="small",  # Options: tiny, base, small, medium, large-v3
    hotkey="<cmd>+<shift>+<space>"  # Change hotkey combination
)
```

**Language:** Change line 115 from `language="en"` to your language code, or `None` for auto-detection

## Performance

On Apple Silicon M1:
- Model loading: ~2-5 seconds (one-time at startup)
- Transcription: ~1-3 seconds for typical voice clips (5-10 seconds of speech)
- Memory usage: ~500MB-1GB

## Troubleshooting

**"No audio recorded!"**
- Check microphone permissions in System Settings

**Text not injecting:**
- Grant Accessibility permissions to Terminal/IDE
- Try clicking into the input field before recording

**Slow transcription:**
- Use `tiny` or `base` model for faster results
- Reduce `cpu_threads` if CPU usage is too high

## Credits

Built with:
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) - Fast Whisper implementation
- [pynput](https://github.com/moses-palmer/pynput) - Keyboard listener
- [sounddevice](https://python-sounddevice.readthedocs.io/) - Audio recording
