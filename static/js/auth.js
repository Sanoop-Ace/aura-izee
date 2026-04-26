/* ── auth.js — AURA Login & Register Logic ──────────────────────────────── */

// ─── Tab switching ─────────────────────────────────────────────────────────
function switchTab(tab) {
  const loginForm    = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');
  const tabs         = document.querySelectorAll('.tab');
  const indicator    = document.getElementById('tabIndicator');

  // Toggle forms
  if (tab === 'login') {
    loginForm.classList.remove('hidden');
    registerForm.classList.add('hidden');
    indicator.classList.remove('right');
  } else {
    loginForm.classList.add('hidden');
    registerForm.classList.remove('hidden');
    indicator.classList.add('right');
  }

  // Toggle active tab
  tabs.forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
  hideAlert();
}

// ─── Alert system ──────────────────────────────────────────────────────────
function showAlert(message, type = 'error') {
  const box = document.getElementById('alertBox');
  box.textContent = message;
  box.className   = `alert show ${type}`;
}
function hideAlert() {
  const box = document.getElementById('alertBox');
  box.className = 'alert';
}

// ─── Loading state ──────────────────────────────────────────────────────────
function setLoading(btnId, isLoading) {
  const btn    = document.getElementById(btnId);
  const text   = btn.querySelector('.btn-text');
  const loader = btn.querySelector('.btn-loader');
  btn.disabled = isLoading;
  text.hidden  = isLoading;
  loader.hidden = !isLoading;
}

// ─── Toggle password visibility ─────────────────────────────────────────────
function togglePassword(inputId) {
  const input = document.getElementById(inputId);
  input.type  = (input.type === 'password') ? 'text' : 'password';
}

// ─── Handle login ───────────────────────────────────────────────────────────
async function handleLogin(e) {
  e.preventDefault();
  hideAlert();

  const email    = document.getElementById('loginEmail').value.trim();
  const password = document.getElementById('loginPassword').value.trim();

  if (!email || !password) {
    showAlert('Please fill in all fields.'); return;
  }

  setLoading('loginBtn', true);

  try {
    const res  = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();

    if (data.success) {
      showAlert('Login successful! Redirecting…', 'success');
      setTimeout(() => { window.location.href = data.redirect || '/chat'; }, 700);
    } else {
      showAlert(data.message || 'Login failed. Please try again.');
      setLoading('loginBtn', false);
    }
  } catch (err) {
    showAlert('Network error. Please check your connection.');
    setLoading('loginBtn', false);
  }
}

// ─── Handle register ─────────────────────────────────────────────────────────
async function handleRegister(e) {
  e.preventDefault();
  hideAlert();

  const name     = document.getElementById('regName').value.trim();
  const email    = document.getElementById('regEmail').value.trim();
  const password = document.getElementById('regPassword').value.trim();

  if (!name || !email || !password) {
    showAlert('Please fill in all fields.'); return;
  }
  if (password.length < 6) {
    showAlert('Password must be at least 6 characters.'); return;
  }
  if (!email.includes('@')) {
    showAlert('Please enter a valid email address.'); return;
  }

  setLoading('registerBtn', true);

  try {
    const res  = await fetch('/api/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password })
    });
    const data = await res.json();

    if (data.success) {
      showAlert('Account created! Redirecting…', 'success');
      setTimeout(() => { window.location.href = data.redirect || '/chat'; }, 700);
    } else {
      showAlert(data.message || 'Registration failed. Please try again.');
      setLoading('registerBtn', false);
    }
  } catch (err) {
    showAlert('Network error. Please check your connection.');
    setLoading('registerBtn', false);
  }
}
