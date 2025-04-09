import speech_recognition as sr
from gtts import gTTS
import playsound
import os
import time
import config  # Import the configuration file
from fuzzywuzzy import process
from collections import deque
import random

# --- Context Memory ---
context_memory = deque(maxlen=config.CONTEXT_MEMORY_SIZE)

# --- Command Templates ---
# Dictionary of command templates for fuzzy matching
command_templates = {
    "greeting": ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening"],
    "time": ["what time is it", "tell me the time", "current time", "time now", "what's the time"],
    "name": ["what's your name", "who are you", "your name", "tell me your name", "introduce yourself"],
    "joke": ["tell me a joke", "say something funny", "make me laugh", "joke", "know any jokes"],
    "exit": ["stop", "exit", "quit", "goodbye", "bye", "shut down", "turn off"]
}

# --- Error Handling Helpers ---

def retry_operation(operation_func, *args, **kwargs):
    """
    Retry an operation multiple times with a delay between attempts.
    
    Args:
        operation_func: The function to retry
        *args, **kwargs: Arguments to pass to the function
        
    Returns:
        The result of the function if successful, None otherwise
    """
    for attempt in range(config.MAX_RETRY_ATTEMPTS):
        try:
            return operation_func(*args, **kwargs)
        except Exception as e:
            print(f"Operation failed (attempt {attempt+1}/{config.MAX_RETRY_ATTEMPTS}): {e}")
            if attempt < config.MAX_RETRY_ATTEMPTS - 1:
                print(f"Retrying in {config.RETRY_DELAY} seconds...")
                time.sleep(config.RETRY_DELAY)
            else:
                print("Maximum retry attempts reached. Operation failed.")
                return None

# --- Core Functions ---

def speak(text):
    """Converts text to speech and plays it."""
    def _speak_operation():
        print(f"Shadow Bot: {text}")
        tts = gTTS(text=text, lang=config.LANGUAGE, slow=False)
        tts.save(config.AUDIO_FILE)
        playsound.playsound(config.AUDIO_FILE)
        os.remove(config.AUDIO_FILE)
        return True
    
    result = retry_operation(_speak_operation)
    if result is None:
        print("Failed to speak. Using fallback method.")
        print(f"Shadow Bot would say: {text}")

def listen_for_audio(timeout=5, phrase_time_limit=10, adjust_noise=True):
    """
    Base function to listen for audio input.
    
    Args:
        timeout: Seconds to wait before timing out
        phrase_time_limit: Maximum seconds for a phrase
        adjust_noise: Whether to adjust for ambient noise
        
    Returns:
        Audio data if successful, None otherwise
    """
    r = sr.Recognizer()
    with sr.Microphone() as source:
        if adjust_noise:
            print("Adjusting for ambient noise...")
            r.adjust_for_ambient_noise(source, duration=1)
        
        try:
            print("Listening...")
            audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            return audio
        except sr.WaitTimeoutError:
            print("No audio detected within timeout period.")
            return None
        except Exception as e:
            print(f"Error capturing audio: {e}")
            return None

def recognize_speech(audio):
    """
    Recognize speech from audio data.
    
    Args:
        audio: Audio data to recognize
        
    Returns:
        Recognized text if successful, None otherwise
    """
    if audio is None:
        return None
        
    r = sr.Recognizer()
    try:
        print("Recognizing...")
        text = r.recognize_google(audio, language=config.LANGUAGE)
        print(f"Recognized: {text}")
        return text.lower()
    except sr.UnknownValueError:
        print("Could not understand the audio.")
        return None
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
        return None
    except Exception as e:
        print(f"Error during speech recognition: {e}")
        return None

def listen_for_wake_word():
    """
    Listen specifically for wake words.
    
    Returns:
        True if a wake word was detected, False otherwise
    """
    if not config.WAKE_WORD_ENABLED:
        return True  # Skip wake word detection if disabled
        
    print("Listening for wake word...")
    
    # Try up to MAX_RETRY_ATTEMPTS times to detect a wake word
    for attempt in range(config.MAX_RETRY_ATTEMPTS):
        audio = listen_for_audio(timeout=None, phrase_time_limit=3, adjust_noise=(attempt == 0))
        if audio is None:
            continue
            
        text = recognize_speech(audio)
        if text is None:
            continue
            
        # Check if any wake word is in the recognized text
        if any(wake_word in text for wake_word in config.WAKE_WORDS):
            print(f"Wake word detected: {text}")
            return True
            
    return False

def listen_for_command():
    """
    Listens for a command from the user via microphone.
    If wake word detection is enabled, only listens after detecting a wake word.
    
    Returns:
        The recognized command text, or None if no command was recognized
    """
    # First check for wake word if enabled
    if config.WAKE_WORD_ENABLED:
        if not listen_for_wake_word():
            return None
        speak("I'm listening")
    
    # Then listen for the actual command
    audio = listen_for_audio(timeout=config.WAKE_WORD_TIMEOUT if config.WAKE_WORD_ENABLED else 5)
    return recognize_speech(audio)

def match_command(command_text):
    """
    Match the command text to the closest command template using fuzzy matching.
    
    Args:
        command_text: The text to match against command templates
        
    Returns:
        Tuple of (command_type, confidence) or (None, 0) if no match
    """
    if command_text is None:
        return None, 0
        
    # Check each command type
    best_match = None
    best_confidence = 0
    
    for command_type, templates in command_templates.items():
        # Find the best match among this command type's templates
        match, confidence = process.extractOne(command_text, templates)
        
        # If this is better than our previous best match, update
        if confidence > best_confidence:
            best_match = command_type
            best_confidence = confidence
    
    # Only return a match if it's above our threshold
    if best_confidence >= config.COMMAND_SIMILARITY_THRESHOLD * 100:  # Convert from 0-1 to 0-100
        return best_match, best_confidence
    else:
        return None, 0

def get_contextual_response(command_type):
    """
    Generate a response based on the command type and conversation context.
    
    Args:
        command_type: The type of command detected
        
    Returns:
        Response text
    """
    # Check if we've recently responded to this same command type
    recent_command_types = [item["command_type"] for item in context_memory]
    repetition = recent_command_types.count(command_type) if command_type else 0
    
    # Greeting responses with variety
    if command_type == "greeting":
        greetings = [
            "Hello there! How can I help?",
            "Hi! What can I do for you?",
            "Hey! Nice to hear from you.",
            "Greetings! I'm at your service."
        ]
        
        # If this is a repeated greeting, acknowledge it
        if repetition > 1:
            return f"Hello again! You seem friendly today. How can I help?"
        else:
            return random.choice(greetings)
            
    # Time responses
    elif command_type == "time":
        current_time = time.strftime("%I:%M %p")  # e.g., 02:55 PM
        
        # If they've asked for the time multiple times recently
        if repetition > 1:
            return f"It's still {current_time}. Time flies when you're having fun!"
        else:
            return f"The current time is {current_time}."
            
    # Name responses
    elif command_type == "name":
        if repetition > 1:
            return "As I mentioned, I'm Shadow Bot. I won't forget my name, I promise!"
        else:
            return "My name is Shadow Bot. I'm your voice assistant."
            
    # Joke responses
    elif command_type == "joke":
        jokes = [
            "Why don't scientists trust atoms? Because they make up everything!",
            "What do you call a fake noodle? An impasta!",
            "Why did the scarecrow win an award? Because he was outstanding in his field!",
            "How does a penguin build its house? Igloos it together!",
            "Why don't eggs tell jokes? They'd crack each other up!"
        ]
        
        # Try not to repeat jokes
        used_jokes = [item["response"] for item in context_memory if item["command_type"] == "joke"]
        available_jokes = [joke for joke in jokes if joke not in used_jokes]
        
        if available_jokes:
            return random.choice(available_jokes)
        else:
            return "I'm all out of fresh jokes! Give me some time to think of new ones."
            
    # Exit responses
    elif command_type == "exit":
        return "Goodbye! Shutting down."
        
    # Unknown command
    else:
        return "Sorry, I don't understand that command. Could you try saying it differently?"

def process_command(command):
    """
    Processes the recognized command text and triggers appropriate actions or responses.

    Args:
        command (str or None): The lowercase text of the command recognized,
                               or None if no command was heard or understood.

    Returns:
        bool: True to continue the main loop, False to exit.
    """
    if command is None:
        if config.WAKE_WORD_ENABLED:
            # If wake word is enabled but no command was heard after wake word
            return True  # Just continue listening
        else:
            # If wake word is disabled and no command was heard
            speak("I didn't hear anything. Could you please repeat?")
            return True
    
    # Match the command to a template
    command_type, confidence = match_command(command)
    
    # Get contextual response based on command type and history
    response = get_contextual_response(command_type)
    
    # Store this interaction in context memory
    context_memory.append({
        "timestamp": time.time(),
        "command": command,
        "command_type": command_type,
        "confidence": confidence,
        "response": response
    })
    
    # Speak the response
    speak(response)
    
    # Return False to exit if this was an exit command
    if command_type == "exit":
        return False
        
    return True  # Continue the loop for all other commands

# --- Main Execution ---

if __name__ == "__main__":
    try:
        speak("Shadow Bot activated and ready.")
        
        if config.WAKE_WORD_ENABLED:
            speak(f"Wake word detection is enabled. Say {config.WAKE_WORDS[0]} to activate me.")
        
        running = True
        while running:
            try:
                command = listen_for_command()
                running = process_command(command)
                # Small delay to prevent tight looping
                time.sleep(0.1)
            except KeyboardInterrupt:
                # Handle Ctrl+C gracefully
                speak("Interrupt detected. Shutting down.")
                running = False
            except Exception as e:
                print(f"Error in main loop: {e}")
                speak("I encountered an error. Let me restart my listening process.")
                time.sleep(1)  # Brief pause before continuing
                
        print("Shadow Bot shutting down.")
        speak("Shadow Bot has shut down. Goodbye!")
        
    except Exception as e:
        print(f"Critical error: {e}")
        speak("A critical error occurred. Shadow Bot must shut down.")
