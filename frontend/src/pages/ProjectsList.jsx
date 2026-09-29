import { useEffect, useState } from 'react'
import { api } from '../api/client.js'

export default function ProjectsList({ ctx, onOpenProject, onLogout }) {
  const [projects, setProjects] = useState([])
  const [clients, setClients] = useState([])
  const [error, setError] = useState('')
  const [newName, setNewName] = useState('')
  const [newClientId, setNewClientId] = useState('')

  async function load() {
    try {
      setProjects(await api.listProjects())
      if (ctx.role !== 'client_user') setClients(await api.listClients())
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => { load() }, [])

  async function createProject(e) {
    e.preventDefault()
    try {
      await api.createProject({ name: newName, client_id: newClientId })
      setNewName('')
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="app-shell">
      <div className="topbar">
        <div>
          <h1>Projects</h1>
          <span className="pill">Viewing as {ctx.role}{ctx.agency_name ? ` @ ${ctx.agency_name}` : ''}</span>
        </div>
        <button className="secondary" onClick={onLogout}>Log out</button>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="card">
        {projects.length === 0 && <p>No projects yet.</p>}
        {projects.map((p) => (
          <div key={p.id} className="task-card" onClick={() => onOpenProject(p)}>
            <strong>{p.name}</strong> <span className="pill">{p.status}</span>
          </div>
        ))}
      </div>

      {ctx.role === 'agency_admin' && (
        <div className="card">
          <h3>New project</h3>
          <form onSubmit={createProject}>
            <input placeholder="Project name" value={newName} onChange={(e) => setNewName(e.target.value)} />
            <select value={newClientId} onChange={(e) => setNewClientId(e.target.value)}>
              <option value="">Select client…</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
            <button type="submit" disabled={!newName || !newClientId}>Create</button>
          </form>
        </div>
      )}
    </div>
  )
}
