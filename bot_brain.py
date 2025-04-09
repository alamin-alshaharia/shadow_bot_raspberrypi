import speech_recognition as sr
from gtts import gTTS
import playsound
import os
import time
import config  # Import the configuration file
from fuzzywuzzy import process
from collections import deque
import random
import re # Import regex for name extraction
from langdetect import detect, LangDetectException # Import langdetect

# --- Context Memory ---
context_memory = deque(maxlen=config.CONTEXT_MEMORY_SIZE)

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
        "how_made": ["how were you made", "who made you", "who created you", "your creator", "how were you created"],
        "yes": ["yes", "yeah", "sure", "absolutely", "correct", "that's right", "yep", "ok", "okay"],
        "no": ["no", "nope", "not really", "i don't think so", "negative", "not at all"],
        "why": ["why", "why is that", "how come", "for what reason", "explain why"],
        "what_else": ["what else", "tell me more", "continue", "go on", "anything else", "more information"]
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
        "shutdown_msg": "Shadow Bot shutting down.",
        "goodbye_msg": "Shadow Bot has shut down. Goodbye!",
        "goodbye_personalized": "Shadow Bot has shut down. Goodbye, {name}!",
        "critical_error_msg": "A critical error occurred. Shadow Bot must shut down."
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
            "আমি সময় বলতে পারি, জোকস বলতে পারি, আপনার সাথে কথা বলতে পারি এবং সাধারণ প্রশ্নের উত্তর দিতে পারি। আমি সবসময় নতুন জিনিস শিখছি! আপনি কি চান আমি করি?",
            "আমি একজন ভয়েস অ্যাসিস্ট্যান্ট যে কথা বলতে পারে, সময় বলতে পারে, জোকস শেয়ার করতে পারে এবং আমাদের চ্যাটের প্রসঙ্গ মনে রাখতে পারে। আমি কিভাবে আপনাকে সাহায্য করতে পারি?",
            "আমি স্বাভাবিক ভাষা বুঝতে পারি, আমাদের কথোপকথনের প্রসঙ্গ মনে রাখতে পারি, জোকস বলতে পারি এবং বিভিন্ন কমান্ডের উত্তর দিতে পারি। আপনি কি চেষ্টা করতে চান?"
        ],
        "about_you": [
            "আমি শ্যাডো বট, একটি ভয়েস অ্যাসিস্ট্যান্ট যা বিভিন্ন কাজে সাহায্য করার জন্য এবং কথোপকথন করার জন্য ডিজাইন করা হয়েছে। আমি স্বাভাবিক ভাষা বুঝতে পারি এবং আমাদের কথোপকথনের প্রসঙ্গ মনে রাখতে পারি।",
            "আমি শ্যাডো বট নামক একটি এআই অ্যাসিস্ট্যান্ট। আমাকে সহায়ক কথোপকথন করার জন্য এবং সময় বলা বা জোকস শেয়ার করার মতো সহজ কাজগুলিতে সহায়তা করার জন্য তৈরি করা হয়েছে।",
            "আমি শ্যাডো বট, একটি ভয়েস-নিয়ন্ত্রিত সহকারী। আপনি যা বলেন তা বোঝার জন্য আমি স্পিচ রিকগনিশন এবং প্রতিক্রিয়া জানাতে টেক্সট-টু-স্পিচ ব্যবহার করি। আমি সাহায্য এবং চ্যাট করার জন্য এখানে আছি!"
        ],
        "how_made": [
            "আমাকে পাইথন ব্যবহার করে স্পিচ রিকগনিশন এবং টেক্সট-টু-স্পিচ লাইব্রেরি দিয়ে তৈরি করা হয়েছে। আমার মস্তিষ্ক একটি প্রোগ্রাম যা ভাষা প্রক্রিয়া করে এবং প্রসঙ্গের উপর ভিত্তি করে প্রতিক্রিয়া তৈরি করে।",
            "আমাকে পাইথন প্রোগ্রামিং ভাষা দিয়ে তৈরি করা হয়েছে, কমান্ড বোঝার জন্য স্পিচ রিকগনিশন এবং প্রতিক্রিয়া জানাতে টেক্সট-টু-স্পিচ ব্যবহার করে। আমাকে স্বাভাবিক কথোপকথন করার জন্য ডিজাইন করা হয়েছে।",
            "আমার স্রষ্টা আমাকে পাইথন ব্যবহার করে স্পিচরিকগনিশন এবং জিটিটিএস-এর মতো লাইব্রেরি দিয়ে তৈরি করেছেন। আমাকে স্বাভাবিক ভাষা বোঝার জন্য এবং কথোপকথনের প্রসঙ্গ বজায় রাখার জন্য ডিজাইন করা হয়েছে।"
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
            "আমি আমাদের কথোপকথন চালিয়ে যেতে পেরে খুশি! আমরা আমার ক্ষমতা নিয়ে আলোচনা করতে পারি, আমি আপনাকে একটি জোক বলতে পারি, অথবা আমরা অন্য কিছু নিয়ে চ্যাট করতে পারি।"
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
        "shutdown_msg": "শ্যাডো বট বন্ধ হচ্ছে।",
        "goodbye_msg": "শ্যাডো বট বন্ধ হয়ে গেছে। বিদায়!",
        "goodbye_personalized": "শ্যাডো বট বন্ধ হয়ে গেছে। বিদায়, {name}!",
        "critical_error_msg": "একটি গুরুতর ত্রুটি ঘটেছে। শ্যাডো বট অবশ্যই বন্ধ করতে হবে।"
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

def speak(text, lang_code=config.DEFAULT_LANGUAGE):
    """Converts text to speech in the specified language and plays it."""
    google_tts_code = config.SUPPORTED_LANGUAGES.get(lang_code, config.SUPPORTED_LANGUAGES[config.DEFAULT_LANGUAGE])
    
    def _speak_operation():
        print(f"Shadow Bot ({google_tts_code}): {text}")
        tts = gTTS(text=text, lang=google_tts_code, slow=False)
        tts.save(config.AUDIO_FILE)
        playsound.playsound(config.AUDIO_FILE)
        os.remove(config.AUDIO_FILE)
        return True
    
    result = retry_operation(_speak_operation)
    if result is None:
        # Fallback message in default language
        fallback_lang_code = config.SUPPORTED_LANGUAGES[config.DEFAULT_LANGUAGE]
        print(f"Failed to speak in {google_tts_code}. Using fallback method.")
        print(f"Shadow Bot ({fallback_lang_code}) would say: {text}")

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
    Attempt to recognize speech in supported languages.
    
    Args:
        audio: Audio data to recognize
        
    Returns:
        Tuple of (recognized_text, detected_language_code) or (None, None)
    """
    if audio is None:
        return None, None
        
    r = sr.Recognizer()
    recognized_text = None
    detected_lang = None

    # Try recognizing in each supported language
    for lang_code, google_code in config.SUPPORTED_LANGUAGES.items():
        try:
            print(f"Attempting recognition in {google_code}...")
            text = r.recognize_google(audio, language=google_code)
            print(f"Recognized as {google_code}: {text}")
            # Simple approach: return the first successful recognition
            # More complex logic could compare confidence scores if available
            recognized_text = text.lower()
            detected_lang = lang_code
            break # Stop after first successful recognition
        except sr.UnknownValueError:
            print(f"Could not understand audio as {google_code}.")
            continue # Try next language
        except sr.RequestError as e:
            print(f"Could not request results from Google ({google_code}); {e}")
            # Potentially stop trying if it's a network error? For now, continue.
            continue 
        except Exception as e:
            print(f"Error during {google_code} speech recognition: {e}")
            continue

    return recognized_text, detected_lang

def listen_for_wake_word():
    """
    Listen specifically for wake words using the configured wake word language.
    
    Returns:
        True if a wake word was detected, False otherwise
    """
    if not config.WAKE_WORD_ENABLED:
        return True  # Skip wake word detection if disabled
        
    print(f"Listening for wake word in {config.WAKE_WORD_LANG}...")
    
    r_wake = sr.Recognizer()
    for attempt in range(config.MAX_RETRY_ATTEMPTS):
        audio = listen_for_audio(timeout=None, phrase_time_limit=3, adjust_noise=(attempt == 0))
        if audio is None:
            continue
            
        try:
            # Use the specific wake word language recognizer
            text = r_wake.recognize_google(audio, language=config.WAKE_WORD_LANG) 
            print(f"Wake word attempt recognized: {text}")
            text_lower = text.lower()
            # Check if any wake word is in the recognized text
            if any(wake_word in text_lower for wake_word in config.WAKE_WORDS):
                print(f"Wake word detected: {text}")
                return True
        except sr.UnknownValueError:
            # Ignore if wake word attempt is not understood
            pass 
        except sr.RequestError as e:
            print(f"Wake word recognition request failed ({config.WAKE_WORD_LANG}); {e}")
            # Continue trying
        except Exception as e:
            print(f"Error during wake word recognition ({config.WAKE_WORD_LANG}): {e}")
            # Continue trying
            
    print("Wake word not detected.")
    return False

def listen_for_command():
    """
    Listens for a command after wake word (if enabled), attempts recognition 
    in supported languages, and detects language.
    
    Returns:
        Tuple of (recognized_text, detected_language_code) or (None, None)
    """
    # First check for wake word if enabled
    if config.WAKE_WORD_ENABLED:
        if not listen_for_wake_word():
            return None, None # No wake word detected
        # Speak confirmation in default language after wake word
        speak("I'm listening", lang_code=config.DEFAULT_LANGUAGE) 
    
    # Listen for the actual command
    print("Listening for command...")
    audio = listen_for_audio(timeout=config.WAKE_WORD_TIMEOUT if config.WAKE_WORD_ENABLED else 5)
    
    # Recognize speech in supported languages
    recognized_text, detected_lang_code = recognize_speech(audio)

    # Optional: Use langdetect as a fallback or confirmation if recognition worked
    if recognized_text:
        try:
            detected_lang_by_lib = detect(recognized_text)
            print(f"Langdetect detected: {detected_lang_by_lib}")
            # You could add logic here to override recognizer's language if langdetect strongly disagrees
            # For now, we trust the recognizer's result if it succeeded.
            if detected_lang_by_lib not in config.SUPPORTED_LANGUAGES:
                 print(f"Warning: Langdetect result '{detected_lang_by_lib}' not in supported languages.")
                 # Stick with the language from successful recognition or default
                 detected_lang_code = detected_lang_code or config.DEFAULT_LANGUAGE
            elif detected_lang_code is None: # If recognition failed but langdetect worked
                 detected_lang_code = detected_lang_by_lib

        except LangDetectException:
            print("Language detection failed.")
            # If detection fails, use the language from recognition if available, else default
            detected_lang_code = detected_lang_code or config.DEFAULT_LANGUAGE
            
    # If recognition failed entirely, detected_lang_code will be None
    # If recognition succeeded, detected_lang_code has the language code

    return recognized_text, detected_lang_code or config.DEFAULT_LANGUAGE # Return default if still None

def match_command(command_text, lang_code):
    """
    Match the command text to the closest command template for the given language.
    
    Args:
        command_text: The text to match
        lang_code: The language code ('en', 'bn', etc.)
        
    Returns:
        Tuple of (command_type, confidence) or (None, 0) if no match
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
            
    if best_confidence >= config.COMMAND_SIMILARITY_THRESHOLD * 100:
        return best_match, best_confidence
    else:
        return None, 0

# --- Conversation State ---
conversation_state = {
    "current_topic": None,
    "expecting_response": False,
    "last_question": None,
    "user_name": None,
    "session_start_time": time.time()
}

def extract_user_name(command, lang_code):
    """
    Extract a user's name from commands in the specified language.
    
    Args:
        command: The command text
        lang_code: The language code ('en', 'bn')
        
    Returns:
        The extracted name or None if no name found
    """
    # Basic patterns - can be expanded
    patterns = {
        "en": [
            r"(?:my name is|i am|i'm|call me) ([a-z]+)", 
            r"([a-z]+) is my name"
        ],
        "bn": [
            r"(?:আমার নাম|আমি হলাম|আমাকে ডাকবে) ([^\s]+)", # Matches Bengali name patterns
            r"([^\s]+) আমার নাম"
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

def get_response_string(key, lang_code, **kwargs):
    """
    Retrieve a response string for the given key and language, performing formatting.
    Handles fallback to default language if the key or language is missing.
    """
    lang_to_use = lang_code if lang_code in responses else config.DEFAULT_LANGUAGE
    
    response_options = responses.get(lang_to_use, {}).get(key)
    
    # Fallback to default language if key not found in specified language
    if response_options is None and lang_to_use != config.DEFAULT_LANGUAGE:
        print(f"Warning: Response key '{key}' not found for language '{lang_to_use}'. Falling back to default.")
        lang_to_use = config.DEFAULT_LANGUAGE
        response_options = responses.get(lang_to_use, {}).get(key)

    if response_options is None:
        print(f"Error: Response key '{key}' not found even in default language '{config.DEFAULT_LANGUAGE}'.")
        # Return a generic error message in the intended language or default
        error_lang = lang_code if lang_code in responses else config.DEFAULT_LANGUAGE
        return responses.get(error_lang, {}).get("unknown", ["Sorry, I encountered an error."])[0]

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
    
    Args:
        command_type: The type of command detected
        command_text: The actual text of the command
        lang_code: The detected language code ('en', 'bn')
        
    Returns:
        Tuple of (response_text, should_ask_followup)
    """
    recent_command_types = [item["command_type"] for item in context_memory]
    repetition = recent_command_types.count(command_type) if command_type else 0
    should_ask_followup = False
    response_text = ""

    # --- Handle response to previous question ---
    if conversation_state["expecting_response"] and conversation_state["last_question"]:
        last_q = conversation_state["last_question"]
        conversation_state["expecting_response"] = False # Reset flag

        if last_q == "name" and command_type in ["user_name", "yes", "no"]:
            name = extract_user_name(command_text, lang_code)
            if name:
                conversation_state["user_name"] = name
                response_text = get_response_string("user_name_confirm", lang_code, name=name)
            else: # Failed to extract name
                response_text = get_response_string("user_name_fail", lang_code)
            return response_text, False # Don't ask another follow-up immediately

        elif last_q == "how_are_you" and command_type:
            if command_type in ["greeting", "how_are_you", "yes"]:
                response_text = get_response_string("how_are_you_resp_glad", lang_code)
            elif command_type == "no":
                 response_text = get_response_string("how_are_you_resp_sorry", lang_code)
                 should_ask_followup = True # Maybe ask if we can help
            else: # Unclear response to "how are you?"
                 response_text = get_response_string("unknown", lang_code)
            return response_text, should_ask_followup
        
        elif last_q == "another_joke":
             if command_type == "yes":
                 command_type = "joke" # Trigger another joke
             else:
                 response_text = get_response_string("no_generic", lang_code)
                 return response_text, False


    # --- Handle specific command types ---
    if command_type == "greeting":
        base_greetings = responses.get(lang_code, responses[config.DEFAULT_LANGUAGE]).get("greeting", [])
        if conversation_state["user_name"]:
            # Attempt personalized greeting (simple format for now)
            personalized_greeting = f"{random.choice(base_greetings).split('!')[0]}, {conversation_state['user_name']}!"
            response_text = personalized_greeting + get_response_string("greeting", lang_code).split('!')[1] # Add the second part like "How can I help?"
        else:
             response_text = random.choice(base_greetings)

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
        jokes_list = responses.get(lang_code, responses[config.DEFAULT_LANGUAGE]).get("joke", [])
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
             response_text = get_response_string("exit", lang_code) # Use generic exit if name unknown
    
    elif command_type == "yes" and not conversation_state["last_question"]:
        response_text = get_response_string("yes_generic", lang_code)
    elif command_type == "no" and not conversation_state["last_question"]:
        response_text = get_response_string("no_generic", lang_code)
    
    elif command_type == "why":
        response_text = get_response_string("why", lang_code)
    
    elif command_type == "what_else":
        response_text = get_response_string("what_else", lang_code)
        
    # --- Unknown command ---
    else: 
        name = conversation_state.get("user_name")
        if name and random.random() < 0.3:
            response_text = get_response_string("unknown_personalized", lang_code, name=name)
        else:
            response_text = get_response_string("unknown", lang_code)

    return response_text, should_ask_followup

def generate_follow_up_question(lang_code):
    """
    Generate a follow-up question in the specified language based on context.
    
    Returns:
        A follow-up question string or None
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
    
    return None

def process_command(command, lang_code):
    """
    Processes the command text in the detected language.

    Args:
        command (str or None): The recognized command text.
        lang_code (str): The detected language code ('en', 'bn').

    Returns:
        bool: True to continue the main loop, False to exit.
    """
    if command is None:
        if config.WAKE_WORD_ENABLED:
            return True # Just continue listening after wake word timeout
        else:
            # Speak "didn't hear" in the last used language or default
            speak(get_response_string("no_command", lang_code), lang_code=lang_code)
            return True
            
    print(f"Processing command '{command}' in language '{lang_code}'")

    # Match command in the detected language
    command_type, confidence = match_command(command, lang_code)
    
    # Get response in the detected language
    response, should_ask_followup = get_contextual_response(command_type, command, lang_code)
    
    # Store interaction (including language)
    context_memory.append({
        "timestamp": time.time(),
        "command": command,
        "lang_code": lang_code,
        "command_type": command_type,
        "confidence": confidence,
        "response": response
    })
    
    # Speak the response in the detected language
    speak(response, lang_code=lang_code)
    
    # Ask follow-up question if needed, in the same language
    if should_ask_followup:
        follow_up = generate_follow_up_question(lang_code)
        if follow_up:
            time.sleep(0.5) 
            speak(follow_up, lang_code=lang_code)
    
    # Exit?
    if command_type == "exit":
        return False
        
    return True 

# --- Main Execution ---

if __name__ == "__main__":
    # Use default language for initial messages
    default_lang = config.DEFAULT_LANGUAGE
    
    try:
        conversation_state["session_start_time"] = time.time()
        
        speak(get_response_string("activated_msg", default_lang), lang_code=default_lang)
        
        if config.WAKE_WORD_ENABLED:
            speak(get_response_string("wake_word_enabled_msg", default_lang, wake_word=config.WAKE_WORDS[0]), lang_code=default_lang)
        
        time.sleep(0.5)
        speak(get_response_string("initial_greeting", default_lang), lang_code=default_lang)
        
        running = True
        idle_time = 0
        last_activity = time.time()
        last_lang_code = default_lang # Keep track of last used language for idle prompts

        while running:
            try:
                current_time = time.time()
                # Idle prompts in the last used language
                if current_time - last_activity > 30 and idle_time == 0:
                    speak(get_response_string("idle_prompt1", last_lang_code), lang_code=last_lang_code)
                    idle_time += 1
                elif current_time - last_activity > 60 and idle_time == 1:
                    speak(get_response_string("idle_prompt2", last_lang_code), lang_code=last_lang_code)
                    idle_time += 1
                
                # Listen for command and detect language
                command, lang_code = listen_for_command()
                
                if command is not None:
                    last_activity = time.time()
                    idle_time = 0
                    last_lang_code = lang_code # Update last used language
                
                # Process command using detected language
                running = process_command(command, lang_code) 
                
                time.sleep(0.1)
                
            except KeyboardInterrupt:
                speak(get_response_string("interrupt_msg", last_lang_code), lang_code=last_lang_code)
                running = False
            except Exception as e:
                print(f"Error in main loop: {e}")
                speak(get_response_string("error_loop_msg", last_lang_code), lang_code=last_lang_code)
                time.sleep(1) 
                
        print(get_response_string("shutdown_msg", last_lang_code))
        
        # Final goodbye in last used language
        name = conversation_state.get("user_name")
        if name:
            speak(get_response_string("goodbye_personalized", last_lang_code, name=name), lang_code=last_lang_code)
        else:
            speak(get_response_string("goodbye_msg", last_lang_code), lang_code=last_lang_code)
        
    except Exception as e:
        print(f"Critical error: {e}")
        # Try to speak error in default language
        speak(get_response_string("critical_error_msg", default_lang), lang_code=default_lang)
