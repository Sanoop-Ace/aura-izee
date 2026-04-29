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
from gpt_module.gpt_chat import mock_gpt_response
import sqlite3

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

    role = (data.get('role', 'student') or 'student').strip()
    result = create_user(name, email, password, role)

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
        session['user_role'] = result['user'].get('role', 'student')
        redirect_url = '/faculty_dashboard' if session['user_role'] == 'faculty' else '/dashboard'
        return jsonify({'success': True, 'message': 'Login successful!', 'redirect': redirect_url})

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

# ── Helper ────────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect('aura.db')
    conn.row_factory = sqlite3.Row
    return conn

# ── Dashboard ─────────────────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    user = get_user_by_id(session['user_id'])
    return render_template('dashboard.html', user=user)

@app.route('/faculty_dashboard')
@login_required
def faculty_dashboard():
    user = get_user_by_id(session['user_id'])
    if session.get('user_role') != 'faculty':
        return redirect(url_for('dashboard'))
    conn = get_db()
    messages = conn.execute("""
        SELECT m.*, u.name as sender_name
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE m.receiver_id = ?
        ORDER BY m.timestamp DESC
    """, (session['user_id'],)).fetchall()
    students = conn.execute("""
        SELECT DISTINCT u.id, u.name, u.email
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE m.receiver_id = ?
    """, (session['user_id'],)).fetchall()
    conn.close()
    return render_template('faculty_dashboard.html',
                           user=user,
                           messages=[dict(m) for m in messages],
                           students=[dict(s) for s in students])

# ── GPT Assistant ─────────────────────────────────────────────────────────────
@app.route('/gpt')
@login_required
def gpt_page():
    user = get_user_by_id(session['user_id'])
    return render_template('gpt_chat.html', user=user)

@app.route('/api/gpt_chat', methods=['POST'])
@login_required
def api_gpt_chat():
    data       = request.get_json()
    user_input = (data.get('message', '') or '').strip()
    if not user_input:
        return jsonify({'success': False, 'message': 'Empty message'}), 400
    response = mock_gpt_response(user_input)
    conn = get_db()
    conn.execute("INSERT INTO gpt_history (user_id, role, message) VALUES (?, ?, ?)",
                 (session['user_id'], 'user', user_input))
    conn.execute("INSERT INTO gpt_history (user_id, role, message) VALUES (?, ?, ?)",
                 (session['user_id'], 'bot', response))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'response': response})

@app.route('/api/gpt_history')
@login_required
def api_gpt_history():
    conn    = get_db()
    history = conn.execute(
        "SELECT role, message, timestamp FROM gpt_history WHERE user_id = ? ORDER BY timestamp ASC LIMIT 100",
        (session['user_id'],)
    ).fetchall()
    conn.close()
    return jsonify({'success': True, 'history': [dict(h) for h in history]})

# ── Faculty DM ────────────────────────────────────────────────────────────────
@app.route('/api/faculty_list')
@login_required
def api_faculty_list():
    conn    = get_db()
    faculty = conn.execute("SELECT id, name, email FROM users WHERE role = 'faculty'").fetchall()
    conn.close()
    return jsonify({'success': True, 'faculty': [dict(f) for f in faculty]})

@app.route('/api/send_dm', methods=['POST'])
@login_required
def api_send_dm():
    data        = request.get_json()
    receiver_id = data.get('receiver_id')
    message     = (data.get('message', '') or '').strip()
    if not receiver_id or not message:
        return jsonify({'success': False, 'message': 'Missing fields'}), 400
    conn = get_db()
    conn.execute("INSERT INTO messages (sender_id, receiver_id, message) VALUES (?, ?, ?)",
                 (session['user_id'], receiver_id, message))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Message sent!'})

@app.route('/api/dm_history/<int:faculty_id>')
@login_required
def api_dm_history(faculty_id):
    conn = get_db()
    msgs = conn.execute("""
        SELECT m.*, u.name as sender_name
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE (m.sender_id = ? AND m.receiver_id = ?)
           OR (m.sender_id = ? AND m.receiver_id = ?)
        ORDER BY m.timestamp ASC
    """, (session['user_id'], faculty_id, faculty_id, session['user_id'])).fetchall()
    conn.close()
    return jsonify({'success': True, 'messages': [dict(m) for m in msgs]})

@app.route('/api/faculty_reply', methods=['POST'])
@login_required
def api_faculty_reply():
    if session.get('user_role') != 'faculty':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    data        = request.get_json()
    receiver_id = data.get('receiver_id')
    message     = (data.get('message', '') or '').strip()
    if not receiver_id or not message:
        return jsonify({'success': False, 'message': 'Missing fields'}), 400
    conn = get_db()
    conn.execute("INSERT INTO messages (sender_id, receiver_id, message) VALUES (?, ?, ?)",
                 (session['user_id'], receiver_id, message))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Reply sent!'})
if __name__ == '__main__':
    print("=" * 50)
    print("  🤖 AURA — College Assistant Chatbot")
    print("  Initializing database...")
    init_db()
    print("  Starting Flask server on http://127.0.0.1:5000")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)
