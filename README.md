# 🤖 AURA — Artificial University Response Assistant

> A smart AI-based college chatbot built with Flask, NLTK, and a modern chat UI.
> Final Year BCA Project — 2024-25

---

## 📸 Features

| Feature | Details |
|---|---|
| 💬 **Chat Interface** | Modern dark UI resembling ChatGPT/WhatsApp |
| 🔐 **Authentication** | Secure register/login with password hashing |
| 🧠 **NLP Engine** | NLTK tokenization + lemmatization + intent matching |
| 💾 **Database** | SQLite (default) or MySQL (optional) |
| 📜 **Chat History** | Persisted per user, loadable across sessions |
| 📱 **Responsive** | Works on desktop and mobile |
| ⚡ **Quick Questions** | Sidebar shortcuts for common queries |

---

## 📁 Project Structure

```
aura/
├── app.py               ← Flask routes & API endpoints
├── nlp_engine.py        ← NLP processing (tokenize, lemmatize, intent match)
├── intents.json         ← Knowledge base (FAQ patterns + responses)
├── requirements.txt     ← Python dependencies
├── database.sql         ← MySQL schema (optional)
├── aura.db              ← SQLite database (auto-created on first run)
│
├── models/
│   ├── __init__.py
│   └── database.py      ← DB operations (users, chat history)
│
├── templates/
│   ├── login.html       ← Login & Register page
│   └── chat.html        ← Main chat interface
│
└── static/
    ├── css/
    │   ├── auth.css     ← Login page styles
    │   └── chat.css     ← Chat interface styles
    └── js/
        ├── auth.js      ← Login/register form logic
        └── chat.js      ← Chat UI, API calls, message rendering
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- VS Code (recommended editor)
- Git (optional)

---

### Step 1 — Clone / Download the project

```bash
# If using git:
git clone <your-repo-url>
cd aura

# Or just open the aura/ folder in VS Code
```

---

### Step 2 — Create a virtual environment (recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

---

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

This installs:
- **Flask** — web framework
- **NLTK** — natural language processing

---

### Step 4 — Run the application

```bash
python app.py
```

You should see:
```
==================================================
  🤖 AURA — College Assistant Chatbot
  Initializing database...
[DB] Database initialized successfully.
  Starting Flask server on http://127.0.0.1:5000
==================================================
 * Running on http://0.0.0.0:5000
```

---

### Step 5 — Open in browser

Visit: **http://127.0.0.1:5000**

1. **Register** a new account
2. Start chatting with AURA!

---

## 💬 Test Queries

Try typing these into the chatbot:

| Query | Expected Intent |
|---|---|
| `When are the exams?` | exam_schedule |
| `What is the fee structure?` | fee_structure |
| `How to apply for admission?` | admission |
| `Tell me about courses` | courses |
| `What is the library timing?` | library |
| `Tell me about BCA` | bca |
| `Is hostel available?` | hostel |
| `What is the placement record?` | placement |
| `Are there any scholarships?` | scholarship |
| `What is the attendance policy?` | attendance |
| `Contact information` | contact |

---

## 🧠 How the NLP Works

```
User Input
    │
    ▼
Preprocessing
  • Lowercase
  • Remove punctuation
  • Tokenize (word_tokenize)
  • Remove stopwords
  • Lemmatize (WordNetLemmatizer)
    │
    ▼
Intent Matching
  • Compare preprocessed tokens against all patterns in intents.json
  • Jaccard similarity + coverage score
  • Pick best match above threshold (0.25)
    │
    ▼
Response Selection
  • Pick random response from matched intent
  • Fallback: "unknown" intent if confidence < threshold
    │
    ▼
Return Response + Intent Tag + Confidence Score
```

---

## 🗄️ Database Schema

### `users`
| Column | Type | Description |
|---|---|---|
| id | INTEGER | Primary key |
| name | TEXT | Full name |
| email | TEXT | Unique email |
| password | TEXT | SHA-256 hash |
| salt | TEXT | Random salt |
| created_at | TEXT | Timestamp |

### `chat_history`
| Column | Type | Description |
|---|---|---|
| id | INTEGER | Primary key |
| user_id | INTEGER | FK → users |
| role | TEXT | 'user' or 'bot' |
| message | TEXT | Message content |
| intent | TEXT | Detected intent |
| confidence | REAL | Match score |
| timestamp | TEXT | Timestamp |

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/register` | Register new user |
| POST | `/api/login` | Login & start session |
| POST | `/api/logout` | End session |
| POST | `/api/chat` | Send message, get response |
| GET | `/api/history` | Get chat history |
| POST | `/api/clear-history` | Clear chat history |

---

## ⚙️ Optional: MySQL Setup

By default, AURA uses **SQLite** (no setup required). To switch to MySQL:

1. Install MySQL connector: `pip install flask-mysqlclient` or `pip install PyMySQL`
2. Create database using `database.sql`
3. Update `models/database.py` — replace `sqlite3` with a MySQL connection

---

## 🛠️ VS Code Tips

- Install **Python extension** by Microsoft
- Install **Pylance** for type hints
- Use the **integrated terminal** to run commands
- Set interpreter to your virtual environment: `Ctrl+Shift+P` → "Python: Select Interpreter"

---

## 📚 Technologies Used

- **Flask** — Python web framework
- **NLTK** — Natural Language Processing
- **SQLite** — Lightweight database
- **HTML5 / CSS3** — Frontend
- **Vanilla JavaScript** — Chat interactions
- **Google Fonts (Syne + DM Sans)** — Typography

---

## 👨‍💻 Author

**[Your Name]**
BCA Final Year — [College Name]
Roll No: [Your Roll Number]
Year: 2024-25

---

## 📄 License

This project is for educational purposes. Feel free to use, modify, and share.
