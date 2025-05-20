import speech_recognition as sr
from gtts import gTTS
# import playsound # Replacing with pydub
import os
import time
# import config # No longer needed, config is inline
from fuzzywuzzy import process
from collections import deque
import random
import re  # Import regex for name extraction
# from langdetect import detect, LangDetectException  # Import langdetect
import google.generativeai as genai  # Gemini API
from pydub import AudioSegment  # For audio playback
from pydub.playback import play  # For audio playback
import tempfile  # For temporary audio files
import json
import logging
from datetime import datetime
import threading
import queue
import warnings

# Suppress ALSA warnings
warnings.filterwarnings("ignore", category=UserWarning)
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

# --- Configuration Settings (formerly config.py) ---

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('shadow_bot.log'),
        logging.StreamHandler()
    ]
)

# Audio Configuration
SAMPLE_RATE = 16000  # Standard sample rate for speech recognition
AUDIO_DEVICE = None  # Will be set to default device

def get_default_audio_device():
    """Get the default audio device configuration."""
    try:
        import alsaaudio
        devices = alsaaudio.pcms(alsaaudio.PCM_CAPTURE)
        if devices:
            return devices[0]  # Return first available device
        return None
    except:
        return None

def initialize_audio():
    """Initialize audio system with proper configuration."""
    try:
        # Try to get default audio device
        device = get_default_audio_device()
        if device:
            logging.info(f"Using audio device: {device}")
            return True
        else:
            logging.warning("No specific audio device found, using default")
            return True
    except Exception as e:
        logging.error(f"Error initializing audio: {e}")
        return False

# Supported Languages
# Define the languages the bot can understand and speak
# Format: { "short_code": {"tts": "google_tts_code", "stt": "google_stt_code"} }
SUPPORTED_LANGUAGES = {
    "en": {"tts": "en", "stt": "en-US"}  # English
}
DEFAULT_LANGUAGE = "en"

# Temporary file path for TTS audio output
AUDIO_FILE = "response.mp3"

# Wake word settings
# WAKE_WORD_ENABLED = True
# WAKE_WORDS = ["hey shadow", "shadow", "hey assistant", "assistant"]
# WAKE_WORD_LANG_STT = "en-US"
# WAKE_WORD_TIMEOUT = 15

# Command parsing settings
COMMAND_SIMILARITY_THRESHOLD = 0.65  # Slightly reduced threshold for better matching

# Contextual conversation settings
CONTEXT_MEMORY_SIZE = 8  # Increased memory size for better context

# Error handling settings
MAX_RETRY_ATTEMPTS = 3  # Maximum number of retries for failed operations
RETRY_DELAY = 2  # Seconds to wait between retries

# --- Microphone Listening Settings ---
DYNAMIC_ENERGY_THRESHOLD = True
PAUSE_THRESHOLD = 0.5  # Reduced for more natural conversation flow
PHRASE_TIME_LIMIT = 20  # Increased for longer phrases
ADJUST_NOISE_DURATION = 2  # Increased for better noise adjustment

# Add these new conversation settings
CONVERSATION_SETTINGS = {
    "max_silence": 5,  # Maximum seconds of silence before prompting
    "follow_up_chance": 0.4,  # Increased chance of follow-up questions
    "context_window": 5,  # Number of previous interactions to consider
    "response_delay": 0.3  # Delay between responses for more natural flow
}

# --- Gemini API Configuration ---
# WARNING: Storing API keys directly in code is insecure. Consider environment variables.
GEMINI_API_KEY = "AIzaSyBY88kNHfPUqauW2z5wu5-qnBv1Kr4d86s" 
try:
    genai.configure(api_key=GEMINI_API_KEY)
    # Using gemini-1.5-flash as gemini-2.0-flash might not be a valid model name yet
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
    print("Gemini model initialized successfully.")
except Exception as e:
    print(f"Error initializing Gemini API: {e}")
    gemini_model = None  # Set model to None if initialization fails

# --- Bot Logic (formerly bot_brain.py) ---

# --- Context Memory ---
context_memory = deque(maxlen=CONTEXT_MEMORY_SIZE)  # Use variable directly

# --- Bilingual Data Structures ---

# Command Templates (English only)
command_templates = {
    "en": {
        "greeting": ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening", "morning",
                     "afternoon", "evening"],
        "time": ["what time is it", "tell me the time", "current time", "time now", "what's the time", "got the time"],
        "name": ["what's your name", "who are you", "your name", "tell me your name", "introduce yourself",
                 "what should I call you"],
        "joke": ["tell me a joke", "say something funny", "make me laugh", "joke", "know any jokes", "be funny",
                 "another joke"],
        "exit": ["stop", "exit", "quit", "goodbye", "bye", "shut down", "turn off", "sleep", "that's all"],
        "how_are_you": ["how are you", "how are you doing", "how's it going", "how do you feel", "are you okay",
                        "you good", "how's everything"],
        "thanks": ["thank you", "thanks", "appreciate it", "that's helpful", "great job", "well done", "good job"],
        "weather": ["what's the weather", "how's the weather", "is it raining", "temperature today", "forecast",
                    "weather like"],
        "capabilities": ["what can you do", "help", "list commands", "your abilities", "what are you capable of",
                         "features", "commands", "options"],
        "about_you": ["tell me about yourself", "what are you", "are you a robot", "are you human", "are you ai",
                      "what kind of ai"],
        "user_name": ["my name is", "call me", "i am", "i'm called", "name's", "the name is"],
        "how_made": ["how were you made", "who made you", "who created you", "your creator", "how were you created",
                     "what are you made of"],
        "yes": ["yes", "yeah", "sure", "absolutely", "correct", "that's right", "yep", "ok", "okay", "right", "yup",
                "of course"],
        "no": ["no", "nope", "not really", "i don't think so", "negative", "not at all", "nah", "never"],
        "why": ["why", "why is that", "how come", "for what reason", "explain why", "what's the reason"],
        "what_else": ["what else", "tell me more", "continue", "go on", "anything else", "more information",
                      "like what", "such as"],
        "ask_question": ["ask me a question", "ask me something", "ask me", "question me", "quiz me"],
        "answer_question": ["the answer is", "it is", "it's", "that would be", "i think it's"]
    }
}

# Responses (English only)
responses = {
    "en": {
        "greeting": [
            "Hello! How can I help you today?", "Hi there! What can I do for you?",
            "Hey! Great to hear from you.", "Greetings! I'm here to assist you.",
            "Hello! Ready to help with whatever you need."
        ],
        "greeting_repeat": "Hello again! You seem friendly today. What can I help you with?",
        "greeting_followup": " How are you doing today?",
        "how_are_you": [
            "I'm doing well, thanks for asking! How about you?", "I'm functioning perfectly! How's your day going?",
            "All systems running smoothly! How are you?", "I'm great! Thanks for checking. How's your day?"
        ],
        "how_are_you_resp_glad": "That's wonderful to hear! What can I help you with today?",
        "how_are_you_resp_sorry": "I'm sorry to hear that. Is there anything I can do to help make your day better?",
        "time": "It's currently {current_time}.",
        "time_repeat": "The time is still {current_time}. Time flies when you're having fun!",
        "name": "I'm Shadow, your AI assistant. I'm here to help and chat with you.",
        "name_repeat": "As I mentioned, I'm Shadow. I'm your friendly AI assistant!",
        "name_ask": "I'm Shadow, your AI assistant. I'd love to know your name too! What should I call you?",
        "user_name_confirm": "It's great to meet you, {name}! How can I help you today?",
        "user_name_fail": "I didn't quite catch your name. Could you tell me again?",
        "joke": [
            "Why don't scientists trust atoms? Because they make up everything!",
            "What do you call a bear with no teeth? A gummy bear!",
            "Why did the scarecrow win an award? Because he was outstanding in his field!",
            "What do you call a fish wearing a bowtie? So-fish-ticated!",
            "Why don't eggs tell jokes? They'd crack each other up!",
            "What do you call a sleeping bull? A bulldozer!",
            "Why did the math book look sad? Because it had too many problems!",
            "What do you call a fake noodle? An impasta!",
            "Why did the cookie go to the doctor? Because it was feeling crumbly!",
            "What do you call a dinosaur that crashes his car? Tyrannosaurus wrecks!"
        ],
        "joke_ask_more": " Would you like to hear another one?",
        "joke_out": "Looks like I've used up all my best jokes! Give me a moment to think of some new ones.",
        "thanks": [
            "You're welcome! What else can I help you with?", "Glad I could help! Need anything else?",
            "Happy to assist! Let me know if you need anything else.", "Anytime! That's what I'm here for.",
            "My pleasure! What else would you like to know?"
        ],
        "capabilities": [
            "I can help you with various tasks! I can tell time, tell jokes, chat with you, answer questions, and remember our conversations. What would you like to try?",
            "I'm your AI assistant that can have conversations, tell time, share jokes, remember context, and help answer your questions. How can I assist you?",
            "I can understand natural language, remember our chat history, tell jokes, and respond to various commands. I also use AI to help answer questions you might have. What interests you?"
        ],
        "about_you": [
            "I'm Shadow, an AI assistant designed to be helpful and friendly. I can understand natural language and remember our conversations to provide better assistance.",
            "I'm an AI assistant named Shadow. I was created to help with tasks and have engaging conversations. I learn from our interactions to serve you better.",
            "I'm Shadow, your AI companion. I use advanced language processing to understand and chat with you, and I remember our conversations to provide more personalized responses."
        ],
        "how_made": [
            "I was created using Python with advanced AI technologies for natural language processing. I use speech recognition to understand you and text-to-speech to respond.",
            "I'm built with Python and various AI technologies that help me understand and process language naturally. I'm designed to learn and improve from our conversations.",
            "I'm powered by Python and AI, using speech recognition and natural language processing to understand and communicate effectively."
        ],
        "weather": [
            "I don't have access to real-time weather data yet, but I'd be happy to help with something else!",
            "I can't check the weather right now, but I'm working on adding that feature. What else can I help you with?",
            "While I can't give you weather updates, I can assist you with many other things. What would you like to know?"
        ],
        "exit": [
            "Goodbye! It was great chatting with you.", "Take care! Have a wonderful day.",
            "Goodbye! I'll be here when you need me again.", "See you later! It was a pleasure talking with you.",
            "Goodbye! Thanks for the great conversation."
        ],
        "yes_generic": "Great! What would you like to discuss?",
        "no_generic": "Alright. Is there something else you'd like to talk about?",
        "why": [
            "That's a great question! I'm designed to respond this way to be more helpful and natural.",
            "I'm programmed to provide the most relevant and helpful information I can based on our conversation.",
            "Good question! My responses come from my training and our conversation context to give you the best possible assistance."
        ],
        "what_else": [
            "I can help with many things! We can chat, I can tell jokes, answer questions, or help you with various tasks. What interests you?",
            "There's quite a bit we can do! I can tell you about myself, share some jokes, or we can just chat. What would you prefer?",
            "I'm happy to continue our conversation! We could explore my capabilities, share some jokes, or discuss any topic you're interested in."
        ],
        "unknown": [
            "I'm not quite sure I understood that. Could you rephrase it?",
            "I'm still learning and didn't catch that. Could you say it differently?",
            "Hmm, I'm not familiar with that. Would you like to know what I can help you with?",
            "I didn't quite get that. Could you try explaining it another way?",
            "I'm not sure about that yet, but I'm always learning! What else would you like to discuss?"
        ],
        "unknown_personalized": "I'm sorry, {name}, I didn't quite catch that. Could you rephrase it?",
        "followup_name": "I'd love to know your name. What should I call you?",
        "followup_how_are_you": "By the way, how's your day going?",
        "idle_prompt1": "I'm still here if you'd like to chat or need help with anything.",
        "idle_prompt2": "Feel free to ask me anything - I'm always happy to help!",
        "no_command": "I didn't catch that. Could you please repeat what you said?",
        "wake_word_listening": "I'm listening! How can I help?",
        "wake_word_enabled_msg": "Just say '{wake_word}' to get my attention!",
        "activated_msg": "Shadow activated and ready to help!",
        "initial_greeting": "Hi! I'm here to chat and help you with whatever you need. Feel free to ask me anything!",
        "interrupt_msg": "Shutting down. Have a great day!",
        "error_loop_msg": "I ran into a small issue. Let me restart my listening process.",
        "shutdown_msg": "Shadow shutting down.",
        "goodbye_msg": "Goodbye! Have a wonderful day!",
        "goodbye_personalized": "Goodbye, {name}! Have a wonderful day!",
        "critical_error_msg": "I encountered an error and need to shut down. Please restart me.",
        "gemini_error": "I couldn't connect to my knowledge base right now. Could you try asking something else?",
        "generic_error": "I ran into a small issue. Could you try that again?",
        "ask_question": [
            "Here's a question for you: {question}",
            "Let me ask you something: {question}",
            "I have a question for you: {question}",
            "Can you answer this: {question}",
            "Try this question: {question}"
        ],
        "question_correct": [
            "That's correct! Well done!",
            "You got it right! Great job!",
            "Perfect answer! You're good at this!",
            "That's exactly right! Impressive!",
            "Correct! You're really smart!"
        ],
        "question_incorrect": [
            "Not quite right. The correct answer is: {answer}",
            "Close, but the answer is actually: {answer}",
            "That's not it. The right answer is: {answer}",
            "Not quite. The correct answer would be: {answer}",
            "Good try, but the answer is: {answer}"
        ],
        "question_timeout": [
            "Time's up! The answer was: {answer}",
            "Sorry, time ran out. The correct answer is: {answer}",
            "Too slow! The answer is: {answer}",
            "Time's over! The right answer is: {answer}",
            "You took too long. The answer is: {answer}"
        ]
    }
}

# Topics that can lead to follow-up questions (Bilingual) - Simplified for now
# We can expand this later if needed
conversation_topics = {
    "user_name": {"asked": False},
    "how_are_you": {"asked": False}
}


# --- Error Handling Helpers ---

def retry_operation(operation_func, *args, **kwargs):
    """
    Retry an operation multiple times with a delay between attempts.
    """
    for attempt in range(MAX_RETRY_ATTEMPTS):  # Use variable directly
        try:
            return operation_func(*args, **kwargs)
        except Exception as e:
            print(f"Operation failed (attempt {attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}")  # Use variable directly
            if attempt < MAX_RETRY_ATTEMPTS - 1:  # Use variable directly
                print(f"Retrying in {RETRY_DELAY} seconds...")  # Use variable directly
                time.sleep(RETRY_DELAY)  # Use variable directly
            else:
                print("Maximum retry attempts reached. Operation failed.")
                return None


# --- Core Functions ---

def speak(text, lang_code=DEFAULT_LANGUAGE):
    """Converts text to speech using gTTS and plays it using pydub."""
    lang_config = SUPPORTED_LANGUAGES.get(lang_code, SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE])
    tts_code = lang_config['tts']
    logging.info(f"Shadow Bot ({tts_code}): {text}")

    def _speak_operation():
        try:
            tts = gTTS(text=text, lang=tts_code, slow=False)
            with tempfile.NamedTemporaryFile(delete=True, suffix=".mp3") as fp:
                temp_path = fp.name
                tts.save(temp_path)
                sound = AudioSegment.from_mp3(temp_path)
                bot_state.is_speaking = True
                play(sound)
                bot_state.is_speaking = False
            return True
        except Exception as e:
            logging.error(f"Speech synthesis error: {e}")
            return False

    result = retry_operation(_speak_operation)
    if result is None:
        logging.warning(f"Failed to speak in {tts_code}. Using fallback print method.")


def listen_for_audio(timeout=5, phrase_time_limit=10, adjust_noise=True):
    """Listens for audio input with improved error handling."""
    r = sr.Recognizer()
    r.pause_threshold = PAUSE_THRESHOLD
    r.energy_threshold = 3000
    r.dynamic_energy_threshold = DYNAMIC_ENERGY_THRESHOLD

    try:
        # Initialize audio system
        if not initialize_audio():
            logging.error("Failed to initialize audio system")
            return None

        with sr.Microphone(sample_rate=SAMPLE_RATE) as source:
            if adjust_noise:
                logging.info("Adjusting for ambient noise...")
                try:
                    r.adjust_for_ambient_noise(source, duration=ADJUST_NOISE_DURATION)
                except Exception as e:
                    logging.warning(f"Could not adjust for ambient noise: {e}")
                    # Continue without noise adjustment
            
            logging.info("Listening...")
            try:
                audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                return audio
            except sr.WaitTimeoutError:
                logging.info("No speech detected within timeout period")
                return None
            except Exception as e:
                logging.error(f"Error during audio capture: {e}")
                return None
    except Exception as e:
        logging.error(f"Error initializing microphone: {e}")
        return None


def recognize_speech(audio):
    """Attempts to recognize speech with improved error handling."""
    if audio is None:
        return None, None

    r = sr.Recognizer()
    for lang_code, lang_details in SUPPORTED_LANGUAGES.items():
        stt_code = lang_details['stt']
        try:
            text = r.recognize_google(audio, language=stt_code)
            logging.info(f"Recognized text ({stt_code}): {text}")
            return text.lower(), lang_code
        except sr.UnknownValueError:
            logging.info(f"Could not understand audio in {stt_code}")
            continue
        except sr.RequestError as e:
            logging.error(f"Error with speech recognition service: {e}")
            continue
    return None, None


def listen_for_command():
    """
    Listens for a command and attempts recognition in supported languages.
    """
    # Listen for the actual command
    print("Listening for command...")
    audio = listen_for_audio(timeout=5)  # Use standard timeout

    # Recognize speech in supported languages
    recognized_text, detected_lang_code = recognize_speech(audio)

    return recognized_text, detected_lang_code


def match_command(command_text, lang_code):
    """
    Match the command text to the closest command template for the given language.
    """
    if command_text is None or lang_code not in command_templates:
        return None, 0

    lang_templates = command_templates[lang_code]
    best_match = None
    best_confidence = 0

    for command_type, templates in lang_templates.items():
        match, confidence = process.extractOne(command_text, templates)
        if confidence > best_confidence:
            best_match = command_type
            best_confidence = confidence

    if best_confidence >= COMMAND_SIMILARITY_THRESHOLD * 100:  # Use variable directly
        return best_match, best_confidence
    else:
        return None, 0


# --- Conversation State ---
conversation_state = {
    "session_start_time": 0,
    "user_name": None,
    "expecting_response": False,
    "last_question": None,
    # New flag to track if bot is activated
    # WAKE_WORD_ENABLED = False
}


def extract_user_name(command, lang_code):
    """
    Extract a user's name from commands in the specified language.
    """
    # Basic patterns - can be expanded
    patterns = {
        "en": [
            r"(?:my name is|i am|i'm|call me) ([a-z]+)",
            r"([a-z]+) is my name"
        ]
    }

    if lang_code not in patterns:
        return None

    for pattern in patterns[lang_code]:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            # For simplicity, capitalize first letter. Might need refinement for different languages/names.
            return match.group(1).capitalize()

    return None


# --- Gemini Function ---
def get_gemini_response(prompt):
    """Sends a prompt to the Gemini API and returns the response text."""
    if gemini_model is None:
        print("Gemini model not initialized. Cannot get response.")
        # Return a specific error message or fallback
        # For now, using a generic error response key
        return get_response_string("gemini_error", DEFAULT_LANGUAGE)

    print(f"Sending prompt to Gemini: {prompt}")
    try:
        response = gemini_model.generate_content(prompt)
        # Clean up response text (remove potential asterisks or markdown)
        cleaned_text = re.sub(r'[*#]', '', response.text).strip()
        print(f"Gemini Response: {cleaned_text}")
        return cleaned_text
    except Exception as e:
        print(f"Gemini API error: {e}")
        # Return a specific error message or fallback
        return get_response_string("gemini_error", DEFAULT_LANGUAGE)


def get_response_string(key, lang_code, **kwargs):
    """
    Retrieve a response string for the given key and language, performing formatting.
    Handles fallback to default language if the key or language is missing.
    """
    lang_to_use = lang_code if lang_code in responses else DEFAULT_LANGUAGE

    response_options = responses.get(lang_to_use, {}).get(key)

    # Fallback to default language if key not found in specified language
    if response_options is None and lang_to_use != DEFAULT_LANGUAGE:
        print(f"Warning: Response key '{key}' not found for language '{lang_to_use}'. Falling back to default.")
        lang_to_use = DEFAULT_LANGUAGE
        response_options = responses.get(lang_to_use, {}).get(key)

    if response_options is None:
        print(f"Error: Response key '{key}' not found even in default language '{DEFAULT_LANGUAGE}'.")
        # Return a generic error message using the already defined generic_error key
        error_lang = lang_code if lang_code in responses else DEFAULT_LANGUAGE
        return responses.get(error_lang, {}).get("generic_error", ["Sorry, an internal error occurred."])[0]

    # If it's a list, choose randomly
    if isinstance(response_options, list):
        chosen_response = random.choice(response_options)
    else:
        chosen_response = response_options

    # Perform formatting if arguments are provided
    try:
        return chosen_response.format(**kwargs)
    except KeyError as e:
        print(f"Error formatting response key '{key}' for language '{lang_to_use}': Missing key {e}")
        # Return the unformatted string or a generic error
        return chosen_response


def get_contextual_response(command_type, command_text, lang_code):
    """
    Generate a response based on command, text, language, and context.
    """
    recent_command_types = [item["command_type"] for item in context_memory]
    repetition = recent_command_types.count(command_type) if command_type else 0
    should_ask_followup = False
    response_text = ""

    # --- Handle response to previous question ---
    if conversation_state["expecting_response"] and conversation_state["last_question"]:
        last_q = conversation_state["last_question"]
        conversation_state["expecting_response"] = False  # Reset flag

        if last_q == "name" and command_type in ["user_name", "yes", "no"]:
            name = extract_user_name(command_text, lang_code)
            if name:
                conversation_state["user_name"] = name
                response_text = get_response_string("user_name_confirm", lang_code, name=name)
            else:  # Failed to extract name
                response_text = get_response_string("user_name_fail", lang_code)
            return response_text, False  # Don't ask another follow-up immediately

        elif last_q == "how_are_you" and command_type:
            if command_type in ["greeting", "how_are_you", "yes"]:
                response_text = get_response_string("how_are_you_resp_glad", lang_code)
            elif command_type == "no":
                response_text = get_response_string("how_are_you_resp_sorry", lang_code)
                should_ask_followup = True  # Maybe ask if we can help
            else:  # Unclear response to "how are you?"
                response_text = get_response_string("unknown", lang_code)
            return response_text, should_ask_followup

        elif last_q == "another_joke":
            if command_type == "yes":
                command_type = "joke"  # Trigger another joke
            else:
                response_text = get_response_string("no_generic", lang_code)
                return response_text, False

    # --- Handle specific command types ---
    if command_type == "greeting":
        base_greetings = responses.get(lang_code, responses[DEFAULT_LANGUAGE]).get("greeting",
                                                                                   [])  # Use variable directly
        if conversation_state["user_name"]:
            # Attempt personalized greeting (simple format for now)
            # Ensure base_greetings is not empty before accessing index 0
            if base_greetings:
                first_greeting = random.choice(base_greetings)
                greeting_part1 = first_greeting.split('!')[0] if '!' in first_greeting else first_greeting
                greeting_part2 = first_greeting.split('!')[1] if '!' in first_greeting and len(
                    first_greeting.split('!')) > 1 else ""
                personalized_greeting = f"{greeting_part1}, {conversation_state['user_name']}!"
                response_text = personalized_greeting + greeting_part2
            else:  # Fallback if no greetings defined
                response_text = f"Hello, {conversation_state['user_name']}!"

        else:
            response_text = random.choice(base_greetings) if base_greetings else "Hello!"

        if repetition > 1:
            response_text = get_response_string("greeting_repeat", lang_code)
        elif not conversation_topics["how_are_you"]["asked"] and random.random() < 0.3:
            conversation_topics["how_are_you"]["asked"] = True
            conversation_state["expecting_response"] = True
            conversation_state["last_question"] = "how_are_you"
            response_text += get_response_string("greeting_followup", lang_code)

    elif command_type == "how_are_you":
        response_text = get_response_string("how_are_you", lang_code)
        conversation_state["expecting_response"] = True
        conversation_state["last_question"] = "how_are_you"

    elif command_type == "time":
        # Format time based on language preference if needed, simple for now
        current_time_str = time.strftime("%I:%M %p")
        if lang_code == 'bn':
            # Convert time to Bangla numerals if desired (complex, skip for now)
            # Or just use standard numerals
            pass
        if repetition > 1:
            response_text = get_response_string("time_repeat", lang_code, current_time=current_time_str)
        else:
            response_text = get_response_string("time", lang_code, current_time=current_time_str)

    elif command_type == "name":
        if repetition > 1:
            response_text = get_response_string("name_repeat", lang_code)
        elif not conversation_state["user_name"] and random.random() < 0.5:
            conversation_state["expecting_response"] = True
            conversation_state["last_question"] = "name"
            response_text = get_response_string("name_ask", lang_code)
        else:
            response_text = get_response_string("name", lang_code)

    elif command_type == "user_name":
        name = extract_user_name(command_text, lang_code)
        if name:
            conversation_state["user_name"] = name
            response_text = get_response_string("user_name_confirm", lang_code, name=name)
        else:
            response_text = get_response_string("user_name_fail", lang_code)

    elif command_type == "joke":
        jokes_list = responses.get(lang_code, responses[DEFAULT_LANGUAGE]).get("joke", [])  # Use variable directly
        used_jokes = [item["response"] for item in context_memory if item["command_type"] == "joke"]
        available_jokes = [j for j in jokes_list if j not in used_jokes]

        if available_jokes:
            joke = random.choice(available_jokes)
            response_text = joke
            if random.random() < 0.3:
                conversation_state["expecting_response"] = True
                conversation_state["last_question"] = "another_joke"
                response_text += get_response_string("joke_ask_more", lang_code)
        else:
            response_text = get_response_string("joke_out", lang_code)

    elif command_type == "thanks":
        response_text = get_response_string("thanks", lang_code)

    elif command_type == "capabilities":
        response_text = get_response_string("capabilities", lang_code)

    elif command_type == "about_you":
        response_text = get_response_string("about_you", lang_code)

    elif command_type == "how_made":
        response_text = get_response_string("how_made", lang_code)

    elif command_type == "weather":
        response_text = get_response_string("weather", lang_code)

    elif command_type == "exit":
        name = conversation_state.get("user_name")
        if name:
            response_text = get_response_string("goodbye_personalized", lang_code, name=name)
        else:
            # Use generic exit if name unknown or key missing
            exit_responses_list = responses.get(lang_code, responses[DEFAULT_LANGUAGE]).get("exit",
                                                                                            [])  # Use variable directly
            response_text = random.choice(exit_responses_list) if exit_responses_list else "Goodbye!"


    elif command_type == "yes" and not conversation_state["last_question"]:
        response_text = get_response_string("yes_generic", lang_code)
    elif command_type == "no" and not conversation_state["last_question"]:
        response_text = get_response_string("no_generic", lang_code)

    elif command_type == "why":
        response_text = get_response_string("why", lang_code)

    elif command_type == "what_else":
        response_text = get_response_string("what_else", lang_code)

    # --- Unknown command: Fallback to Gemini ---
    elif command_type == "ask_question":
        # Generate a new question
        question_data = generate_question()
        conversation_state["current_question"] = question_data
        conversation_state["question_start_time"] = time.time()
        conversation_state["expecting_response"] = True
        conversation_state["last_question"] = "answer_question"
        response_text = get_response_string("ask_question", lang_code, question=question_data["question"])
        return response_text, False

    elif command_type == "answer_question" and conversation_state["last_question"] == "answer_question":
        # Check if we have a current question
        if "current_question" not in conversation_state:
            response_text = get_response_string("unknown", lang_code)
            return response_text, False

        # Get the current question data
        question_data = conversation_state["current_question"]
        user_answer = command_text.lower().strip()
        correct_answer = question_data["answer"].lower().strip()
        
        # Check if the answer is correct
        if user_answer == correct_answer:
            response_text = get_response_string("question_correct", lang_code)
        else:
            response_text = get_response_string("question_incorrect", lang_code, answer=correct_answer)
        
        # Clear the current question
        conversation_state.pop("current_question", None)
        conversation_state["expecting_response"] = False
        conversation_state["last_question"] = None
        
        return response_text, True

    else:
        print(f"Command type '{command_type}' not recognized or no match. Querying Gemini...")
        # Use the original command text as the prompt for Gemini
        gemini_response = get_gemini_response(command_text)
        response_text = gemini_response
        # Don't ask follow-up questions after a Gemini response for now
        should_ask_followup = False

    return response_text, should_ask_followup


def generate_follow_up_question(lang_code):
    """
    Generate a follow-up question in the specified language based on context.
    """
    # Ask for name?
    if not conversation_state["user_name"] and random.random() < 0.2:
        conversation_state["expecting_response"] = True
        conversation_state["last_question"] = "name"
        return get_response_string("followup_name", lang_code)

    # Ask how they are?
    session_duration = time.time() - conversation_state["session_start_time"]
    if session_duration > 60 and not conversation_topics["how_are_you"]["asked"] and random.random() < 0.3:
        conversation_topics["how_are_you"]["asked"] = True
        conversation_state["expecting_response"] = True
        conversation_state["last_question"] = "how_are_you"
        return get_response_string("followup_how_are_you", lang_code)

    # Add this new section to ask questions
    if random.random() < 0.2:  # 20% chance to ask a question
        question_data = generate_question()
        conversation_state["current_question"] = question_data
        conversation_state["question_start_time"] = time.time()
        conversation_state["expecting_response"] = True
        conversation_state["last_question"] = "answer_question"
        return get_response_string("ask_question", lang_code, question=question_data["question"])

    return None


def process_command(command, lang_code):
    """Processes commands with improved context management."""
    if command is None:
        return True

    try:
        # Update last activity time
        bot_state.last_activity = time.time()

        # Build context from previous interactions
        context = []
        if bot_state.context_memory:
            start_index = max(0, len(bot_state.context_memory) - 3)
            for item in list(bot_state.context_memory)[start_index:]:
                context.append(f"Previous: {item['command']} -> {item['response']}")
        
        context_str = "\n".join(context) if context else "No previous context"
        
        # Get response from Gemini
        try:
            response = get_gemini_response(f"""Respond concisely to: "{command}"
            {context_str}""")
            if not response or response.strip() == "":
                response = "Could you repeat that?"
        except Exception as e:
            logging.error(f"Error getting Gemini response: {e}")
            response = "Let's try something else."

        # Store interaction
        bot_state.context_memory.append({
            "timestamp": time.time(),
            "command": command,
            "lang_code": lang_code,
            "response": response
        })

        # Add natural delay before speaking
        time.sleep(CONVERSATION_SETTINGS["response_delay"])

        # Speak the response
        speak(response, lang_code=lang_code)

        # Check for exit command
        if any(exit_word in command.lower() for exit_word in ["exit", "quit", "goodbye", "bye", "stop"]):
            return False

        return True

    except Exception as e:
        logging.error(f"Error processing command: {e}")
        return True


# --- Main Execution ---

if __name__ == "__main__":
    default_lang = DEFAULT_LANGUAGE

    try:
        # Initialize audio system before starting
        if not initialize_audio():
            print("Error: Could not initialize audio system.")
            print("Please check your audio configuration and try again.")
            exit(1)

        conversation_state["session_start_time"] = time.time()
        speak("Hi! How can I help?", lang_code=default_lang)
        time.sleep(0.5)

        running = True
        last_activity = time.time()
        last_lang_code = default_lang

        while running:
            # Listen and recognize speech
            command, lang_code = listen_for_command()

            if command is not None:
                last_activity = time.time()
                if lang_code:
                    last_lang_code = lang_code

                # Process the command
                process_lang = lang_code if lang_code else last_lang_code
                running = process_command(command, process_lang)

            time.sleep(0.1)

    except KeyboardInterrupt:
        speak("Goodbye!", lang_code=last_lang_code)
    except Exception as e:
        logging.error(f"Critical error: {e}")
        speak("I need to restart. Goodbye!", lang_code=default_lang)


def generate_question():
    """Generate a random question for the user."""
    questions = [
        {
            "question": "What is the capital of France?",
            "answer": "paris",
            "timeout": 10
        },
        {
            "question": "How many sides does a hexagon have?",
            "answer": "6",
            "timeout": 10
        },
        {
            "question": "What is the largest planet in our solar system?",
            "answer": "jupiter",
            "timeout": 10
        },
        {
            "question": "What is the chemical symbol for gold?",
            "answer": "au",
            "timeout": 10
        },
        {
            "question": "Who painted the Mona Lisa?",
            "answer": "leonardo da vinci",
            "timeout": 15
        },
        {
            "question": "What is the square root of 144?",
            "answer": "12",
            "timeout": 10
        },
        {
            "question": "What is the main ingredient in guacamole?",
            "answer": "avocado",
            "timeout": 10
        },
        {
            "question": "How many continents are there?",
            "answer": "7",
            "timeout": 10
        },
        {
            "question": "What is the opposite of 'hot'?",
            "answer": "cold",
            "timeout": 5
        },
        {
            "question": "What is the largest mammal in the world?",
            "answer": "blue whale",
            "timeout": 10
        }
    ]
    return random.choice(questions)

