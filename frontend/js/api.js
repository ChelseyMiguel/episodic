const API_BASE = import.meta?.env?.VITE_API_URL
  || (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
      ? 'http://localhost:8000/api/v1'
      : 'https://episodic.up.railway.app/api/v1');

async function apiFetch(path, options = {}) {
  const token = localStorage.getItem('episodic_token');
  const headers = { ...(options.headers || {}) };

  let body = undefined;

  if (options.body instanceof FormData) {
    body = options.body;
    // Don't set Content-Type — browser sets it with boundary
  } else if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(options.body);
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method || 'GET',
    headers,
    body,
  });

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}`;
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorData.message || errorMessage;
    } catch (_) {
      // ignore parse errors
    }
    const err = new Error(errorMessage);
    err.status = response.status;
    throw err;
  }

  // Handle 204 No Content
  if (response.status === 204) return null;

  return response.json();
}

const api = {
  auth: {
    login(email, password) {
      return apiFetch('/auth/login', { method: 'POST', body: { email, password } });
    },
    signup(email, password, displayName) {
      return apiFetch('/auth/signup', { method: 'POST', body: { email, password, display_name: displayName } });
    },
    me() {
      return apiFetch('/auth/me');
    },
    logout() {
      localStorage.removeItem('episodic_token');
      localStorage.removeItem('episodic_user');
    },
  },

  articles: {
    list(params = {}) {
      const qs = new URLSearchParams();
      if (params.category) qs.set('category', params.category);
      if (params.tag) qs.set('tag', params.tag);
      if (params.issue_id) qs.set('issue_id', params.issue_id);
      if (params.featured !== undefined) qs.set('featured', params.featured);
      const query = qs.toString();
      return apiFetch(`/articles${query ? '?' + query : ''}`);
    },
    get(slug) {
      return apiFetch(`/articles/${slug}`);
    },
    featured() {
      return apiFetch('/articles/featured');
    },
  },

  issues: {
    list() {
      return apiFetch('/issues');
    },
    get(slug) {
      return apiFetch(`/issues/${slug}`);
    },
  },

  resources: {
    list(params = {}) {
      const qs = new URLSearchParams();
      if (params.category) qs.set('category', params.category);
      if (params.region) qs.set('region', params.region);
      const query = qs.toString();
      return apiFetch(`/resources${query ? '?' + query : ''}`);
    },
  },

  submissions: {
    create(data) {
      return apiFetch('/submissions', { method: 'POST', body: data });
    },
    mine() {
      return apiFetch('/submissions/mine');
    },
    submit(id) {
      return apiFetch(`/submissions/${id}/submit`, { method: 'POST' });
    },
    uploadFile(id, file) {
      const formData = new FormData();
      formData.append('file', file);
      return apiFetch(`/submissions/${id}/upload`, {
        method: 'POST',
        body: formData,
      });
    },
  },

  contributors: {
    apply(data) {
      return apiFetch('/contributors/apply', { method: 'POST', body: data });
    },
    me() {
      return apiFetch('/contributors/me');
    },
  },

  newsletter: {
    subscribe(email) {
      return apiFetch('/newsletter/subscribe', { method: 'POST', body: { email } });
    },
  },
};

export default api;
export { apiFetch };
