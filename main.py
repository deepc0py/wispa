#!/usr/bin/env python3
"""
Wispa - Fast local voice-to-text for macOS
Hold Command+Option+Control to record, release to transcribe and inject text
"""

import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from pynput import keyboard


# ============================================================================
# CONFIGURATION - Edit these settings to customize Wispa
# ============================================================================

# Hotkey combination - Set which keys to use (True = required, False = not used)
USE_CMD = True  # Command key
USE_OPTION = True  # Option/Alt key
USE_CTRL = True  # Control key
USE_SHIFT = False  # Shift key

# Model settings
MODEL_SIZE = "small"  # Options: "tiny", "base", "small", "medium", "large-v3"
LANGUAGE = "en"  # Language code (e.g., "en", "es", "fr") or None for auto-detect

# Audio feedback sounds (macOS system sounds)
# Options: Tink, Pop, Basso, Blow, Bottle, Frog, Funk, Glass, Hero, Morse, Ping, Purr, Sosumi, Submarine
START_SOUND = "Tink"  # Sound when recording starts
STOP_SOUND = "Pop"  # Sound when recording stops

# ============================================================================


class Wispa:
    def __init__(self, model_size="small", language="en"):
        """Initialize Wispa with faster-whisper model."""
        self.language = language

        print(f"Loading {model_size} model... (this may take a few seconds)")

        # Optimize for Apple Silicon M1
        self.model = WhisperModel(
            model_size,
            device="cpu",  # M1 uses CPU with Metal acceleration
            compute_type="int8",  # Fast quantized inference
            cpu_threads=4,  # Optimize for M1 performance cores
        )

        # Build hotkey description
        keys = []
        if USE_CMD:
            keys.append("Command")
        if USE_OPTION:
            keys.append("Option")
        if USE_CTRL:
            keys.append("Control")
        if USE_SHIFT:
            keys.append("Shift")
        hotkey_desc = "+".join(keys)

        print("Model loaded! Ready to transcribe.")
        print(f"Hold {hotkey_desc} to record, release to transcribe.\n")

        # Recording state
        self.is_recording = False
        self.audio_data = []
        self.sample_rate = 16000  # Whisper expects 16kHz
        self.stream = None

    def start_recording(self):
        """Start recording audio."""
        self.is_recording = True
        self.audio_data = []

        print("[REC] Recording... (release key to transcribe)")

        def audio_callback(indata, frames, time, status):
            """Callback to capture audio chunks."""
            if status:
                print(f"Audio status: {status}")
            self.audio_data.append(indata.copy())

        # Start audio stream FIRST, before the beep
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype=np.float32,
            callback=audio_callback,
        )
        self.stream.start()

        # Audio feedback - play system beep (non-blocking)
        subprocess.Popen(
            ["afplay", f"/System/Library/Sounds/{START_SOUND}.aiff"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def stop_recording(self):
        """Stop recording and transcribe."""
        if not self.is_recording:
            return

        self.is_recording = False

        # Stop audio stream
        if self.stream:
            self.stream.stop()
            self.stream.close()

        # Audio feedback - different sound for stop
        subprocess.run(
            ["afplay", f"/System/Library/Sounds/{STOP_SOUND}.aiff"], check=False
        )

        print("[STOP] Stopped recording, transcribing...")

        # Process audio
        if not self.audio_data:
            print("No audio recorded!")
            return

        # Combine audio chunks
        audio = np.concatenate(self.audio_data, axis=0).flatten()

        # Debug: show audio info
        duration = len(audio) / self.sample_rate
        max_amplitude = np.max(np.abs(audio))
        print(f"[DEBUG] Recorded {duration:.2f}s, max amplitude: {max_amplitude:.4f}")

        # Save to temporary WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name

        try:
            # Write WAV file
            with wave.open(temp_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self.sample_rate)
                # Convert float32 to int16
                audio_int16 = (audio * 32767).astype(np.int16)
                wf.writeframes(audio_int16.tobytes())

            # Transcribe with faster-whisper
            segments, info = self.model.transcribe(
                temp_path,
                beam_size=1,  # Faster, less accurate beam search
                language=self.language,  # Use configured language
                vad_filter=False,  # Disable VAD to see if it's filtering everything
            )

            print(
                f"[DEBUG] Language detected: {info.language}, probability: {info.language_probability:.2f}"
            )

            # Get transcription text
            text = " ".join([segment.text.strip() for segment in segments])

            if text:
                print(f" Transcribed: {text}")
                self.inject_text(text)
            else:
                print("No speech detected!")

        finally:
            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)

    def inject_text(self, text):
        """Inject text into focused input using AppleScript."""
        # Add a space after the text for continuous dictation
        text_with_space = text + " "

        # Escape special characters for AppleScript
        escaped = text_with_space.replace("\\", "\\\\").replace('"', '\\"')

        script = f'tell application "System Events" to keystroke "{escaped}"'

        try:
            subprocess.run(
                ["osascript", "-e", script], check=True, capture_output=True, text=True
            )
        except subprocess.CalledProcessError as e:
            print(f"Failed to inject text: {e.stderr}")

    def run(self):
        """Run the keyboard listener loop."""
        print("Wispa is running in the background...")
        print("Press Ctrl+C to exit.\n")

        # Track key state for hold-to-record
        cmd_pressed = False
        option_pressed = False
        ctrl_pressed = False
        shift_pressed = False

        def on_press(key):
            nonlocal cmd_pressed, option_pressed, ctrl_pressed, shift_pressed

            # Check for modifier keys
            if (
                key == keyboard.Key.cmd
                or key == keyboard.Key.cmd_l
                or key == keyboard.Key.cmd_r
            ):
                cmd_pressed = True
            elif (
                key == keyboard.Key.alt
                or key == keyboard.Key.alt_l
                or key == keyboard.Key.alt_r
            ):
                option_pressed = True
            elif (
                key == keyboard.Key.ctrl
                or key == keyboard.Key.ctrl_l
                or key == keyboard.Key.ctrl_r
            ):
                ctrl_pressed = True
            elif (
                key == keyboard.Key.shift
                or key == keyboard.Key.shift_l
                or key == keyboard.Key.shift_r
            ):
                shift_pressed = True

            # Check if all required keys are pressed
            all_pressed = (
                (not USE_CMD or cmd_pressed)
                and (not USE_OPTION or option_pressed)
                and (not USE_CTRL or ctrl_pressed)
                and (not USE_SHIFT or shift_pressed)
            )

            # Start recording when all required keys are pressed
            if all_pressed and not self.is_recording:
                self.start_recording()

        def on_release(key):
            nonlocal cmd_pressed, option_pressed, ctrl_pressed, shift_pressed

            # Track key releases
            if (
                key == keyboard.Key.cmd
                or key == keyboard.Key.cmd_l
                or key == keyboard.Key.cmd_r
            ):
                cmd_pressed = False
            elif (
                key == keyboard.Key.alt
                or key == keyboard.Key.alt_l
                or key == keyboard.Key.alt_r
            ):
                option_pressed = False
            elif (
                key == keyboard.Key.ctrl
                or key == keyboard.Key.ctrl_l
                or key == keyboard.Key.ctrl_r
            ):
                ctrl_pressed = False
            elif (
                key == keyboard.Key.shift
                or key == keyboard.Key.shift_l
                or key == keyboard.Key.shift_r
            ):
                shift_pressed = False

            # Check if all required keys are still pressed
            all_pressed = (
                (not USE_CMD or cmd_pressed)
                and (not USE_OPTION or option_pressed)
                and (not USE_CTRL or ctrl_pressed)
                and (not USE_SHIFT or shift_pressed)
            )

            # Stop recording when any required key is released
            if self.is_recording and not all_pressed:
                self.stop_recording()

        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()


if __name__ == "__main__":
    try:
        wispa = Wispa(model_size=MODEL_SIZE, language=LANGUAGE)
        wispa.run()
    except KeyboardInterrupt:
        print("\n\nWispa stopped.")
    except Exception as e:
        print(f"\nError: {e}")
        raise
