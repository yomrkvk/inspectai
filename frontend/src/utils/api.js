import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

// Inject auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Handle 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api

// ── Auth ─────────────────────────────────────────────────────────
export const authAPI = {
  login: (username, password) => {
    const fd = new FormData()
    fd.append('username', username)
    fd.append('password', password)
    return api.post('/auth/login', fd)
  },
  register: (data) => api.post('/auth/register', data),
  me: () => api.get('/auth/me'),
}

// ── Inspections ───────────────────────────────────────────────────
export const inspectionsAPI = {
  exifPreview: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/inspections/exif-preview', fd)
  },
  upload: (file, params) => {
    const fd = new FormData()
    fd.append('file', file)
    Object.entries(params || {}).forEach(([k, v]) => {
      if (v !== null && v !== undefined) fd.append(k, v)
    })
    return api.post('/inspections/upload', fd)
  },
  list: (params) => api.get('/inspections/', { params }),
  get: (id) => api.get(`/inspections/${id}`),
  status: (id) => api.get(`/inspections/${id}/status`),
}

// ── Stats ─────────────────────────────────────────────────────────
export const statsAPI = {
  dashboard: () => api.get('/stats/dashboard'),
}

// ── Reports ───────────────────────────────────────────────────────
export const reportsAPI = {
  pdfUrl: (id) => `/api/reports/${id}/pdf`,
  jsonUrl: (id) => `/api/reports/${id}/json`,
}

// ── Comments ──────────────────────────────────────────────────────
export const commentsAPI = {
  list: (params) => api.get('/comments/', { params }),
  create: (data) => api.post('/comments/', data),
}

// ── Map ───────────────────────────────────────────────────────────
export const mapAPI = {
  config: () => api.get('/map/config'),
  points: () => api.get('/map/points'),
}
