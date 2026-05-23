import api from './api.js';

function getToken() {
  return localStorage.getItem('episodic_token');
}

function setToken(token) {
  localStorage.setItem('episodic_token', token);
}

function getUser() {
  try {
    return JSON.parse(localStorage.getItem('episodic_user') || 'null');
  } catch (_) {
    return null;
  }
}

function setUser(user) {
  localStorage.setItem('episodic_user', JSON.stringify(user));
}

function isLoggedIn() {
  return !!getToken();
}

function logout() {
  api.auth.logout();
  window.location.href = './login.html';
}

/**
 * requireAuth(roles=[])
 * Redirects to login if not authenticated.
 * Optionally checks role: 'contributor', 'editor', 'admin'.
 * Returns the current user object if authenticated and authorized.
 */
function requireAuth(roles = []) {
  if (!isLoggedIn()) {
    const returnTo = encodeURIComponent(window.location.href);
    window.location.href = `./login.html?returnTo=${returnTo}`;
    return null;
  }

  const user = getUser();

  if (roles.length > 0 && user) {
    const userRole = user.role || '';
    if (!roles.includes(userRole)) {
      window.location.href = './index.html';
      return null;
    }
  }

  return user;
}

/**
 * updateNavForAuth()
 * Updates the nav CTA button to show "Dashboard" if logged in, "Sign In" if not.
 * Expects an element with id="nav-cta" in the page.
 */
function updateNavForAuth() {
  const btn = document.getElementById('nav-cta');
  if (!btn) return;

  if (isLoggedIn()) {
    const user = getUser();
    btn.textContent = 'Dashboard';
    btn.href = './dashboard.html';
    btn.setAttribute('href', './dashboard.html');
    // Convert button to anchor if needed
    if (btn.tagName === 'BUTTON') {
      btn.onclick = () => { window.location.href = './dashboard.html'; };
    }
  } else {
    btn.textContent = 'Sign In';
    btn.setAttribute('href', './login.html');
    if (btn.tagName === 'BUTTON') {
      btn.onclick = () => { window.location.href = './login.html'; };
    }
  }
}

export {
  getToken,
  setToken,
  getUser,
  setUser,
  isLoggedIn,
  logout,
  requireAuth,
  updateNavForAuth,
};
