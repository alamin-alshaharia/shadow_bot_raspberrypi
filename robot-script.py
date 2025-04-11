import speech_recognition as sr
from gtts import gTTS
# import playsound # Replacing with pydub
import os
import time
# import config # No longer needed, config is inline
from fuzzywuzzy import process
from collections import deque
import random
import re # Import regex for name extraction
from langdetect import detect, LangDetectException # Import langdetect
from pydub import AudioSegment # For audio playback
from pydub.playback import play # For audio playback
import tempfile # For temporary audio files
import vosk

# --- Configuration Settings (formerly config.py) ---

# Supported Languages
# Define the languages the bot can understand and speak
# Format: { "short_code": {"tts": "google_tts_code", "stt": "google_stt_code"} }
# Note: SpeechRecognition uses BCP-47 codes (e.g., "bn-BD"), gTTS uses simpler codes (e.g., "bn")
SUPPORTED_LANGUAGES = {
    "en": {"tts": "en", "stt": "en-US"},  # English
    "bn": {"tts": "bn", "stt": "bn-BD"}   # Bengali (Bangladesh)
}
DEFAULT_LANGUAGE = "en" # Default language if detection fails or for initial messages

# Temporary file path for TTS audio output
AUDIO_FILE = "response.mp3"

# Wake word settings (Keep wake words primarily in one language for simplicity, e.g., English)
WAKE_WORD_ENABLED = True
WAKE_WORDS = ["hey shadow bot", "shadow bot", "hey shadow", "shadow"] # English wake words
WAKE_WORD_LANG_STT = "en-US" # STT Language for wake word recognition
WAKE_WORD_TIMEOUT = 10  # Seconds to listen for a command after wake word

# Command parsing settings
COMMAND_SIMILARITY_THRESHOLD = 0.7  # Threshold for fuzzy matching commands (0.0 to 1.0)

# Contextual conversation settings
CONTEXT_MEMORY_SIZE = 5  # Number of previous interactions to remember

# Error handling settings
MAX_RETRY_ATTEMPTS = 3  # Maximum number of retries for failed operations
RETRY_DELAY = 2  # Seconds to wait between retries

# --- Microphone Listening Settings ---
# Adjust based on microphone sensitivity and environment noise
# Higher values require louder speech to be detected
DYNAMIC_ENERGY_THRESHOLD = True # Let the library adjust energy threshold automatically
# If DYNAMIC_ENERGY_THRESHOLD is False, uncomment and set manually:
# ENERGY_THRESHOLD = 3000
PAUSE_THRESHOLD = 0.8  # Seconds of non-speaking audio before phrase is considered complete
PHRASE_TIME_LIMIT = 10 # Max seconds for a single phrase/command
ADJUST_NOISE_DURATION = 1 # Seconds to adjust for ambient noise on startup/wake

# --- Vosk Offline Speech Recognition Settings ---
# Path to the Vosk model (download from https://alphacephei.com/vosk/models)
VOSK_MODEL_PATH = "model"  # Replace with the actual path to your Vosk model

# --- Load Vosk Model ---
try:
    vosk_model = vosk.Model(VOSK_MODEL_PATH)
    print("Vosk model initialized successfully.")
except Exception as e:
    print(f"Error loading Vosk model: {e}")
    vosk_model = None

# --- Bot Logic (formerly bot_brain.py) ---

# --- Context Memory ---
context_memory = deque(maxlen=CONTEXT_MEMORY_SIZE) # Use variable directly

# --- Bilingual Data Structures ---

# Command Templates (Nested by language)
command_templates = {
    "en": {
        "greeting": ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening"],
        "time": ["what time is it", "tell me the time", "current time", "time now", "what's the time"],
        "name": ["what's your name", "who are you", "your name", "tell me your name", "introduce yourself"],
        "joke": ["tell me a joke", "say something funny", "make me laugh", "joke", "know any jokes"],
        "exit": ["stop", "exit", "quit", "goodbye", "bye", "shut down", "turn off"],
        "how_are_you": ["how are you", "how are you doing", "how's it going", "how do you feel", "are you okay"],
        "thanks": ["thank you", "thanks", "appreciate it", "that's helpful", "great job"],
        "weather": ["what's the weather", "how's the weather", "is it raining", "temperature today", "forecast"],
        "capabilities": ["what can you do", "help", "list commands", "your abilities", "what are you capable of", "features"],
        "about_you": ["tell me about yourself", "what are you", "are you a robot", "are you human", "are you ai"],
        "user_name": ["my name is", "call me", "i am", "i'm called"],
        "how_made": ["how were you made", "who made you", "your creator", "how were you created"],
        "yes": ["yes", "yeah", "sure", "absolutely", "correct", "that's right", "yep", "ok", "okay"],
        "no": ["no", "nope", "not really", "i don't think so", "negative", "not at all"],
        "why": ["why", "why is that", "how come", "for what reason", "explain why"],
        "what_else": ["আর কি", "আরও বলো", "চালিয়ে যাও", "আর কিছু", "আরও তথ্য"]
    },
    "bn": {
        "greeting": ["হ্যালো", "হাই", "সালাম", "শুভেচ্ছা", "শুভ সকাল", "শুভ বিকাল", "শুভ সন্ধ্যা"],
        "time": ["কয়টা বাজে", "সময় কত", "এখন কয়টা বাজে", "সময় বলুন", "বর্তমান সময়"],
        "name": ["তোমার নাম কি", "আপনি কে", "আপনার নাম", "তোমার নাম বলো", "পরিচয় দাও"],
        "joke": ["একটা জোকস বলো", "মজার কিছু বলো", "হাসাও", "জোকস", "কৌতুক বলো"],
        "exit": ["বন্ধ করো", "থামো", "বিদায়", "বাই", "বন্ধ হও", "বের হও"],
        "how_are_you": ["কেমন আছো", "কেমন আছেন", "কি খবর", "কেমন চলছে", "আপনি ঠিক আছেন"],
        "thanks": ["ধন্যবাদ", "থ্যাঙ্ক ইউ", "অনেক ধন্যবাদ", "সাহায্যের জন্য ধন্যবাদ", "খুব ভালো"],
        "weather": ["আবহাওয়া কেমন", "আজকের আবহাওয়া", "বৃষ্টি হচ্ছে", "আজকের তাপমাত্রা", "আবহাওয়ার পূর্বাভাস"],
        "capabilities": ["তুমি কি করতে পারো", "সাহায্য", "কমান্ড লিস্ট", "তোমার ক্ষমতা", "কি কি পারো", "ফিচার"],
        "about_you": ["তোমার সম্পর্কে বলো", "তুমি কি", "তুমি কি রোবট", "তুমি কি মানুষ", "তুমি কি এআই"],
        "user_name": ["আমার নাম", "আমাকে ডাকবে", "আমি হলাম", "আমার নাম হলো"],
        "how_made": ["তোমাকে কিভাবে বানানো হয়েছে", "কে বানিয়েছে", "তোমার স্রষ্টা কে", "কিভাবে তৈরি হয়েছো"],
        "yes": ["হ্যাঁ", "জি", "অবশ্যই", "ঠিক", "আচ্ছা", "ওকে"],
        "no": ["না", "জি না", "আসলে না", "মনে হয় না", "নেগেটিভ"],
        "why": ["কেন", "কি জন্য", "কি কারণে", "কারণ কি", "ব্যাখ্যা করো"],
        "what_else": ["আর কি", "আরও বলো", "চালিয়ে যাও", "আর কিছু", "আরও তথ্য"]
    }
}

# Responses (Nested by language)
responses = {
    "en": {
        "greeting": [
            "Hello there! How can I help?", "Hi! What can I do for you?",
            "Hey! Nice to hear from you.", "Greetings! I'm at your service."
        ],
        "greeting_repeat": "Hello again! You seem friendly today. How can I help?",
        "greeting_followup": " How are you doing today?",
        "how_are_you": [
            "I'm doing well, thank you for asking! How about you?", "I'm functioning perfectly! How are you?",
            "All systems operational! How's your day going?", "I'm great! Thanks for asking. How are you doing?"
        ],
        "how_are_you_resp_glad": "I'm glad to hear that! What can I help you with today?",
        "how_are_you_resp_sorry": "I'm sorry to hear that. Is there anything I can do to help?",
        "time": "The current time is {current_time}.",
        "time_repeat": "It's still {current_time}. Time flies when you're having fun!",
        "name": "My name is Shadow Bot. I'm your voice assistant.",
        "name_repeat": "As I mentioned, I'm Shadow Bot. I won't forget my name, I promise!",
        "name_ask": "My name is Shadow Bot. I'm your voice assistant. What's your name?",
        "user_name_confirm": "Nice to meet you, {name}! How can I help you today?",
        "user_name_fail": "I didn't quite catch your name. Could you tell me again?",
        "joke": [
            "Why don't scientists trust atoms? Because they make up everything!", "What do you call a fake noodle? An impasta!",
            "Why did the scarecrow win an award? Because he was outstanding in his field!", "How does a penguin build its house? Igloos it together!",
            "Why don't eggs tell jokes? They'd crack each other up!", "What did the ocean say to the beach? Nothing, it just waved!",
            "Why did the bicycle fall over? Because it was two-tired!", "What's orange and sounds like a parrot? A carrot!",
            "Why can't you give Elsa a balloon? Because she will let it go!", "I told my wife she was drawing her eyebrows too high. She looked surprised!"
        ],
        "joke_ask_more": " Would you like to hear another one?",
        "joke_out": "I'm all out of fresh jokes! Give me some time to think of new ones.",
        "thanks": [
            "You're welcome! Is there anything else I can help with?", "My pleasure! What else would you like to know?",
            "Happy to help! Let me know if you need anything else.", "Anytime! That's what I'm here for."
        ],
        "capabilities": [
            "I can tell you the time, tell jokes, chat with you, and respond to basic questions. I'm always learning new things! What would you like me to do?",
            "I'm a voice assistant that can have conversations, tell you the time, share jokes, and remember context from our chat. How can I assist you?",
            "I can understand natural language, remember our conversation context, tell jokes, and respond to various commands. What would you like to try?"
        ],
        "about_you": [
            "I'm Shadow Bot, a voice assistant designed to help with various tasks and have conversations. I can understand natural language and remember our conversation context.",
            "I'm an AI assistant called Shadow Bot. I was created to have helpful conversations and assist with simple tasks like telling the time or sharing jokes.",
            "I'm Shadow Bot, a voice-controlled assistant. I use speech recognition to understand what you say and text-to-speech to respond. I'm here to help and chat!"
        ],
        "how_made": [
            "I was created using Python with libraries for speech recognition and text-to-speech. My brain is a program that processes language and generates responses based on context.",
            "I'm built with Python programming language, using speech recognition to understand commands and text-to-speech to respond. I'm designed to have natural conversations.",
            "My creator built me using Python with libraries like SpeechRecognition and gTTS. I'm designed to understand natural language and maintain conversation context."
        ],
        "weather": [
            "I don't have access to real-time weather data, but I'd be happy to chat about other topics!",
            "Unfortunately, I can't check the weather for you. Is there something else I can help with?",
            "I don't have weather capabilities yet, but I'm learning new skills all the time!"
        ],
        "exit": [
            "Goodbye! It was nice chatting with you.", "See you later! Have a great day.",
            "Goodbye! I'll be here when you need me again.", "Shutting down. It was a pleasure talking with you!"
        ],
        "yes_generic": "Great! What would you like to talk about?",
        "no_generic": "Alright. Is there something else you'd like to discuss?",
        "why": [
            "That's an interesting question! I'm designed to respond this way to be helpful.",
            "I'm programmed to provide the most relevant information I can.",
            "Good question! My responses are based on my programming and conversation context."
        ],
        "what_else": [
            "I can tell you the time, tell jokes, chat about various topics, or just have a friendly conversation. What interests you?",
            "We could talk about how I was made, I could tell you a joke, or we could just chat. What would you prefer?",
            "I'm happy to continue our conversation! We could discuss my capabilities, I could tell you a joke, or we could chat about something else."
        ],
        "unknown": [
            "I'm not sure I understand. Could you rephrase that?",
            "I'm still learning and didn't quite catch that. What would you like to talk about?",
            "Hmm, I'm not familiar with that. Would you like to know what I can do?",
            "I didn't understand that completely. Would you like to chat about something else?",
            "I'm not programmed to understand that yet, but I'm always learning! What else would you like to discuss?"
        ],
        "unknown_personalized": "I'm sorry, {name}, I didn't quite understand that. Could you try saying it differently?",
        "followup_name": "By the way, what's your name?",
        "followup_how_are_you": "How are you doing today?",
        "idle_prompt1": "I'm still here if you need anything.",
        "idle_prompt2": "Just let me know if you'd like to chat.",
        "no_command": "I didn't hear anything. Could you please repeat?",
        "wake_word_listening": "I'm listening",
        "wake_word_enabled_msg": "Wake word detection is enabled. Say {wake_word} to activate me.",
        "activated_msg": "Shadow Bot activated and ready.",
        "initial_greeting": "I'm here to chat and help you. Feel free to ask me questions or just have a conversation!",
        "interrupt_msg": "Interrupt detected. Shutting down.",
        "error_loop_msg": "I encountered an error. Let me restart my listening process.",
        "shutdown_msg": "Shadow Bot has shut down. Goodbye!",
        "goodbye_personalized": "Shadow Bot has shut down. Goodbye, {name}!",
        "critical_error_msg": "A critical error occurred. Shadow Bot must shut down.",
        "gemini_error": "Sorry, I couldn't connect to my knowledge base right now.",
        "generic_error": "Sorry, an internal error occurred."
    },
    "bn": {
        "greeting": [
            "হ্যালো! আমি কিভাবে সাহায্য করতে পারি?", "হাই! আপনার জন্য কি করতে পারি?",
            "আরে! আপনার কথা শুনে ভালো লাগলো।", "শুভেচ্ছা! আমি আপনার সেবায় حاضر।"
        ],
        "greeting_repeat": "আবারো হ্যালো! আপনাকে আজ বেশ বন্ধুত্বপূর্ণ লাগছে। আমি কিভাবে সাহায্য করতে পারি?",
        "greeting_followup": " আপনি আজ কেমন আছেন?",
        "how_are_you": [
            "আমি ভালো আছি, জিজ্ঞাসা করার জন্য ধন্যবাদ! আপনি কেমন আছেন?", "আমি পুরোপুরি কাজ করছি! আপনি কেমন আছেন?",
            "সব সিস্টেম চালু আছে! আপনার দিন কেমন যাচ্ছে?", "আমি দারুণ আছি! ধন্যবাদ। আপনি কেমন আছেন?"
        ],
        "how_are_you_resp_glad": "শুনে ভালো লাগলো! আমি আজ আপনাকে কিভাবে সাহায্য করতে পারি?",
        "how_are_you_resp_sorry": "শুনে দুঃখিত হলাম। আমি কি আপনাকে কোনোভাবে সাহায্য করতে পারি?",
        "time": "এখন সময় {current_time}।",
        "time_repeat": "এখনো {current_time} বাজে। মজা করলে সময় দ্রুত চলে যায়!",
        "name": "আমার নাম শ্যাডো বট। আমি আপনার ভয়েস অ্যাসিস্ট্যান্ট।",
        "name_repeat": "আমি আগেই বলেছি, আমার নাম শ্যাডো বট। আমি আমার নাম ভুলবো না, কথা দিচ্ছি!",
        "name_ask": "আমার নাম শ্যাডো বট। আমি আপনার ভয়েস অ্যাসিস্ট্যান্ট। আপনার নাম কি?",
        "user_name_confirm": "আপনার সাথে পরিচিত হয়ে ভালো লাগলো, {name}! আমি আজ আপনাকে কিভাবে সাহায্য করতে পারি?",
        "user_name_fail": "আমি আপনার নামটা ঠিক বুঝতে পারিনি। আপনি কি আবার বলবেন?",
        "joke": [
            "বিজ্ঞানীরা পরমাণুকে বিশ্বাস করে না কেন? কারণ তারা সবকিছু তৈরি করে!", "নকল নুডুলসকে কি বলে? ইম্পাস্তা!",
            "কাকতাড়ুয়া কেন পুরস্কার জিতেছিল? কারণ সে তার ক্ষেত্রে অসামান্য ছিল!", "পেঙ্গুইন কিভাবে তার ঘর তৈরি করে? ইগলু দিয়ে!",
            "ডিমেরা কেন জোকস বলে না? তারা একে অপরকে ফাটিয়ে ফেলবে!", "সমুদ্র সৈকতকে কি বলেছিল? কিছুই না, শুধু ঢেউ দিয়েছিল!",
            "সাইকেলটি কেন পড়ে গিয়েছিল? কারণ এটি টু-টায়ার্ড ছিল!", "কমলা রঙের এবং টিয়া পাখির মতো শব্দ করে কি? একটি গাজর!",
            "এলসাকে কেন বেলুন দিতে পারবেন না? কারণ সে এটা ছেড়ে দেবে!", "আমি আমার স্ত্রীকে বলেছিলাম সে তার ভ্রু খুব উঁচুতে আঁকছে। সে অবাক হয়ে তাকিয়ে ছিল!"
        ],
        "joke_ask_more": " আপনি কি আরেকটি শুনতে চান?",
        "joke_out": "আমার কাছে নতুন কোনো জোকস নেই! আমাকে নতুন কিছু ভাবার জন্য সময় দিন।",
        "thanks": [
            "আপনাকে স্বাগতম! আমি কি অন্য কিছুতে সাহায্য করতে পারি?", "আমার আনন্দ! আপনি আর কি জানতে চান?",
            "সাহায্য করতে পেরে খুশি! অন্য কিছু লাগলে জানাবেন।", "সবসময়! আমি এজন্যই এখানে আছি।"
        ],
        "capabilities": [
            "আমি সময় বলতে পারি, জোকস বলতে পারি, বিভিন্ন বিষয়ে চ্যাট করতে পারি, অথবা শুধু একটি বন্ধুত্বপূর্ণ কথোপকথন করতে পারি। আপনার কিসে আগ্রহ?",
            "আমরা আলোচনা করতে পারি কিভাবে আমাকে তৈরি করা হয়েছে, আমি আপনাকে একটি জোক বলতে পারি, অথবা আমরা শুধু চ্যাট করতে পারি। আপনি কোনটি পছন্দ করবেন?",
            "আমি খুশি যে আমাদের কথোপকথন চালিয়ে যেতে পারি! আমরা আমার ক্ষমতা নিয়ে আলোচনা করতে পারি, আমি আপনাকে একটি জোক বলতে পারি, অথবা আমরা অন্য কিছু নিয়ে চ্যাট করতে পারি।"
        ],
        "about_you": [
            "আমি শ্যাডো বট, একটি ভয়েস অ্যাসিস্ট্যান্ট যা বিভিন্ন কাজে সাহায্য করার জন্য এবং কথোপকথন করার জন্য ডিজাইন করা হয়েছে। আমি স্বাভাবিক ভাষা বুঝতে পারি এবং আমাদের কথোপকথনের প্রসঙ্গ মনে রাখতে পারি।",
            "আমি শ্যাডো বট নামক একটি এআই অ্যাসিস্ট্যান্ট। আমাকে সহায়ক কথোপকথন করার জন্য এবং সময় বলা বা জোকস শেয়ার করার মতো সহজ কাজগুলিতে সহায়তা করার জন্য তৈরি করা হয়েছে।",
            "আমি শ্যাডো বট, একটি ভয়েস-নিয়ন্ত্রিত সহকারী। আপনি যা বলেন তা বোঝার জন্য আমি স্পিচ রিকগনিশন এবং প্রতিক্রিয়া জানাতে টেক্সট-টু-স্পিচ ব্যবহার করি। আমি সাহায্য এবং চ্যাট করার জন্য এখানে আছি!"
        ],
        "how_made": [
            "আমাকে পাইথন ব্যবহার করে স্পিচ রিকগনিশন এবং টেক্সট-টু-স্পিচ লাইব্রেরি দিয়ে তৈরি করা হয়েছে। আমার মস্তিষ্ক একটি প্রোগ্রাম যা ভাষা প্রক্রিয়া করে এবং প্রসঙ্গের উপর ভিত্তি করে প্রতিক্রিয়া জানাতে টেক্সট-টু-স্পিচ ব্যবহার করে। আমাকে স্বাভাবিক কথোপকথন করার জন্য ডিজাইন করা হয়েছে।"
        ],
        "weather": [
            "আমার কাছে রিয়েল-টাইম আবহাওয়ার ডেটা অ্যাক্সেস নেই, তবে আমি অন্যান্য বিষয়ে কথা বলতে পেরে খুশি হব!",
            "দুর্ভাগ্যবশত, আমি আপনার জন্য আবহাওয়া পরীক্ষা করতে পারছি না। আমি কি অন্য কিছুতে সাহায্য করতে পারি?",
            "আমার এখনও আবহাওয়ার ক্ষমতা নেই, তবে আমি সবসময় নতুন দক্ষতা শিখছি!"
        ],
        "exit": [
            "বিদায়! আপনার সাথে কথা বলে ভালো লাগলো।", "পরে দেখা হবে! আপনার দিনটি ভালো কাটুক।",
            "বিদায়! আপনার আবার প্রয়োজন হলে আমি এখানে থাকব।", "বন্ধ হচ্ছে। আপনার সাথে কথা বলাটা আনন্দের ছিল!"
        ],
        "yes_generic": "দারুণ! আপনি কি বিষয়ে কথা বলতে চান?",
        "no_generic": "আচ্ছা। আপনি কি অন্য কিছু আলোচনা করতে চান?",
        "why": [
            "এটি একটি মজার প্রশ্ন! আমাকে সহায়ক হওয়ার জন্য এইভাবে প্রতিক্রিয়া জানাতে ডিজাইন করা হয়েছে।",
            "আমি যতটা সম্ভব প্রাসঙ্গিক তথ্য সরবরাহ করার জন্য প্রোগ্রাম করা হয়েছি।",
            "ভালো প্রশ্ন! আমার প্রতিক্রিয়াগুলি আমার প্রোগ্রামিং এবং কথোপকথনের প্রসঙ্গের উপর ভিত্তি করে।"
        ],
        "what_else": [
            "আমি সময় বলতে পারি, জোকস বলতে পারি, বিভিন্ন বিষয়ে চ্যাট করতে পারি, অথবা শুধু একটি বন্ধুত্বপূর্ণ কথোপকথন করতে পারি। আপনার কিসে আগ্রহ?",
            "আমরা আলোচনা করতে পারি কিভাবে আমাকে তৈরি করা হয়েছে, আমি আপনাকে একটি জোক বলতে পারি, অথবা আমরা শুধু চ্যাট করতে পারি। আপনি কোনটি পছন্দ করবেন?",
            "আমি খুশি যে আমাদের কথোপকথন চালিয়ে যেতে পারি! আমরা আমার ক্ষমতা নিয়ে আলোচনা করতে পারি, আমি আপনাকে একটি জোক বলতে পারি, অথবা আমরা অন্য কিছু নিয়ে চ্যাট করতে পারি।"
        ],
        "unknown": [
            "আমি ঠিক বুঝতে পারছি না। আপনি কি অন্যভাবে বলতে পারবেন?",
            "আমি এখনও শিখছি এবং এটা ঠিক ধরতে পারিনি। আপনি কি বিষয়ে কথা বলতে চান?",
            "হুম, আমি এর সাথে পরিচিত নই। আপনি কি জানতে চান আমি কি করতে পারি?",
            "আমি এটা পুরোপুরি বুঝতে পারিনি। আপনি কি অন্য কিছু নিয়ে চ্যাট করতে চান?",
            "আমাকে এখনও এটি বোঝার জন্য প্রোগ্রাম করা হয়নি, তবে আমি সবসময় শিখছি! আপনি আর কি আলোচনা করতে চান?"
        ],
        "unknown_personalized": "আমি দুঃখিত, {name}, আমি এটা ঠিক বুঝতে পারিনি। আপনি কি অন্যভাবে বলার চেষ্টা করবেন?",
        "followup_name": "যাইহোক, আপনার নাম কি?",
        "followup_how_are_you": "আপনি আজ কেমন আছেন?",
        "idle_prompt1": "আপনার যদি কিছুর প্রয়োজন হয় তবে আমি এখনও এখানে আছি।",
        "idle_prompt2": "আপনি চ্যাট করতে চাইলে শুধু আমাকে জানান।",
        "no_command": "আমি কিছু শুনতে পাইনি। আপনি কি দয়া করে পুনরাবৃত্তি করবেন?",
        "wake_word_listening": "আমি শুনছি",
        "wake_word_enabled_msg": "ওয়েক ওয়ার্ড সনাক্তকরণ সক্রিয় করা হয়েছে। আমাকে সক্রিয় করতে {wake_word} বলুন।",
        "activated_msg": "শ্যাডো বট সক্রিয় এবং প্রস্তুত।",
        "initial_greeting": "আমি এখানে চ্যাট করতে এবং আপনাকে সাহায্য করতে এসেছি। নির্দ্বিধায় আমাকে প্রশ্ন জিজ্ঞাসা করুন বা শুধু একটি কথোপকথন করুন!",
        "interrupt_msg": "বাধা সনাক্ত করা হয়েছে। বন্ধ করা হচ্ছে।",
        "error_loop_msg": "আমি একটি ত্রুটি সম্মুখীন হয়েছি। আমাকে আমার শোনার প্রক্রিয়া পুনরায় চালু করতে দিন।",
        "shutdown_msg": "শ্যাডো বট বন্ধ হয়ে গেছে। বিদায়!",
        "goodbye_msg": "শ্যাডো বট বন্ধ হয়ে গেছে। বিদায়, {name}!",
        "critical_error_msg": "একটি গুরুতর ত্রুটি ঘটেছে। শ্যাডো বট অবশ্যই বন্ধ করতে হবে।",
        "gemini_error": "দুঃখিত, আমি এই মুহূর্তে আমার জ্ঞান ভান্ডারের সাথে সংযোগ করতে পারছি না।",
        "generic_error": "দুঃখিত, একটি অভ্যন্তরীণ ত্রুটি ঘটেছে।"
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
    for attempt in range(MAX_RETRY_ATTEMPTS): # Use variable directly
        try:
            return operation_func(*args, **kwargs)
        except Exception as e:
            print(f"Operation failed (attempt {attempt+1}/{MAX_RETRY_ATTEMPTS}): {e}") # Use variable directly
            if attempt < MAX_RETRY_ATTEMPTS - 1: # Use variable directly
                print(f"Retrying in {RETRY_DELAY} seconds...") # Use variable directly
                time.sleep(RETRY_DELAY) # Use variable directly
            else:
                print("Maximum retry attempts reached. Operation failed.")
                return None

# --- Core Functions ---

def speak(text, lang_code=DEFAULT_LANGUAGE):
    """Converts text to speech using gTTS and plays it using pydub."""
    lang_config = SUPPORTED_LANGUAGES.get(lang_code, SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE])
    tts_code = lang_config['tts']
    print(f"Shadow Bot ({tts_code}): {text}") # Print what the bot intends to say

    def _speak_operation():
        tts = gTTS(text=text, lang=tts_code, slow=False)
        with tempfile.NamedTemporaryFile(delete=True, suffix=".mp3") as fp:
            temp_path = fp.name
            tts.save(temp_path)
            # Load the audio file using pydub
            sound = AudioSegment.from_mp3(temp_path)
            # Play the audio file
            play(sound)
        return True # Indicate success

    # Retry the speak operation if it fails
    result = retry_operation(_speak_operation)
    if result is None:
        fallback_lang_config = SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE]
        fallback_tts_code = fallback_lang_config['tts']
        print(f"Failed to speak in {tts_code}. Using fallback print method.")
        # Fallback: Just print the text if audio fails completely
        # print(f"Shadow Bot ({fallback_tts_code}) would say: {text}") # Already printed above

def listen_for_audio(timeout=5, phrase_time_limit=10, adjust_noise=True):
    """
    Base function to listen for audio input.
    """
    r = sr.Recognizer()
    # Apply microphone settings from config
    r.pause_threshold = PAUSE_THRESHOLD 
    if not DYNAMIC_ENERGY_THRESHOLD:
        # Only set manually if dynamic adjustment is disabled
        try:
           # Check if ENERGY_THRESHOLD is defined (might be commented out)
           r.energy_threshold = ENERGY_THRESHOLD 
        except NameError:
           print("Warning: DYNAMIC_ENERGY_THRESHOLD is False, but ENERGY_THRESHOLD is not defined. Using default.")
           # Let the library use its default if ENERGY_THRESHOLD isn't set

    with sr.Microphone() as source:
        if adjust_noise and DYNAMIC_ENERGY_THRESHOLD: # Only adjust dynamically if enabled
            print(f"Adjusting for ambient noise ({ADJUST_NOISE_DURATION} sec)...")
            r.adjust_for_ambient_noise(source, duration=ADJUST_NOISE_DURATION)
            print(f"Dynamic energy threshold set to: {r.energy_threshold:.2f}")
        elif not DYNAMIC_ENERGY_THRESHOLD:
             print(f"Using fixed energy threshold: {r.energy_threshold}")


        try:
            print(f"Listening... (Timeout: {timeout}s, Pause Threshold: {r.pause_threshold}s, Phrase Limit: {phrase_time_limit}s)")
            # Pass phrase_time_limit to r.listen
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
    Attempt to recognize speech in supported languages.
    """
    if audio is None:
        return None, None

    # Initialize recognizer and Kaldi recognizer
    r = sr.Recognizer()
    try:
        # Use raw audio data
        # Convert audio data to raw data
        raw_data = audio.get_raw_data(convert_rate=16000, convert_width=2)

        # Create a Kaldi recognizer
        kaldi_rec = vosk.KaldiRecognizer(vosk_model, 16000)

        # Recognize speech using Vosk
        kaldi_rec.AcceptWaveform(raw_data)
        result = kaldi_rec.Result()
        recognized_text = result
        detected_lang = DEFAULT_LANGUAGE # Since Vosk doesn't directly detect language, default to the configured language

        # Extract recognized text
        recognized_text = result.split('"text": "')[1].split('"}')[0].strip()
        print(f"Vosk recognized: {recognized_text}")
        return recognized_text, detected_lang

    except Exception as e:
        print(f"Error during offline speech recognition (Vosk): {e}")
        return None, None

def listen_for_wake_word():
    """
    Listen specifically for wake words using the configured wake word STT language.
    """
    if not WAKE_WORD_ENABLED: # Use variable directly
        return True  # Skip wake word detection if disabled

    wake_word_stt_lang = WAKE_WORD_LANG_STT # Use variable directly
    print(f"Listening for wake word in {wake_word_stt_lang}...")

    r_wake = sr.Recognizer()
    for attempt in range(MAX_RETRY_ATTEMPTS): # Use variable directly
        audio = listen_for_audio(timeout=None, phrase_time_limit=3, adjust_noise=(attempt == 0))
        if audio is None:
            continue

        try:
            # Use the specific wake word STT language recognizer
            text = r_wake.recognize_google(audio, language=wake_word_stt_lang)
            print(f"Wake word attempt recognized: {text}")
            text_lower = text.lower()
            # Check if any English wake word is in the recognized text
            # Assuming wake words in config are English for simplicity
            if any(wake_word in text_lower for wake_word in WAKE_WORDS): # Use variable directly
                print(f"Wake word detected: {text}")
                return True
        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            print(f"Wake word recognition request failed ({wake_word_stt_lang}); {e}")
            continue
        except Exception as e:
            print(f"Error during wake word recognition ({wake_word_stt_lang}): {e}")
            continue

    print("Wake word not detected.")
    return False

def listen_for_command():
    """
    Listens for a command after wake word (if enabled), attempts recognition
    in supported languages, and detects language.
    """
    # First check for wake word if enabled
    if WAKE_WORD_ENABLED: # Use variable directly
        if not listen_for_wake_word():
            return None, None # No wake word detected
        # Speak confirmation in default language after wake word
        speak(get_response_string("wake_word_listening", DEFAULT_LANGUAGE), lang_code=DEFAULT_LANGUAGE) # Use variable directly

    # Listen for the actual command
    print("Listening for command...")
    audio = listen_for_audio(timeout=WAKE_WORD_TIMEOUT if WAKE_WORD_ENABLED else 5, phrase_time_limit=PHRASE_TIME_LIMIT, adjust_noise=DYNAMIC_ENERGY_THRESHOLD) # Use variables directly

    # Recognize speech in supported languages
    recognized_text, detected_lang_code = recognize_speech(audio)

    # Optional: Use langdetect as a fallback or confirmation if recognition worked
    if recognized_text:
        try:
            detected_lang_by_lib = detect(recognized_text)
            print(f"Langdetect detected: {detected_lang_by_lib}")
            # You could add logic here to override recognizer's language if langdetect strongly disagrees
            # For now, we trust the recognizer's result if it succeeded.
            if detected_lang_by_lib not in SUPPORTED_LANGUAGES: # Use variable directly
                 print(f"Warning: Langdetect result '{detected_lang_by_lib}' not in supported languages.")
                 # Stick with the language from successful recognition or default
                 detected_lang_code = detected_lang_code or DEFAULT_LANGUAGE # Use variable directly
            elif detected_lang_code is None: # If recognition failed but langdetect worked
                 # Trust langdetect if STT failed but detection worked
                 if detected_lang_by_lib in SUPPORTED_LANGUAGES: # Use variable directly
                    detected_lang_code = detected_lang_by_lib

        except LangDetectException:
            print("Language detection failed.")
            # If detection fails, use the language from recognition if available, else default
            detected_lang_code = detected_lang_code or DEFAULT_LANGUAGE # Use variable directly

    # If recognition failed entirely, detected_lang_code will be None
    # If recognition succeeded, detected_lang_code has the language code (short code like 'en' or 'bn')

    # Ensure we always return a valid language code from our supported list, defaulting if necessary
    final_lang_code = detected_lang_code if detected_lang_code in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    
    return recognized_text, final_lang_code

def match_command(command_text, lang_code):
    """
    Match the command text to the closest command template for the given language.
    """
    if command_text is None or lang_code not in command_templates:
        return None, 0

    lang_templates = command_templates[lang
