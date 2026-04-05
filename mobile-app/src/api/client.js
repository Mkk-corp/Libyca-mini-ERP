import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 12000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Attach JWT on every request ──────────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ── Auto-refresh on 401 ──────────────────────────────────────
let _refreshing = false;
let _queue = [];

const processQueue = (error, token = null) => {
  _queue.forEach((p) => (error ? p.reject(error) : p.resolve(token)));
  _queue = [];
};

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      if (_refreshing) {
        return new Promise((resolve, reject) => {
          _queue.push({ resolve, reject });
        }).then((token) => {
          original.headers.Authorization = `Bearer ${token}`;
          return api(original);
        });
      }
      original._retry = true;
      _refreshing = true;
      try {
        const refresh = localStorage.getItem('refresh_token');
        if (!refresh) throw new Error('no refresh token');
        const { data } = await axios.post(`${BASE_URL}/api/auth/refresh`, {
          refresh_token: refresh,
        });
        const newToken = data.data.access_token;
        localStorage.setItem('access_token', newToken);
        processQueue(null, newToken);
        original.headers.Authorization = `Bearer ${newToken}`;
        return api(original);
      } catch (err) {
        processQueue(err, null);
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.dispatchEvent(new Event('libyca:logout'));
        return Promise.reject(err);
      } finally {
        _refreshing = false;
      }
    }
    return Promise.reject(error);
  }
);

// ── Typed helpers ────────────────────────────────────────────
export const auth = {
  login: (email, password) =>
    api.post('/api/auth/login', { email, password }).then((r) => r.data.data),
  me: () => api.get('/api/auth/me').then((r) => r.data.data),
  refresh: (refresh_token) =>
    api.post('/api/auth/refresh', { refresh_token }).then((r) => r.data.data),
  logout: () => api.post('/api/auth/logout').catch(() => {}),
};

export const dashboard = {
  // The web dashboard route — returns HTML, so we use the API reports instead
  monthly: () => api.get('/api/reports/monthly').then((r) => r.data.data),
};

export const items = {
  list: (params) => api.get('/api/items', { params }).then((r) => r.data),
  create: (body) => api.post('/api/items', body).then((r) => r.data.data),
  update: (id, body) => api.put(`/api/items/${id}`, body).then((r) => r.data.data),
  delete: (id) => api.delete(`/api/items/${id}`).then((r) => r.data),
};

export const sales = {
  list: (params) => api.get('/api/sales', { params }).then((r) => r.data),
  create: (body) => api.post('/api/sales', body).then((r) => r.data.data),
  delete: (id) => api.delete(`/api/sales/${id}`).then((r) => r.data),
};

export const purchases = {
  list: (params) => api.get('/api/purchases', { params }).then((r) => r.data),
  create: (body) => api.post('/api/purchases', body).then((r) => r.data.data),
  delete: (id) => api.delete(`/api/purchases/${id}`).then((r) => r.data),
};

export const expenses = {
  list: (params) => api.get('/api/expenses', { params }).then((r) => r.data),
  create: (body) => api.post('/api/expenses', body).then((r) => r.data.data),
  delete: (id) => api.delete(`/api/expenses/${id}`).then((r) => r.data),
};

export const inventory = {
  list: (params) => api.get('/api/inventory', { params }).then((r) => r.data),
};

export const suppliers = {
  list: (params) => api.get('/api/suppliers', { params }).then((r) => r.data),
};

export const customers = {
  list: (params) => api.get('/api/customers', { params }).then((r) => r.data),
};

export const employees = {
  list: (params) => api.get('/api/employees', { params }).then((r) => r.data),
};

export default api;
