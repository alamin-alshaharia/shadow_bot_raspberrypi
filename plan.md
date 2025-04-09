# Project: Shadow Bot - Voice Controlled Raspberry Pi Robot

**Goal:** Create a Raspberry Pi-based robot named "Shadow Bot" that can understand and respond to voice commands.

**I. Hardware Requirements:**

1.  **Raspberry Pi:** Any recent model (Pi 3B+, Pi 4, Pi 5) should suffice.
2.  **Microphone:** A USB microphone is generally easiest to set up. Ensure compatibility with Raspberry Pi OS.
3.  **Speaker:** A small speaker connectable via the 3.5mm audio jack or USB/Bluetooth.
4.  **Power Source:** Adequate power supply for the Pi and any connected peripherals. A portable power bank if the robot needs to be mobile.
5.  **(Optional) Robot Chassis/Platform:** If Shadow Bot needs to move, you'll need a chassis, motors, motor controller (like L298N), and wheels.
6.  **(Optional) Additional Sensors/Actuators:** Depending on the commands you want it to execute (e.g., LEDs, distance sensor).

**II. Software Requirements:**

1.  **Operating System:** Raspberry Pi OS (previously Raspbian) - Lite or Desktop version.
2.  **Programming Language:** Python 3.
3.  **Core Libraries:**
    *   **Audio Input/Output:** Libraries like `PyAudio` or `sounddevice` to interact with the microphone and speaker.
    *   **Speech Recognition (STT - Speech-to-Text):**
        *   *Online Options (Easier setup, requires internet):* Google Cloud Speech-to-Text API (via libraries like `speech_recognition`), Wit.ai.
        *   *Offline Options (More complex setup, no internet needed):* PocketSphinx, Vosk, CMUSphinx.
    *   **Text-to-Speech (TTS):**
        *   *Online Options:* Google Text-to-Speech (gTTS library), AWS Polly.
        *   *Offline Options:* eSpeak, Festival, PicoTTS.
    *   **(Optional) GPIO Control:** `RPi.GPIO` or `gpiozero` library if controlling hardware like motors or LEDs.
    *   **(Optional) Wake Word Detection:** Libraries like `Porcupine` (requires account/license) or `Snowboy` (may be outdated) if you want the bot to listen only after hearing a specific word (e.g., "Hey Shadow Bot").

**III. Development Steps:**

1.  **Setup Raspberry Pi:** Install Raspberry Pi OS on an SD card and boot the Pi. Configure Wi-Fi/network access.
2.  **Hardware Connection & Configuration:**
    *   Connect the USB microphone and speaker.
    *   Test audio input and output using OS tools (like `arecord` and `aplay`).
    *   (If applicable) Assemble the robot chassis and connect motors/sensors to the Pi's GPIO pins via the motor controller.
3.  **Software Installation:**
    *   Update the OS: `sudo apt update && sudo apt upgrade`
    *   Install Python 3 and pip if not present.
    *   Install chosen STT, TTS, and audio libraries (e.g., `pip install SpeechRecognition PyAudio gTTS`).
    *   Install GPIO libraries if needed (`pip install RPi.GPIO gpiozero`).
4.  **Core Logic Development (`bot_brain.py`):**
    *   **Initialization:** Set up audio streams, initialize STT/TTS engines.
    *   **(Optional) Wake Word Listener:** Implement logic to constantly listen for the wake word.
    *   **Main Loop:**
        *   Once woken up (or if no wake word), listen for a command using the microphone.
        *   Capture audio data.
        *   Send audio data to the STT engine to get transcribed text.
        *   **Command Parsing:** Analyze the transcribed text to understand the user's intent.
        *   **Action Execution:** Based on the parsed command:
            *   Generate a verbal response using the TTS engine.
            *   Play the response through the speaker.
            *   (If applicable) Control GPIO pins (move motors, light LEDs, read sensors).
        *   Return to listening state.
5.  **Implement Specific Commands:** Define functions for actions Shadow Bot should perform based on recognized commands (e.g., "What time is it?", "Move forward", "Tell me a joke").
6.  **Testing & Refinement:** Test thoroughly in different noise environments. Tune microphone sensitivity, STT/TTS accuracy, and command recognition logic.

**IV. File Structure (Suggestion):**

```
shadow_bot_raspberrypi/
├── bot_brain.py         # Main application logic
├── requirements.txt     # Python dependencies
├── config.py            # Configuration (API keys, pins, etc.)
└── plan.md              # This plan document
