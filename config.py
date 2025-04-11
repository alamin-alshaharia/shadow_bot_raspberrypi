# Configuration settings for Shadow Bot

# Supported Languages
# Define the languages the bot can understand and speak
# Format: { "short_code": "google_tts_code" }
# Note: SpeechRecognition uses BCP-47 codes (e.g., "bn-BD"), gTTS uses simpler codes (e.g., "bn")
SUPPORTED_LANGUAGES = {
    "en": {"tts": "en", "stt": "en-US"},  # English
    "bn": {"tts": "bn", "stt": "bn-BD"}   # Bengali (Bangladesh)
}
DEFAULT_LANGUAGE = "en" # Default language if detection fails or for initial messages

# Gemini API key configuration
GEMINI_API_KEY = "AIzaSyBY88kNHfPUqauW2z5wu5-qnBv1Kr4d86s"

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
