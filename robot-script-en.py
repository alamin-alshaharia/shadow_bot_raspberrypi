import speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play
import os
import time
from fuzzywuzzy import process
from collections import deque
import random
import re
import vosk
from datetime import datetime
import json
import glob
import requests

# Configuration Settings for Raspberry Pi
DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = {"en": {"tts": "en", "stt": "en-US"}}

# Audio settings optimized for Raspberry Pi
AUDIO_FILE = "response.mp3"  # Keep in current directory for better compatibility
PHRASE_TIME_LIMIT = 8  # Reduced for better responsiveness
ADJUST_NOISE_DURATION = 1  # Increased for better noise calibration
SAMPLE_RATE = 16000  # Standard sample rate for better compatibility

# Context settings
CONTEXT_MEMORY_SIZE = 5  # Reduced for better performance
context_memory = deque(maxlen=CONTEXT_MEMORY_SIZE)

# Vosk settings for Raspberry Pi
VOSK_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vosk-model-small-en-us-0.15")  # Path to optimized Vosk model
vosk_model = None

# Gemini API settings
GEMINI_API_KEY = None  # Set this in config file
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"

# Command templates
command_templates = {
    "en": {
        "greeting": ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"],
        "time": ["what time is it", "tell me the time", "current time", "time now"],
        "weather": ["what's the weather", "how's the weather", "weather forecast"],
        "joke": ["tell me a joke", "say something funny", "make me laugh"],
        "music": ["play music", "play song", "play something"],
        "news": ["tell me news", "what's happening", "news update"],
        "search": ["search for", "find out", "what is"],
        "reminder": ["set reminder", "remind me", "don't forget"],
        "calendar": ["what's on my calendar", "my schedule", "upcoming events"],
        "location": ["where is", "find location", "directions to"],
        "definition": ["what does mean", "define", "meaning of"],
        "synonym": ["synonyms for", "other words for"],
        "antonym": ["antonyms for", "opposite of"],
        "translate": ["translate to", "in other language", "how to say"],
        "calculate": ["what is", "calculate", "how much"],
        "convert": ["convert to", "change to", "in other unit"],
        "currency": ["exchange rate", "currency conversion", "how much in"],
        "temperature": ["temperature in", "weather in", "is it hot"],
        "alarm": ["set alarm", "wake me up", "alarm for"],
        "timer": ["set timer", "start timer", "countdown for"],
        "note": ["take note", "write down", "remember this"],
        "todo": ["add to todo", "todo list", "things to do"],
        "help": ["what can you do", "help me", "how to use"],
        "exit": ["stop", "exit", "quit", "goodbye", "bye"],
        "yes": ["yes", "yeah", "sure", "absolutely", "correct"],
        "no": ["no", "nope", "not really", "i don't think so"],
        "why": ["why", "why is that", "how come", "for what reason"],
        "how": ["how", "how to", "what's the way to"],
        "when": ["when", "what time", "at what time"],
        "where": ["where", "in which place", "at what location"],
        "who": ["who", "who is", "about who"],
        "what": ["what", "what is", "about what"],
        "which": ["which", "what kind", "what type"]
    }
}

# Responses
def get_response(command_type, context=None):
    responses = {
        "greeting": [
            "Hello! I'm here to help you.",
            "Hi there! How can I assist you today?",
            "Hey! Ready to help with anything you need."
        ],
        "time": [
            "The current time is {time}",
            "It's {time} right now",
            "The time is {time}"
        ],
        "weather": [
            "The weather is {weather} today",
            "It's {weather} outside",
            "Current weather conditions are {weather}"
        ],
        "joke": [
            "Why don't scientists trust atoms? Because they make up everything!",
            "What do you call a fake noodle? An impasta!",
            "Why did the scarecrow win an award? Because he was outstanding in his field!"
        ],
        "help": [
            "I can help with time, weather, jokes, searching information, setting reminders, and more!",
            "Try asking me about the time, weather, or any information you need.",
            "I can assist with tasks like setting reminders, searching for information, and more."
        ],
        "offline": [
            "I'm currently in offline mode.",
            "I can help you with basic tasks while offline.",
            "I'll be back online as soon as possible."
        ],
        "error": [
            "I'm sorry, I didn't understand that.",
            "Could you please rephrase your question?",
            "I'm having trouble understanding your request."
        ],
        "goodbye": [
            "Goodbye! Have a great day!",
            "See you later! Take care!",
            "Bye! Don't hesitate to ask if you need help again."
        ]
    }
    
    if command_type in responses:
        response = random.choice(responses[command_type])
        if context:
            response = response.format(**context)
        return response
    return "I'm here to help! What would you like to know?"

def speak(text, lang_code=DEFAULT_LANGUAGE):
    """Convert text to speech using gTTS optimized for Raspberry Pi"""
    try:
        tts = gTTS(text=text, lang=SUPPORTED_LANGUAGES[lang_code]["tts"])
        tts.save(AUDIO_FILE)
        
        # Try multiple playback methods with specific ALSA device
        try:
            # First try mplayer with specific ALSA device
            if os.system(f"mplayer -ao alsa:device=default {AUDIO_FILE} -quiet") != 0:
                # If mplayer fails, try aplay with specific device
                if os.system(f"aplay -D default {AUDIO_FILE}") != 0:
                    # If both fail, use pydub with specific device
                    audio = AudioSegment.from_mp3(AUDIO_FILE)
                    try:
                        # Try to use default ALSA device
                        play(audio, device='default')
                    except:
                        # Fallback to any available device
                        play(audio)
        except Exception as e:
            print(f"Playback error: {e}")
            # Final fallback to pydub without device specification
            audio = AudioSegment.from_mp3(AUDIO_FILE)
            play(audio)
        
        # Clean up
        if os.path.exists(AUDIO_FILE):
            os.remove(AUDIO_FILE)
            
    except Exception as e:
        print(f"Speech synthesis error: {e}")

def get_gemini_response(prompt):
    """Get response from Gemini AI"""
    if not GEMINI_API_KEY:
        return "Gemini API key not configured. Please set it in config file."
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GEMINI_API_KEY}"
    }
    
    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        response = requests.post(GEMINI_URL, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            return result["candidates"][0]["content"]["parts"][0]["text"]
        else:
            return "Sorry, I couldn't connect to Gemini AI at the moment."
    except Exception as e:
        print(f"Error with Gemini API: {e}")
        return "Sorry, I couldn't connect to Gemini AI at the moment."

def listen_for_audio(timeout=5, phrase_time_limit=PHRASE_TIME_LIMIT, adjust_noise=True):
    """Listen for audio input from microphone with ALSA configuration"""
    try:
        # Initialize recognizer with specific audio settings
        r = sr.Recognizer()
        device_index = None
        
        # Try to find the default ALSA device
        for index, name in enumerate(sr.Microphone.list_microphone_names()):
            if 'default' in name.lower() or 'alsa' in name.lower() or 'usb' in name.lower():
                device_index = index
                print(f"Using microphone device: {name}")
                break
        
        # Configure microphone with ALSA settings
        with sr.Microphone(device_index=device_index, sample_rate=SAMPLE_RATE) as source:
            print("Listening...")
            if adjust_noise:
                print("Adjusting for ambient noise...")
                r.adjust_for_ambient_noise(source, duration=ADJUST_NOISE_DURATION)
            
            # Configure recognition parameters
            r.energy_threshold = 4000
            r.dynamic_energy_threshold = True
            r.pause_threshold = 0.8
            r.non_speaking_duration = 0.5
            
            try:
                audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                return audio
            except sr.WaitTimeoutError:
                print("No speech detected within timeout")
                return None
    except Exception as e:
        print(f"Error in audio input: {e}")
        return None

def recognize_speech(audio):
    """Recognize speech from audio using Vosk for offline support"""
    if audio is None:
        return None, None
    
    try:
        if vosk_model:
            # Convert audio to format Vosk expects
            with open("temp.wav", "wb") as f:
                f.write(audio.get_wav_data())
            
            with open("temp.wav", "rb") as f:
                audio_data = f.read()
            
            rec = vosk.KaldiRecognizer(vosk_model, 16000)
            rec.AcceptWaveform(audio_data)
            result = rec.FinalResult()
            
            if result:
                data = json.loads(result)
                if "text" in data:
                    text = data["text"].strip()
                    if text:
                        return text, DEFAULT_LANGUAGE
        
        # Fallback to Google if Vosk fails
        r = sr.Recognizer()
        text = r.recognize_google(audio, language="en-US")
        return text, DEFAULT_LANGUAGE
    except Exception as e:
        print(f"Error in speech recognition: {e}")
        return None, None
    finally:
        if os.path.exists("temp.wav"):
            os.remove("temp.wav")

def match_command(command_text, lang_code):
    """Match command text to known command templates"""
    if not command_text or lang_code not in command_templates:
        return None, 0
    
    best_match = None
    best_score = 0
    
    for command_type, templates in command_templates[lang_code].items():
        for template in templates:
            score = process.extractOne(command_text.lower(), [template.lower()])[1]
            if score > best_score:
                best_match = command_type
                best_score = score
    
    return best_match, best_score

def process_command(command_text, lang_code):
    """Process the recognized command with Gemini integration"""
    if not command_text:
        speak("I didn't catch that. Could you please repeat?")
        return
    
    # Add to context memory
    context_memory.append({"text": command_text, "time": time.time()})
    
    command_type, confidence = match_command(command_text, lang_code)
    
    if confidence < 70:  # Adjust threshold as needed
        speak("I'm not sure I understood that. Could you please rephrase?")
        return
    
    # Handle different command types
    if command_type == "time":
        current_time = datetime.now().strftime("%I:%M %p")
        speak(get_response("time", {"time": current_time}))
    elif command_type == "greeting":
        speak(get_response("greeting"))
    elif command_type == "joke":
        speak(get_response("joke"))
    elif command_type == "help":
        speak(get_response("help"))
    elif command_type == "exit":
        speak(get_response("goodbye"))
        return False
    else:
        # Check internet connection
        try:
            import requests
            requests.get("https://www.google.com", timeout=5)
            
            # Use Gemini for complex queries
            if command_type in ["search", "definition", "synonym", "antonym", "translate", "weather"]:
                response = get_gemini_response(command_text)
                speak(response)
            else:
                speak("I'm online and ready to help!")
        except:
            speak(get_response("offline"))
    
    return True

def main():
    """Main function optimized for Raspberry Pi"""
    print("Starting English Voice Assistant for Raspberry Pi...")
    
    # Try to initialize audio
    try:
        # List available audio devices
        print("\nAvailable microphones:")
        for index, name in enumerate(sr.Microphone.list_microphone_names()):
            print(f"Microphone {index}: {name}")
        
        # Initialize microphone
        device_index = None
        for index, name in enumerate(sr.Microphone.list_microphone_names()):
            if 'default' in name.lower() or 'usb' in name.lower():
                device_index = index
                print(f"\nUsing microphone: {name}")
                break
        
        with sr.Microphone(device_index=device_index, sample_rate=SAMPLE_RATE) as source:
            print("\nAdjusting microphone for Raspberry Pi...")
            r = sr.Recognizer()
            r.adjust_for_ambient_noise(source, duration=ADJUST_NOISE_DURATION)
            r.energy_threshold = 4000
            r.dynamic_energy_threshold = True
        
        speak("Hello! I'm your English voice assistant. How can I help you today?")
    except Exception as e:
        print(f"\nError initializing audio: {e}")
        print("Please check your microphone connection and ALSA configuration.")
        return
    
    while True:
        try:
            # Listen for command
            audio = listen_for_audio()
            if audio:
                # Recognize speech
                command_text, lang_code = recognize_speech(audio)
                print(f"Heard: {command_text}")
                
                if command_text:
                    # Process command
                    if not process_command(command_text, lang_code):
                        break
        except KeyboardInterrupt:
            print("\nAssistant stopped.")
            break
        except Exception as e:
            print(f"Error: {e}")
            speak("I'm having some trouble. Please try again.")
            time.sleep(2)

if __name__ == "__main__":
    try:
        # Load Vosk model
        vosk_model = vosk.Model(VOSK_MODEL_PATH)
        print("Vosk model initialized successfully.")
    except Exception as e:
        print(f"Error loading Vosk model: {e}")
        vosk_model = None
    
    try:
        main()
    except Exception as e:
        print(f"Error in main: {e}")
        speak("I'm having some trouble starting up. Please check the logs.")
