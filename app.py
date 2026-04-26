"""
app.py — AURA Flask Backend
Main application entry point. Handles routing, API endpoints, and session management.
"""

from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from functools import wraps
import os
import sys

# ─── Path setup ───────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

# ─── Import project modules ───────────────────────────────────────────────────
from models.database import (
    init_db, create_user, authenticate_user,
    get_user_by_id, save_message, get_chat_history, clear_chat_history
)
from nlp_engine import get_response

# ─── Flask app setup ──────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'aura-secret-key-change-in-production')

# ─── Auth decorator ───────────────────────────────────────────────────────────
def login_required(f):
    """Decorator to protect routes that require authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Authentication required', 'redirect': '/login'}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated


# ──────────────────────────────────────────────────────────────────────────────
#  PAGE ROUTES
# ──────────────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Root — redirect based on auth status."""
    if 'user_id' in session:
        return redirect(url_for('chat_page'))
    return redirect(url_for('login_page'))


@app.route('/login')
def login_page():
    """Serve the login/register page."""
    if 'user_id' in session:
        return redirect(url_for('chat_page'))
    return render_template('login.html')


@app.route('/chat')
@login_required
def chat_page():
    """Serve the main chat interface."""
    user = get_user_by_id(session['user_id'])
    return render_template('chat.html', user=user)


# ──────────────────────────────────────────────────────────────────────────────
#  AUTH API ROUTES
# ──────────────────────────────────────────────────────────────────────────────

@app.route('/api/register', methods=['POST'])
def api_register():
    """Register a new user account."""
    data = request.get_json()

    # Validate input
    name     = (data.get('name', '') or '').strip()
    email    = (data.get('email', '') or '').strip()
    password = (data.get('password', '') or '').strip()

    if not name or not email or not password:
        return jsonify({'success': False, 'message': 'All fields are required.'}), 400

    if len(password) < 6:
        return jsonify({'success': False, 'message': 'Password must be at least 6 characters.'}), 400

    if '@' not in email:
        return jsonify({'success': False, 'message': 'Invalid email address.'}), 400

    result = create_user(name, email, password)

    if result['success']:
        # Auto login after registration
        session['user_id'] = result['user']['id']
        session['user_name'] = result['user']['name']
        return jsonify({'success': True, 'message': result['message'], 'redirect': '/chat'})

    return jsonify({'success': False, 'message': result['message']}), 409


@app.route('/api/login', methods=['POST'])
def api_login():
    """Authenticate user and start session."""
    data = request.get_json()

    email    = (data.get('email', '') or '').strip()
    password = (data.get('password', '') or '').strip()

    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required.'}), 400

    result = authenticate_user(email, password)

    if result['success']:
        session['user_id'] = result['user']['id']
        session['user_name'] = result['user']['name']
        return jsonify({'success': True, 'message': 'Login successful!', 'redirect': '/chat'})

    return jsonify({'success': False, 'message': result['message']}), 401


@app.route('/api/logout', methods=['POST'])
def api_logout():
    """Clear session and log out user."""
    session.clear()
    return jsonify({'success': True, 'redirect': '/login'})


# ──────────────────────────────────────────────────────────────────────────────
#  CHAT API ROUTES
# ──────────────────────────────────────────────────────────────────────────────

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    """Process a user message and return the bot response."""
    data = request.get_json()
    user_input = (data.get('message', '') or '').strip()

    if not user_input:
        return jsonify({'success': False, 'message': 'Empty message.'}), 400

    user_id = session['user_id']

    # ── Save user message ────────────────────────────────────────────────────
    save_message(user_id, 'user', user_input)

    # ── Process with NLP engine ──────────────────────────────────────────────
    result = get_response(user_input)

    # ── Save bot response ────────────────────────────────────────────────────
    save_message(
        user_id, 'bot', result['response'],
        intent=result['tag'],
        confidence=result['confidence']
    )

    return jsonify({
        'success': True,
        'response': result['response'],
        'intent': result['tag'],
        'confidence': result['confidence']
    })


@app.route('/api/history', methods=['GET'])
@login_required
def api_history():
    """Retrieve chat history for the logged-in user."""
    user_id = session['user_id']
    history = get_chat_history(user_id, limit=100)
    return jsonify({'success': True, 'history': history})


@app.route('/api/clear-history', methods=['POST'])
@login_required
def api_clear_history():
    """Clear chat history for the logged-in user."""
    user_id = session['user_id']
    clear_chat_history(user_id)
    return jsonify({'success': True, 'message': 'Chat history cleared.'})


# ──────────────────────────────────────────────────────────────────────────────
#  ERROR HANDLERS
# ──────────────────────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    if request.is_json:
        return jsonify({'error': 'Endpoint not found.'}), 404
    return redirect(url_for('login_page'))


@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error. Please try again.'}), 500


# ──────────────────────────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 50)
    print("  🤖 AURA — College Assistant Chatbot")
    print("  Initializing database...")
    init_db()
    print("  Starting Flask server on http://127.0.0.1:5000")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)
