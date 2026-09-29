import { useState } from 'react'
import Login from './pages/Login.jsx'
import ProjectsList from './pages/ProjectsList.jsx'
import ProjectBoard from './pages/ProjectBoard.jsx'
import { setToken, api } from './api/client.js'
import { decodeJwt } from './api/jwt.js'

export default function App() {
  const [ctx, setCtx] = useState(null) // { role, agency_id, client_id, agency_name }
  const [project, setProject] = useState(null)

  function handleLoggedIn(token) {
    setToken(token)
    const payload = decodeJwt(token)
    setCtx({ role: payload.role, agency_id: payload.agency_id, client_id: payload.client_id })
  }

  function handleLogout() {
    setToken(null)
    setCtx(null)
    setProject(null)
  }

  if (!ctx) return <Login onLoggedIn={handleLoggedIn} />

  if (project) {
    return <ProjectBoard ctx={ctx} project={project} onBack={() => setProject(null)} />
  }

  return <ProjectsList ctx={ctx} onOpenProject={setProject} onLogout={handleLogout} />
}
