<<<<<<< HEAD
/* ═══════════════════════════════════════════════════════
   EmoStudyAI — login.js
═══════════════════════════════════════════════════════ */

function switchTab(tab) {
  const loginForm    = document.getElementById('login-form');
  const registerForm = document.getElementById('register-form');
  const indicator    = document.getElementById('tab-indicator');
  const tabs         = document.querySelectorAll('.tab');

  if (tab === 'login') {
    loginForm.classList.remove('hidden');
    registerForm.classList.add('hidden');
    indicator.classList.remove('right');
    tabs[0].classList.add('active');
    tabs[1].classList.remove('active');
  } else {
    loginForm.classList.add('hidden');
    registerForm.classList.remove('hidden');
    indicator.classList.add('right');
    tabs[1].classList.add('active');
    tabs[0].classList.remove('active');
  }
}

function togglePwd(id, btn) {
  const input = document.getElementById(id);
  if (input.type === 'password') {
    input.type       = 'text';
    btn.textContent  = '🙈';
  } else {
    input.type       = 'password';
    btn.textContent  = '👁';
  }
}

/* ── LOGIN ──────────────────────────────────────────── */
async function handleLogin(e) {
  e.preventDefault();

  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value;
  const errorEl  = document.getElementById('login-error');
  const btn      = document.getElementById('login-btn');

  errorEl.textContent = '';
  btn.classList.add('loading');
  btn.querySelector('span').textContent = 'Signing in…';

  try {
    const res  = await fetch('/login', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ username, password })
    });

    // Flask returns 200 on success, 401 on failure
    if (res.ok) {
      const data = await res.json();
      // Flask sends { "status": "ok" }
      if (data.status === 'ok') {
        window.location.href = '/dashboard';
        return;
      }
      errorEl.textContent = data.message || 'Login failed.';
    } else {
      const data = await res.json().catch(() => ({}));
      errorEl.textContent = data.message || 'Invalid username or password.';
    }

  } catch (err) {
    errorEl.textContent = 'Cannot reach server. Is Flask running?';
  }

  btn.classList.remove('loading');
  btn.querySelector('span').textContent = 'Sign In';
}

/* ── REGISTER ───────────────────────────────────────── */
async function handleRegister(e) {
  e.preventDefault();

  // Flask expects "fullname" — was sending "name" before (bug fixed)
  const fullname = document.getElementById('reg-name').value.trim();
  const username = document.getElementById('reg-username').value.trim();
  const password = document.getElementById('reg-password').value;
  const errorEl  = document.getElementById('register-error');
  const btn      = e.target.querySelector('button[type="submit"]');

  errorEl.textContent = '';
  if (btn) {
    btn.classList.add('loading');
    btn.querySelector('span').textContent = 'Creating…';
  }

  try {
    const res  = await fetch('/register', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ fullname, username, password })  // ← fixed: fullname not name
    });

    const data = await res.json();

    // Flask sends { "status": "ok" } on success
    if (data.status === 'ok') {
      // Auto-login after register
      const loginRes = await fetch('/login', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ username, password })
      });
      if (loginRes.ok) {
        window.location.href = '/dashboard';
        return;
      }
      // If auto-login fails, switch to login tab
      switchTab('login');
      document.getElementById('login-error').textContent = 'Account created! Please sign in.';
      return;
    }

    errorEl.textContent = data.message || 'Registration failed.';

  } catch (err) {
    errorEl.textContent = 'Cannot reach server. Is Flask running?';
  }

  if (btn) {
    btn.classList.remove('loading');
    btn.querySelector('span').textContent = 'Create Account';
  }
}

/* ── GUEST ──────────────────────────────────────────── */
function guestLogin() {
  window.location.href = '/guest';
=======
function switchTab(tab) {
  const loginForm = document.getElementById('login-form');
  const registerForm = document.getElementById('register-form');
  const indicator = document.getElementById('tab-indicator');
  const tabs = document.querySelectorAll('.tab');

  if (tab === 'login') {
    loginForm.classList.remove('hidden');
    registerForm.classList.add('hidden');
    indicator.classList.remove('right');
    tabs[0].classList.add('active');
    tabs[1].classList.remove('active');
  } else {
    loginForm.classList.add('hidden');
    registerForm.classList.remove('hidden');
    indicator.classList.add('right');
    tabs[1].classList.add('active');
    tabs[0].classList.remove('active');
  }
}

function togglePwd(id, btn) {
  const input = document.getElementById(id);
  if (input.type === 'password') {
    input.type = 'text';
    btn.textContent = '🙈';
  } else {
    input.type = 'password';
    btn.textContent = '👁';
  }
}

function handleLogin(e) {
  e.preventDefault();
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value;
  const errorEl = document.getElementById('login-error');
  const btn = document.getElementById('login-btn');

  errorEl.textContent = '';

  if (!username || !password) {
    errorEl.textContent = 'Please fill in all fields.';
    return;
  }

  btn.classList.add('loading');
  btn.querySelector('span').textContent = 'Signing in...';

  // Check stored users
  const users = JSON.parse(localStorage.getItem('emo_users') || '{}');

  setTimeout(() => {
    if (users[username] && users[username].password === password) {
      localStorage.setItem('emo_current_user', JSON.stringify({
        username,
        name: users[username].name
      }));
      window.location.href = '/dashboard';
    } else if (username === 'admin' && password === 'admin') {
      // Default admin account
      localStorage.setItem('emo_current_user', JSON.stringify({
        username: 'admin',
        name: 'Admin User'
      }));
      window.location.href = '/dashboard';
    } else {
      errorEl.textContent = 'Invalid username or password.';
      btn.classList.remove('loading');
      btn.querySelector('span').textContent = 'Sign In';
    }
  }, 800);
}

function handleRegister(e) {
  e.preventDefault();
  const name = document.getElementById('reg-name').value.trim();
  const username = document.getElementById('reg-username').value.trim();
  const password = document.getElementById('reg-password').value;
  const errorEl = document.getElementById('register-error');

  errorEl.textContent = '';

  if (!name || !username || !password) {
    errorEl.textContent = 'Please fill in all fields.';
    return;
  }
  if (password.length < 4) {
    errorEl.textContent = 'Password must be at least 4 characters.';
    return;
  }

  const users = JSON.parse(localStorage.getItem('emo_users') || '{}');
  if (users[username]) {
    errorEl.textContent = 'Username already taken.';
    return;
  }

  users[username] = { name, password };
  localStorage.setItem('emo_users', JSON.stringify(users));
  localStorage.setItem('emo_current_user', JSON.stringify({ username, name }));

  window.location.href = '/dashboard';
}

function guestLogin() {
  localStorage.setItem('emo_current_user', JSON.stringify({
    username: 'guest',
    name: 'Guest User'
  }));
  window.location.href = '/dashboard';
}

// Redirect if already logged in
if (localStorage.getItem('emo_current_user')) {
  window.location.href = '/dashboard';
>>>>>>> 50806243a990f5276a5517268c84289a1eccefbd
}