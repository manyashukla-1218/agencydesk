import { useState } from 'react'
import { api } from '../api/client.js'

export default function Login({ onLoggedIn }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [contexts, setContexts] = useState(null)
  const [error, setError] = useState('')

  async function submit(e) {
    e.preventDefault()
    setError('')
    try {
      const res = await api.login(email, password)
      if (res.token) {
        onLoggedIn(res.token)
      } else {
        setContexts(res.contexts)
      }
    } catch (err) {
      setError(err.message)
    }
  }

  async function pick(ctx) {
    setError('')
    try {
      const res = await api.selectContext({
        email,
        password,
        agency_id: ctx.client_id ? null : ctx.agency_id,
        client_id: ctx.client_id || null,
      })
      onLoggedIn(res.token)
    } catch (err) {
      setError(err.message)
    }
  }

  if (contexts) {
    return (
      <div className="app-shell">
        <div className="card" style={{ maxWidth: 420, margin: '60px auto' }}>
          <h2>Which account?</h2>
          <p>This email is linked to more than one workspace.</p>
          {error && <div className="error">{error}</div>}
          {contexts.map((c, i) => (
            <div className="context-option" key={i} onClick={() => pick(c)}>
              <strong>{c.client_name ? c.client_name : c.agency_name}</strong>
              <div style={{ fontSize: 13, color: '#666' }}>
                {c.client_name ? `Client portal · ${c.agency_name}` : `${c.role} @ ${c.agency_name}`}
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="app-shell">
      <div className="card" style={{ maxWidth: 380, margin: '60px auto' }}>
        <h2>AgencyDesk</h2>
        {error && <div className="error">{error}</div>}
        <form onSubmit={submit}>
          <input placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <input placeholder="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <button type="submit">Log in</button>
        </form>
        <p style={{ fontSize: 12, color: '#888', marginTop: 12 }}>
          Try: admin@northwind.test / password123, or demo.person@example.com / password123
          (has two accounts — you'll get a picker).
        </p>
      </div>
    </div>
  )
}
