"""
app.py — AURA Flask Backend
Main application entry point. Handles routing, API endpoints, and session management.
"""

from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from functools import wraps
from html import escape
import os
import sys
from flask_mail import Mail, Message as MailMessage
import secrets
import time

if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

# ─── Path setup ───────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

# ─── Import project modules ───────────────────────────────────────────────────
from models.database import (
    init_db, create_user, authenticate_user,
    get_user_by_id, save_message, get_chat_history, clear_chat_history,
    get_connection
)
from nlp_engine import get_response
from gpt_module.gpt_chat import mock_gpt_response

# ─── Flask app setup ──────────────────────────────────────────────────────────
app = Flask(__name__)
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if os.environ.get('RENDER'):
        raise RuntimeError('SECRET_KEY environment variable is required in production.')
    SECRET_KEY = 'dev-only-placeholder-key-not-for-production'
# ── Email Configuration ───────────────────────────────────────────────────────
MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or os.environ.get('GMAIL_USERNAME')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or os.environ.get('GMAIL_PASSWORD')
MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or MAIL_USERNAME
MAIL_SENDER_NAME = os.environ.get('MAIL_SENDER_NAME', 'AURA - IZee')

app.config.update(
    SECRET_KEY=SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get(
        'SESSION_COOKIE_SECURE',
        'true' if os.environ.get('RENDER') else 'false',
    ).lower() == 'true',
    MAIL_SERVER=os.environ.get('MAIL_SERVER', 'smtp.gmail.com'),
    MAIL_PORT=int(os.environ.get('MAIL_PORT', '587')),
    MAIL_USE_TLS=os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true',
    MAIL_USE_SSL=os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true',
    MAIL_USERNAME=MAIL_USERNAME,
    MAIL_PASSWORD=MAIL_PASSWORD,
    MAIL_DEFAULT_SENDER=(MAIL_SENDER_NAME, MAIL_DEFAULT_SENDER) if MAIL_DEFAULT_SENDER else None,
)
mail = Mail(app)

init_db()

# Store OTPs temporarily {email: {otp, expiry}}
otp_store = {}


def json_body():
    """Return JSON request data without raising on empty or invalid bodies."""
    return request.get_json(silent=True) or {}


def normalize_role(role):
    return role if role in {'student', 'faculty'} else 'student'


def validate_registration_role(data):
    role = normalize_role((data.get('role') or 'student').strip())
    return role, None


def password_is_valid(password):
    return len(password) >= 8


def mail_is_configured():
    return bool(app.config.get('MAIL_USERNAME') and app.config.get('MAIL_PASSWORD'))

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


@app.after_request
def add_security_headers(response):
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    response.headers.setdefault(
        'Permissions-Policy',
        'camera=(), microphone=(), geolocation=()',
    )
    return response


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
    data = json_body()

    # Validate input
    name     = (data.get('name', '') or '').strip()
    email    = (data.get('email', '') or '').strip()
    password = (data.get('password', '') or '').strip()

    if not name or not email or not password:
        return jsonify({'success': False, 'message': 'All fields are required.'}), 400

    if not password_is_valid(password):
        return jsonify({'success': False, 'message': 'Password must be at least 8 characters.'}), 400

    if '@' not in email:
        return jsonify({'success': False, 'message': 'Invalid email address.'}), 400

    role, role_error = validate_registration_role(data)
    if role_error:
        return jsonify({'success': False, 'message': role_error}), 403

    result = create_user(name, email, password, role)

    if result['success']:
        # Auto login after registration
        session['user_id'] = result['user']['id']
        session['user_name'] = result['user']['name']
        session['user_role'] = role
        redirect_url = '/faculty_dashboard' if role == 'faculty' else '/dashboard'
        return jsonify({'success': True, 'message': result['message'], 'redirect': redirect_url})

    return jsonify({'success': False, 'message': result['message']}), 409


@app.route('/api/login', methods=['POST'])
def api_login():
    """Authenticate user and start session."""
    data = json_body()

    email    = (data.get('email', '') or '').strip()
    password = (data.get('password', '') or '').strip()

    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required.'}), 400

    result = authenticate_user(email, password)

    if result['success']:
        session['user_id']   = result['user']['id']
        session['user_name'] = result['user']['name']

        # Get role directly from database — most reliable
        conn = get_db()
        row  = conn.execute(
            "SELECT role FROM users WHERE id = ?",
            (result['user']['id'],)
        ).fetchone()
        conn.close()

        role = row['role'] if row and row['role'] else 'student'
        session['user_role'] = role

        redirect_url = '/faculty_dashboard' if role == 'faculty' else '/dashboard'
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
    data = json_body()
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
    return get_connection()

def ensure_student_dashboard_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS student_dashboard (
            user_id              INTEGER PRIMARY KEY,
            attendance_percent   INTEGER DEFAULT 86,
            attendance_note      TEXT    DEFAULT 'Above the 75% requirement',
            fee_status           TEXT    DEFAULT 'Due soon',
            fee_balance          TEXT    DEFAULT '₹12,500',
            fee_note             TEXT    DEFAULT 'Balance due by 30 May',
            fee_paid             TEXT    DEFAULT '₹87,500',
            fee_paid_percent     INTEGER DEFAULT 88,
            next_exam_title      TEXT    DEFAULT 'Business Analytics',
            next_exam_date       TEXT    DEFAULT '2026-05-24T09:30',
            exam_result          TEXT    DEFAULT 'Internal 1: 82%',
            gpa                  TEXT    DEFAULT '8.7',
            cgpa                 TEXT    DEFAULT '8.4',
            timetable            TEXT    DEFAULT 'Mon 09:30 - Business Analytics\nTue 11:00 - Python Lab\nWed 10:00 - Finance\nThu 02:00 - Marketing\nFri 09:30 - Mentoring',
            updated_at           TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    conn.commit()

def get_student_dashboard_data(user_id):
    conn = get_db()
    ensure_student_dashboard_table(conn)
    row = conn.execute(
        "SELECT * FROM student_dashboard WHERE user_id = ?",
        (user_id,)
    ).fetchone()

    if not row:
        conn.execute(
            "INSERT INTO student_dashboard (user_id) VALUES (?)",
            (user_id,)
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM student_dashboard WHERE user_id = ?",
            (user_id,)
        ).fetchone()

    conn.close()
    return dict(row)

def require_faculty():
    if session.get('user_role') == 'faculty':
        return True

    conn = get_db()
    row = conn.execute(
        "SELECT role FROM users WHERE id = ?",
        (session.get('user_id'),)
    ).fetchone()
    conn.close()

    role = row['role'] if row and row['role'] else 'student'
    session['user_role'] = role
    return role == 'faculty'

# ── Dashboard ─────────────────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    user = get_user_by_id(session['user_id'])
    dashboard_data = get_student_dashboard_data(session['user_id'])
    return render_template('dashboard.html', user=user, dashboard=dashboard_data)

@app.route('/faculty_dashboard')
@login_required
def faculty_dashboard():
    user = get_user_by_id(session['user_id'])

    # Check role from database directly — more reliable than session
    conn = get_db()
    user_row = conn.execute(
        "SELECT role FROM users WHERE id = ?",
        (session['user_id'],)
    ).fetchone()

    actual_role = user_row['role'] if user_row else 'student'
    session['user_role'] = actual_role  # fix session if wrong

    if actual_role != 'faculty':
        conn.close()
        return redirect(url_for('dashboard'))

    messages = conn.execute("""
        SELECT m.*, u.name as sender_name
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE m.receiver_id = ?
        ORDER BY m.timestamp DESC
    """, (session['user_id'],)).fetchall()

    ensure_student_dashboard_table(conn)
    students = conn.execute("""
        SELECT id, name, email
        FROM users
        WHERE role = 'student'
        ORDER BY name ASC
    """).fetchall()

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
    data       = json_body()
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

@app.route('/api/student_dashboard/<int:student_id>')
@login_required
def api_student_dashboard(student_id):
    if not require_faculty() and student_id != session['user_id']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    return jsonify({'success': True, 'dashboard': get_student_dashboard_data(student_id)})

@app.route('/api/student_dashboard/<int:student_id>', methods=['POST'])
@login_required
def api_update_student_dashboard(student_id):
    if not require_faculty():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    data = json_body()

    def clean_text(key, default=''):
        return str(data.get(key, default) or default).strip()

    def clean_int(key, default=0, min_value=0, max_value=100):
        try:
            value = int(data.get(key, default))
        except (TypeError, ValueError):
            value = default
        return max(min_value, min(max_value, value))

    conn = get_db()
    ensure_student_dashboard_table(conn)

    student = conn.execute(
        "SELECT id FROM users WHERE id = ? AND role = 'student'",
        (student_id,)
    ).fetchone()
    if not student:
        conn.close()
        return jsonify({'success': False, 'message': 'Student not found'}), 404

    conn.execute("""
        INSERT INTO student_dashboard (
            user_id, attendance_percent, attendance_note, fee_status,
            fee_balance, fee_note, fee_paid, fee_paid_percent,
            next_exam_title, next_exam_date, exam_result, gpa, cgpa, timetable,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(user_id) DO UPDATE SET
            attendance_percent = excluded.attendance_percent,
            attendance_note = excluded.attendance_note,
            fee_status = excluded.fee_status,
            fee_balance = excluded.fee_balance,
            fee_note = excluded.fee_note,
            fee_paid = excluded.fee_paid,
            fee_paid_percent = excluded.fee_paid_percent,
            next_exam_title = excluded.next_exam_title,
            next_exam_date = excluded.next_exam_date,
            exam_result = excluded.exam_result,
            gpa = excluded.gpa,
            cgpa = excluded.cgpa,
            timetable = excluded.timetable,
            updated_at = datetime('now')
    """, (
        student_id,
        clean_int('attendance_percent', 86),
        clean_text('attendance_note', 'Above the 75% requirement'),
        clean_text('fee_status', 'Due soon'),
        clean_text('fee_balance', '₹12,500'),
        clean_text('fee_note', 'Balance due by 30 May'),
        clean_text('fee_paid', '₹87,500'),
        clean_int('fee_paid_percent', 88),
        clean_text('next_exam_title', 'Business Analytics'),
        clean_text('next_exam_date', '2026-05-24T09:30'),
        clean_text('exam_result', 'Internal 1: 82%'),
        clean_text('gpa', '8.7'),
        clean_text('cgpa', '8.4'),
        clean_text('timetable', '')
    ))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Student dashboard updated'})

@app.route('/api/send_dm', methods=['POST'])
@login_required
def api_send_dm():
    data        = json_body()
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
    if not require_faculty():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    data        = json_body()
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
@app.route('/dm_chat')
@login_required
def dm_chat():
    """Student chat page to view and reply to faculty messages."""
    user = get_user_by_id(session['user_id'])
    return render_template('dm_chat.html', user=user)

@app.route('/api/my_conversations')
@login_required
def api_my_conversations():
    """Get list of faculty that this student has messaged."""
    conn = get_db()
    faculty = conn.execute("""
        SELECT DISTINCT u.id, u.name, u.email
        FROM messages m
        JOIN users u ON (
            CASE
                WHEN m.sender_id = ? THEN u.id = m.receiver_id
                ELSE u.id = m.sender_id
            END
        )
        WHERE (m.sender_id = ? OR m.receiver_id = ?)
          AND u.role = 'faculty'
    """, (session['user_id'], session['user_id'], session['user_id'])).fetchall()
    conn.close()
    return jsonify({'success': True, 'faculty': [dict(f) for f in faculty]})
# ── OTP Routes ────────────────────────────────────────────────────────────────
@app.route('/api/send_otp', methods=['POST'])
def api_send_otp():
    data  = json_body()
    email = (data.get('email', '') or '').strip().lower()
    name  = (data.get('name',  '') or '').strip()
    password = (data.get('password', '') or '').strip()

    if not name or not email or not password:
        return jsonify({'success': False, 'message': 'All fields are required.'}), 400

    if not password_is_valid(password):
        return jsonify({'success': False, 'message': 'Password must be at least 8 characters.'}), 400

    role, role_error = validate_registration_role(data)
    if role_error:
        return jsonify({'success': False, 'message': role_error}), 403

    if not mail_is_configured():
        result = create_user(name, email, password, role)

        if result['success']:
            session['user_id']   = result['user']['id']
            session['user_name'] = result['user']['name']
            session['user_role'] = role
            redirect_url = '/faculty_dashboard' if role == 'faculty' else '/dashboard'
            return jsonify({
                'success': True,
                'message': 'Account created!',
                'redirect': redirect_url,
                'otp_required': False
            })

        status = 409 if 'already' in result['message'].lower() else 400
        return jsonify({'success': False, 'message': result['message']}), status

    # Check if email already registered
    conn     = get_db()
    existing = conn.execute(
        "SELECT id FROM users WHERE email = ?", (email,)
    ).fetchone()
    conn.close()

    if existing:
        return jsonify({'success': False, 'message': 'Email already registered.'}), 409

    # Generate 6-digit OTP
    otp    = f"{secrets.randbelow(900000) + 100000}"
    expiry = time.time() + 300  # expires in 5 minutes
    otp_store[email] = {'otp': otp, 'expiry': expiry}

    # Send email
    try:
        safe_name = escape(name or 'Student')
        msg      = MailMessage(
            subject    = 'AURA – Your Verification Code',
            recipients = [email]
        )
        msg.html = f"""
        <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;background:#09090e;color:#f0f0f8;border-radius:16px;overflow:hidden;">
          <div style="background:linear-gradient(135deg,#6c63ff,#00d4ff);padding:24px;text-align:center;">
            <h1 style="margin:0;font-size:28px;color:white;">AURA</h1>
            <p style="margin:4px 0 0;color:rgba(255,255,255,0.85);font-size:13px;">IZee Business School</p>
          </div>
          <div style="padding:32px 24px;">
            <p style="font-size:16px;margin-bottom:8px;">Hi <strong>{safe_name}</strong>,</p>
            <p style="color:#8888aa;font-size:14px;margin-bottom:24px;">Use the code below to verify your email and complete registration.</p>
            <div style="background:#1c1c2a;border:1px solid #2a2a3d;border-radius:12px;padding:24px;text-align:center;margin-bottom:24px;">
              <p style="margin:0 0 8px;font-size:13px;color:#8888aa;">Your verification code</p>
              <h2 style="margin:0;font-size:42px;letter-spacing:12px;color:#6c63ff;font-family:monospace;">{otp}</h2>
              <p style="margin:8px 0 0;font-size:12px;color:#555570;">Expires in 5 minutes</p>
            </div>
            <p style="font-size:12px;color:#555570;">If you didn't request this, please ignore this email.</p>
          </div>
        </div>
        """
        mail.send(msg)
        return jsonify({'success': True, 'message': 'OTP sent to your email!'})

    except Exception as e:
        print(f"Email error: {e}")
        return jsonify({'success': False, 'message': 'Failed to send email. Check your email address.'}), 500


@app.route('/api/verify_otp', methods=['POST'])
def api_verify_otp():
    data     = json_body()
    email    = (data.get('email',    '') or '').strip().lower()
    otp      = (data.get('otp',      '') or '').strip()
    name     = (data.get('name',     '') or '').strip()
    password = (data.get('password', '') or '').strip()
    role, role_error = validate_registration_role(data)

    if not name or not email or not password:
        return jsonify({'success': False, 'message': 'All fields are required.'}), 400

    if not password_is_valid(password):
        return jsonify({'success': False, 'message': 'Password must be at least 8 characters.'}), 400

    if role_error:
        return jsonify({'success': False, 'message': role_error}), 403

    if email not in otp_store:
        return jsonify({'success': False, 'message': 'OTP expired. Please request a new one.'}), 400

    stored = otp_store[email]

    if time.time() > stored['expiry']:
        del otp_store[email]
        return jsonify({'success': False, 'message': 'OTP expired. Please request a new one.'}), 400

    if not secrets.compare_digest(otp, stored['otp']):
        return jsonify({'success': False, 'message': 'Incorrect OTP. Please try again.'}), 400

    del otp_store[email]
    result = create_user(name, email, password, role)

    if result['success']:
        session['user_id']   = result['user']['id']
        session['user_name'] = result['user']['name']
        session['user_role'] = role
        redirect_url = '/faculty_dashboard' if role == 'faculty' else '/dashboard'
        return jsonify({'success': True, 'message': 'Account created!', 'redirect': redirect_url})

    return jsonify({'success': False, 'message': result['message']}), 400
if __name__ == '__main__':

    print("=" * 50)
    print("  AURA - College Assistant Chatbot")
    print("  Initializing database...")
    init_db()
    port = int(os.environ.get('PORT', '5000'))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    print(f"  Starting Flask server on http://127.0.0.1:{port}")
    print("=" * 50)
    app.run(debug=debug, host='0.0.0.0', port=port)
