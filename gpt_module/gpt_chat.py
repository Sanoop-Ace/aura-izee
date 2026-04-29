"""
gpt_module/gpt_chat.py — Mock GPT Student AI Assistant
When you get a real OpenAI API key, replace the mock_gpt_response
function with the real OpenAI API call shown at the bottom.
"""

import random
from datetime import datetime

# ── Mock responses by topic ───────────────────────────────────────────────────
MOCK_RESPONSES = {
    "study": [
        "Great question! Here are some effective study tips:\n\n📚 **Active Recall** — Test yourself instead of re-reading notes.\n⏱ **Pomodoro Technique** — Study 25 mins, break 5 mins.\n🗂 **Mind Maps** — Visualize connections between concepts.\n😴 **Sleep** — Memory consolidates during sleep, don't skip it!",
        "For better studying, try the **Feynman Technique**: explain the concept in simple words as if teaching a child. If you can't explain it simply, you don't understand it yet.",
    ],
    "exam": [
        "📝 **Exam Preparation Tips:**\n\n1. Start at least 2 weeks before\n2. Make a revision timetable\n3. Practice past papers\n4. Focus on weak areas first\n5. Get 8 hours sleep before exam day\n6. Eat a proper breakfast on exam day",
        "For exam success: **Past papers are your best friend!** They reveal patterns in questions and help you practice time management under pressure.",
    ],
    "career": [
        "🚀 **Career Tips for BCA Students:**\n\n• Build projects for your portfolio\n• Learn Git and GitHub\n• Practice DSA (Data Structures & Algorithms)\n• Get internship experience\n• Build a LinkedIn profile\n• Contribute to open source",
        "Top careers after BCA:\n💻 Software Developer\n🌐 Web Developer\n📊 Data Analyst\n☁️ Cloud Engineer\n🔒 Cybersecurity Analyst\n\nAll pay well and have high demand!",
    ],
    "code": [
        "Here are some coding tips:\n\n```\n# Always write clean, readable code\n# Use meaningful variable names\n# Comment your code\n# Test edge cases\n```\n\nRemember: **Code that works is good. Code that others can read is better.**",
        "For learning to code faster:\n\n1. Build real projects, not just tutorials\n2. Read other people's code on GitHub\n3. Debug without Stack Overflow first — try yourself!\n4. Code every day, even just 30 minutes",
    ],
    "python": [
        "Python tips for beginners:\n\n🐍 Python is beginner-friendly but powerful\n📦 Learn these libraries: NumPy, Pandas, Flask, Django\n🎯 Practice on HackerRank or LeetCode\n📁 Build projects: calculator, to-do app, web scraper",
        "**Python learning path:**\nBasics → Functions → OOP → File I/O → Libraries → Web Framework (Flask/Django) → Database → Deploy!\n\nYou're already using Flask — great start! 🎉",
    ],
    "stress": [
        "It's okay to feel stressed sometimes. Here are some tips:\n\n🧘 **Mindfulness** — 5 mins of deep breathing helps\n🚶 **Walk** — Even a 10-min walk clears your mind\n✅ **Break tasks** — Big tasks feel overwhelming, split them\n👥 **Talk** — Share with friends or family\n😴 **Sleep** — Everything feels worse when tired",
        "Student stress is real! Remember:\n\n• One step at a time\n• Progress over perfection\n• It's okay to ask for help\n• Take breaks — they make you more productive, not less\n\nYou've got this! 💪",
    ],
    "default": [
        "That's an interesting question! As your AI study assistant, I can help with:\n\n📚 Study techniques\n📝 Exam preparation\n💻 Coding help\n🚀 Career guidance\n🧘 Managing student stress\n\nWhat specific area would you like help with?",
        "I'm your Student AI Assistant! I can help with study tips, coding questions, career advice, and more. Could you be more specific about what you need help with?",
        "Great question! Let me think about that...\n\nAs a student AI assistant, I'm best at helping with:\n• Academic topics\n• Study strategies\n• Programming questions\n• Career planning\n\nCould you give me more details?",
    ]
}

def mock_gpt_response(user_message: str) -> str:
    """
    Generate a mock GPT-like response based on keywords.
    Replace this function with real OpenAI API when you have a key.
    """
    msg = user_message.lower()

    # Keyword matching for topic detection
    if any(w in msg for w in ['study', 'learn', 'notes', 'revision', 'focus']):
        return random.choice(MOCK_RESPONSES['study'])
    elif any(w in msg for w in ['exam', 'test', 'paper', 'marks', 'grade']):
        return random.choice(MOCK_RESPONSES['exam'])
    elif any(w in msg for w in ['career', 'job', 'salary', 'placement', 'future']):
        return random.choice(MOCK_RESPONSES['career'])
    elif any(w in msg for w in ['python', 'flask', 'django', 'program']):
        return random.choice(MOCK_RESPONSES['python'])
    elif any(w in msg for w in ['code', 'coding', 'debug', 'error', 'bug']):
        return random.choice(MOCK_RESPONSES['code'])
    elif any(w in msg for w in ['stress', 'anxious', 'worried', 'tired', 'help']):
        return random.choice(MOCK_RESPONSES['stress'])
    else:
        return random.choice(MOCK_RESPONSES['default'])


# ── REAL OpenAI API (uncomment when you have a key) ──────────────────────────
# import openai
# openai.api_key = "your-api-key-here"
#
# def real_gpt_response(user_message: str) -> str:
#     response = openai.ChatCompletion.create(
#         model="gpt-3.5-turbo",
#         messages=[
#             {"role": "system", "content": "You are a helpful student assistant for IZee Business School. Help students with studies, career, coding, and academic queries."},
#             {"role": "user", "content": user_message}
#         ]
#     )
#     return response.choices[0].message.content
