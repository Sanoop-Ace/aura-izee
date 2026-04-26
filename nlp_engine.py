"""
nlp_engine.py — AURA NLP Processing Module
Handles tokenization, keyword matching, and intent recognition using NLTK.
"""

import json
import os
import random
import re
import nltk

# ─── Download required NLTK data (runs once) ────────────────────────────────
def download_nltk_data():
    """Download required NLTK resources if not already present."""
    resources = ['punkt', 'stopwords', 'wordnet', 'averaged_perceptron_tagger']
    for resource in resources:
        try:
            nltk.data.find(f'tokenizers/{resource}' if resource == 'punkt' else f'corpora/{resource}')
        except LookupError:
            nltk.download(resource, quiet=True)

download_nltk_data()

from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

# ─── Load intents from JSON ──────────────────────────────────────────────────
INTENTS_PATH = os.path.join(os.path.dirname(__file__), 'intents.json')

with open(INTENTS_PATH, 'r', encoding='utf-8') as f:
    INTENTS_DATA = json.load(f)

# ─── Initialize NLP tools ────────────────────────────────────────────────────
lemmatizer = WordNetLemmatizer()
STOP_WORDS = set(stopwords.words('english'))

# Words to keep even if they are stopwords (important for our domain)
KEEP_WORDS = {'when', 'where', 'what', 'how', 'which', 'who', 'why', 'not', 'about'}
STOP_WORDS -= KEEP_WORDS


def preprocess(text: str) -> list[str]:
    """
    Preprocess input text:
    1. Lowercase
    2. Remove punctuation/special chars
    3. Tokenize
    4. Remove stopwords
    5. Lemmatize
    """
    text = text.lower().strip()
    text = re.sub(r"[^a-zA-Z0-9\s]", "", text)          # remove special chars
    tokens = word_tokenize(text)                           # tokenize
    tokens = [t for t in tokens if t not in STOP_WORDS]  # remove stopwords
    tokens = [lemmatizer.lemmatize(t) for t in tokens]   # lemmatize
    return tokens


def compute_similarity(user_tokens: list[str], pattern_tokens: list[str]) -> float:
    """
    Compute similarity score between user input tokens and a pattern.
    Uses Jaccard similarity with partial bonus for consecutive matches.
    """
    if not pattern_tokens or not user_tokens:
        return 0.0

    user_set = set(user_tokens)
    pattern_set = set(pattern_tokens)

    # Jaccard similarity
    intersection = user_set & pattern_set
    union = user_set | pattern_set
    jaccard = len(intersection) / len(union) if union else 0.0

    # Bonus: how many pattern words are covered
    coverage = len(intersection) / len(pattern_set) if pattern_set else 0.0

    # Weighted score
    score = (jaccard * 0.4) + (coverage * 0.6)
    return score


def classify_intent(user_input: str) -> dict:
    """
    Classify user input into an intent.
    Returns the best matching intent dictionary with a confidence score.
    """
    user_tokens = preprocess(user_input)

    best_intent = None
    best_score = 0.0
    THRESHOLD = 0.25  # minimum confidence to match

    for intent in INTENTS_DATA['intents']:
        if intent['tag'] == 'unknown':
            continue  # skip the fallback intent during matching

        for pattern in intent['patterns']:
            pattern_tokens = preprocess(pattern)
            score = compute_similarity(user_tokens, pattern_tokens)

            if score > best_score:
                best_score = score
                best_intent = intent

    # If confidence is too low, return the unknown/fallback intent
    if best_score < THRESHOLD or best_intent is None:
        fallback = next(i for i in INTENTS_DATA['intents'] if i['tag'] == 'unknown')
        return {
            'tag': 'unknown',
            'confidence': 0.0,
            'response': random.choice(fallback['responses'])
        }

    return {
        'tag': best_intent['tag'],
        'confidence': round(best_score, 3),
        'response': random.choice(best_intent['responses'])
    }


def get_response(user_input: str) -> dict:
    """
    Main entry point: process user input and return response dict.
    """
    if not user_input or not user_input.strip():
        return {
            'tag': 'empty',
            'confidence': 0.0,
            'response': 'Please type a message so I can help you! 😊'
        }

    result = classify_intent(user_input)
    return result


# ─── Quick test when run directly ───────────────────────────────────────────
if __name__ == '__main__':
    test_queries = [
        "When are exams?",
        "What is the fee structure?",
        "Tell me about courses",
        "How to apply for admission?",
        "What is the library timing?",
        "blah blah random stuff",
    ]
    print("AURA NLP Engine Test\n" + "="*40)
    for q in test_queries:
        result = get_response(q)
        print(f"\n Q: {q}")
        print(f"   Tag: {result['tag']} | Confidence: {result['confidence']}")
        print(f"   Response: {result['response'][:80]}...")
