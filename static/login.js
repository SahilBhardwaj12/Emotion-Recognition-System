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
}