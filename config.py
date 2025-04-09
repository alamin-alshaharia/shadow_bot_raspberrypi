# Configuration settings for Shadow Bot

# Language for STT and TTS
LANGUAGE = "en"

# Temporary file path for TTS audio output
AUDIO_FILE = "response.mp3"

# Wake word settings
WAKE_WORD_ENABLED = True
WAKE_WORDS = ["hey shadow bot", "shadow bot", "hey shadow", "shadow"]
WAKE_WORD_TIMEOUT = 10  # Seconds to listen for a command after wake word

# Command parsing settings
COMMAND_SIMILARITY_THRESHOLD = 0.7  # Threshold for fuzzy matching commands (0.0 to 1.0)

# Contextual conversation settings
CONTEXT_MEMORY_SIZE = 5  # Number of previous interactions to remember

# Error handling settings
MAX_RETRY_ATTEMPTS = 3  # Maximum number of retries for failed operations
RETRY_DELAY = 2  # Seconds to wait between retries
