# Shadow Bot Functionality Checklist

This file tracks the development progress of Shadow Bot features.

## Core Voice Interaction

-   [x] Basic Setup (Raspberry Pi OS, Python)
-   [x] Microphone Input Setup
-   [x] Speaker Output Setup
-   [x] Speech-to-Text (STT) Integration (e.g., `speech_recognition`)
-   [x] Text-to-Speech (TTS) Integration (e.g., `gTTS`, `playsound`)
-   [x] Basic Command Loop (`listen -> process -> speak`)
-   [x] Simple Commands ("hello", "what time is it", "stop")
-   [x] Wake Word Detection (e.g., "Hey Shadow Bot")
-   [x] More Complex Command Parsing (understanding variations)
-   [x] Contextual Conversation (remembering previous interactions)
-   [x] Error Handling (microphone issues, API errors, unknown commands)

## Mobility (Optional)

-   [ ] Robot Chassis Assembly
-   [ ] Motor Controller Setup (e.g., L298N)
-   [ ] Motor Control Code (forward, backward, left, right, stop)
-   [ ] Voice Commands for Movement ("move forward", "turn left", etc.)

## Sensors & Actuators (Optional)

-   [ ] GPIO Library Integration (`RPi.GPIO` or `gpiozero`)
-   [ ] Distance Sensor Integration (e.g., HC-SR04)
-   [ ] Voice Commands for Sensors ("how far is the object?")
-   [ ] LED Control Integration
-   [ ] Voice Commands for LEDs ("turn on the light")
-   [ ] Other Sensors (Temperature, Light, etc.)

## Advanced Features (Optional)

-   [ ] Object Detection/Recognition (with Camera Module & AI libraries like OpenCV)
-   [ ] Remote Control Interface (Web server or App)
-   [ ] Personality/Response Variety
-   [ ] Learning Capabilities (adapting responses or actions)
-   [ ] Configuration File (`config.py` or similar) for settings

## Project Management

-   [x] Initial Plan (`plan.md`)
-   [x] Dependency Management (`requirements.txt`)
-   [x] Functionality Checklist (`functionality.md`)
-   [ ] Code Documentation (Docstrings, Comments)
-   [ ] Testing and Debugging Strategy
-   [ ] Version Control (e.g., Git)
