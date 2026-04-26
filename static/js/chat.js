/* ── chat.js — AURA Chat Interface Logic ────────────────────────────────── */

// ─── DOM refs ───────────────────────────────────────────────────────────────
const messagesEl   = document.getElementById('messages');
const inputEl      = document.getElementById('userInput');
const sendBtn      = document.getElementById('sendBtn');
const typingEl     = document.getElementById('typingIndicator');
const wrapEl       = document.getElementById('messagesWrap');
const sidebar      = document.getElementById('sidebar');
const overlay      = document.getElementById('overlay');

// ─── State ──────────────────────────────────────────────────────────────────
let isSending = false;

// ─── Initialization ──────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', async () => {
  await loadHistory();
  inputEl.focus();
});

// ─── Load chat history from server ─────────────────────────────────────────
async function loadHistory() {
  try {
    const res  = await fetch('/api/history');
    const data = await res.json();

    if (data.success && data.history.length > 0) {
      // Clear default, render history
      messagesEl.innerHTML = '';
      data.history.forEach(msg => {
        appendMessage(msg.role, msg.message, msg.timestamp, false);
      });
      scrollBottom();
    } else {
      // Show welcome card for new users
      showWelcome();
    }
  } catch {
    showWelcome();
  }
}

// ─── Welcome card ────────────────────────────────────────────────────────────
function showWelcome() {
  const name = window.AURA_USER?.name?.split(' ')[0] || 'Student';
  const card = document.createElement('div');
  card.className = 'welcome-card';
  card.innerHTML = `
    <div class="wc-icon">
      <svg viewBox="0 0 40 40" fill="none">
        <circle cx="20" cy="20" r="18" stroke="currentColor" stroke-width="2"/>
        <path d="M12 26 L20 14 L28 26" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M14.5 22h11" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <circle cx="20" cy="20" r="2" fill="currentColor"/>
      </svg>
    </div>
    <h3>Hi ${escapeHtml(name)}, I'm AURA! 👋</h3>
    <p>Your AI-powered college assistant. Ask me anything about exams, fees, admissions, courses, placements, and more!</p>
  `;
  messagesEl.appendChild(card);
  scrollBottom();
}

// ─── Append a message bubble ─────────────────────────────────────────────────
function appendMessage(role, text, timestamp, animate = true) {
  const isUser = (role === 'user');
  const row    = document.createElement('div');
  row.className = `msg-row ${isUser ? 'user' : 'bot'}`;
  if (!animate) row.style.animation = 'none';

  // Avatar initial
  const initial = isUser
    ? (window.AURA_USER?.initial || 'U')
    : 'A';

  // Format time
  const timeStr = timestamp
    ? new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  // Format bot message (basic markdown)
  const formattedText = isUser ? escapeHtml(text) : formatBotMessage(text);

  row.innerHTML = `
    <div class="msg-avatar">${escapeHtml(initial)}</div>
    <div>
      <div class="bubble">${formattedText}</div>
      <div class="msg-time">${timeStr}</div>
    </div>
  `;

  messagesEl.appendChild(row);
  scrollBottom();
}

// ─── Format bot messages (simple markdown-like parsing) ──────────────────────
function formatBotMessage(text) {
  return escapeHtml(text)
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')  // **bold**
    .replace(/\n/g, '<br>')                             // newlines
    .replace(/•/g, '&bull;')                            // bullets
    .replace(/(📅|💰|🎓|📚|🏠|🚀|🎖️|✅|📞|📊|📖|🏛️|🤔|😊|🗓️|💻)/g, '$1');
}

// ─── Escape HTML to prevent XSS ─────────────────────────────────────────────
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ─── Scroll to bottom ───────────────────────────────────────────────────────
function scrollBottom() {
  requestAnimationFrame(() => {
    wrapEl.scrollTop = wrapEl.scrollHeight;
  });
}

// ─── Show / hide typing indicator ───────────────────────────────────────────
function showTyping()  { typingEl.classList.remove('hidden'); scrollBottom(); }
function hideTyping()  { typingEl.classList.add('hidden'); }

// ─── Auto-resize textarea ───────────────────────────────────────────────────
function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

// ─── Handle Enter / Shift+Enter ─────────────────────────────────────────────
function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

// ─── Send quick question from sidebar ───────────────────────────────────────
function sendQuick(text) {
  inputEl.value = text;
  autoResize(inputEl);
  sendMessage();
  // Close sidebar on mobile
  if (window.innerWidth <= 768) toggleSidebar();
}

// ─── Main send function ──────────────────────────────────────────────────────
async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text || isSending) return;

  isSending = true;
  sendBtn.disabled = true;
  inputEl.value = '';
  inputEl.style.height = 'auto';

  // Remove welcome card if present
  const wCard = messagesEl.querySelector('.welcome-card');
  if (wCard) wCard.remove();

  // Show user message immediately
  appendMessage('user', text);

  // Show typing indicator
  showTyping();

  try {
    const res  = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text })
    });
    const data = await res.json();

    // Simulate slight delay for natural feel (400–700ms)
    await delay(400 + Math.random() * 300);
    hideTyping();

    if (data.success) {
      appendMessage('bot', data.response);
    } else {
      appendMessage('bot', "I'm having trouble processing that right now. Please try again.");
    }
  } catch {
    await delay(400);
    hideTyping();
    appendMessage('bot', "⚠️ Connection error. Please check your internet and try again.");
  }

  isSending = false;
  sendBtn.disabled = false;
  inputEl.focus();
}

// ─── Clear history ───────────────────────────────────────────────────────────
async function clearHistory() {
  if (!confirm('Clear all chat history? This cannot be undone.')) return;

  try {
    await fetch('/api/clear-history', { method: 'POST' });
    messagesEl.innerHTML = '';
    showWelcome();
  } catch {
    alert('Could not clear history. Try again.');
  }
}

// ─── Logout ──────────────────────────────────────────────────────────────────
async function logout() {
  try {
    const res  = await fetch('/api/logout', { method: 'POST' });
    const data = await res.json();
    window.location.href = data.redirect || '/login';
  } catch {
    window.location.href = '/login';
  }
}

// ─── Sidebar toggle (mobile) ─────────────────────────────────────────────────
function toggleSidebar() {
  sidebar.classList.toggle('open');
  overlay.classList.toggle('visible');
  overlay.classList.toggle('hidden');
}

// ─── Utility: sleep ──────────────────────────────────────────────────────────
function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
