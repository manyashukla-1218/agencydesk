const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

let authToken = null

export function setToken(token) {
  authToken = token
}

export function getToken() {
  return authToken
}

async function request(path, { method = 'GET', body, isForm = false } = {}) {
  const headers = {}
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`
  if (!isForm && body !== undefined) headers['Content-Type'] = 'application/json'

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
  })

  if (!res.ok) {
    let detail = res.statusText
    try {
      const data = await res.json()
      detail = data.detail || JSON.stringify(data)
    } catch (_) {}
    throw new Error(detail)
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  login: (email, password) => request('/auth/login', { method: 'POST', body: { email, password } }),
  selectContext: (payload) => request('/auth/select-context', { method: 'POST', body: payload }),

  listProjects: () => request('/projects'),
  createProject: (payload) => request('/projects', { method: 'POST', body: payload }),
  getProject: (id) => request(`/projects/${id}`),

  listClients: () => request('/clients'),
  createClient: (payload) => request('/clients', { method: 'POST', body: payload }),

  listTasks: (projectId, params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/projects/${projectId}/tasks${qs ? `?${qs}` : ''}`)
  },
  createTask: (projectId, payload) => request(`/projects/${projectId}/tasks`, { method: 'POST', body: payload }),
  updateTask: (taskId, payload) => request(`/tasks/${taskId}`, { method: 'PATCH', body: payload }),

  listComments: (taskId) => request(`/tasks/${taskId}/comments`),
  addComment: (taskId, payload) => request(`/tasks/${taskId}/comments`, { method: 'POST', body: payload }),

  listFiles: (taskId) => request(`/tasks/${taskId}/files`),
  uploadFile: (taskId, formData) => request(`/tasks/${taskId}/files`, { method: 'POST', body: formData, isForm: true }),
  setFileApproval: (fileId, approved) =>
    request(`/files/${fileId}/approve?approved=${approved}`, { method: 'POST' }),

  listTimeEntries: (taskId) => request(`/tasks/${taskId}/time-entries`),
  logTime: (taskId, payload) => request(`/tasks/${taskId}/time-entries`, { method: 'POST', body: payload }),

  getDashboard: (projectId) => request(`/projects/${projectId}/dashboard`),

  createInvite: (payload) => request('/invites', { method: 'POST', body: payload }),
  removeMember: (projectId, userId) => request(`/projects/${projectId}/members/${userId}`, { method: 'DELETE' }),
}
