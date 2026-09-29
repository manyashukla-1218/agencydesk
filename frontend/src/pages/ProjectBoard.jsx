import { useEffect, useState } from 'react'
import { api } from '../api/client.js'

const STATUSES = ['todo', 'in_progress', 'in_review', 'done']

export default function ProjectBoard({ ctx, project, onBack }) {
  const isClient = ctx.role === 'client_user'
  const isStaff = !isClient
  const [tasks, setTasks] = useState([])
  const [dashboard, setDashboard] = useState(null)
  const [error, setError] = useState('')
  const [selectedTask, setSelectedTask] = useState(null)
  const [newTitle, setNewTitle] = useState('')
  const [newVisible, setNewVisible] = useState(false)

  async function load() {
    try {
      setTasks(await api.listTasks(project.id))
      setDashboard(await api.getDashboard(project.id))
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => { load() }, [])

  async function createTask(e) {
    e.preventDefault()
    try {
      await api.createTask(project.id, { title: newTitle, is_client_visible: newVisible })
      setNewTitle('')
      setNewVisible(false)
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  async function moveTask(task, status) {
    try {
      await api.updateTask(task.id, { status })
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="app-shell">
      <div className="topbar">
        <div>
          <button className="secondary" onClick={onBack}>← Projects</button>
          <h1 style={{ display: 'inline', marginLeft: 12 }}>{project.name}</h1>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {dashboard && (
        <div className="card">
          <strong>Status counts: </strong>
          {STATUSES.map((s) => (
            <span key={s} className="pill" style={{ marginRight: 6 }}>{s}: {dashboard.task_counts_by_status[s] || 0}</span>
          ))}
          {dashboard.total_hours_logged !== null && dashboard.total_hours_logged !== undefined && (
            <span className="pill">total hours: {dashboard.total_hours_logged}</span>
          )}
        </div>
      )}

      {isStaff && (
        <div className="card">
          <form onSubmit={createTask} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input placeholder="New task title" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} style={{ marginBottom: 0, flex: 1 }} />
            <label style={{ display: 'flex', alignItems: 'center', gap: 4, whiteSpace: 'nowrap' }}>
              <input type="checkbox" style={{ width: 'auto' }} checked={newVisible} onChange={(e) => setNewVisible(e.target.checked)} />
              client-visible
            </label>
            <button type="submit" disabled={!newTitle}>Add</button>
          </form>
        </div>
      )}

      <div className="board">
        {STATUSES.map((status) => (
          <div className="column" key={status}>
            <h3>{status}</h3>
            {tasks.filter((t) => t.status === status).map((t) => (
              <div className="task-card" key={t.id} onClick={() => setSelectedTask(t)}>
                {t.title}
                <span className={`badge ${t.is_client_visible ? 'visible' : 'internal'}`}>
                  {t.is_client_visible ? 'client-visible' : 'internal'}
                </span>
                {isStaff && (
                  <div style={{ marginTop: 6 }}>
                    <select value={t.status} onChange={(e) => moveTask(t, e.target.value)} onClick={(e) => e.stopPropagation()}>
                      {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                )}
              </div>
            ))}
          </div>
        ))}
      </div>

      {selectedTask && (
        <TaskDetail
          ctx={ctx}
          task={selectedTask}
          onClose={() => setSelectedTask(null)}
        />
      )}
    </div>
  )
}

function TaskDetail({ ctx, task, onClose }) {
  const isClient = ctx.role === 'client_user'
  const [comments, setComments] = useState([])
  const [files, setFiles] = useState([])
  const [timeEntries, setTimeEntries] = useState([])
  const [newComment, setNewComment] = useState('')
  const [commentVisible, setCommentVisible] = useState(false)
  const [error, setError] = useState('')
  const [timeMinutes, setTimeMinutes] = useState('')

  async function load() {
    try {
      setComments(await api.listComments(task.id))
      setFiles(await api.listFiles(task.id))
      if (!isClient) setTimeEntries(await api.listTimeEntries(task.id))
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => { load() }, [])

  async function submitComment(e) {
    e.preventDefault()
    try {
      await api.addComment(task.id, { body: newComment, is_client_visible: isClient ? true : commentVisible })
      setNewComment('')
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  async function submitTime(e) {
    e.preventDefault()
    try {
      await api.logTime(task.id, { duration_minutes: Number(timeMinutes) })
      setTimeMinutes('')
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  async function upload(e) {
    const file = e.target.files[0]
    if (!file) return
    const form = new FormData()
    form.append('upload', file)
    form.append('is_client_visible', 'false')
    try {
      await api.uploadFile(task.id, form)
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  async function approve(fileId, approved) {
    try {
      await api.setFileApproval(fileId, approved)
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="card" style={{ position: 'fixed', top: 40, right: 40, left: 40, bottom: 40, overflowY: 'auto', zIndex: 10 }}>
      <button className="secondary" onClick={onClose} style={{ float: 'right' }}>Close</button>
      <h2>{task.title}</h2>
      {error && <div className="error">{error}</div>}

      <h3>Comments</h3>
      {comments.map((c) => (
        <div className="comment" key={c.id}>
          <span className={`badge ${c.is_client_visible ? 'visible' : 'internal'}`}>
            {c.is_client_visible ? 'client-visible' : 'internal'}
          </span>{' '}
          {c.body}
        </div>
      ))}
      <form onSubmit={submitComment}>
        <textarea placeholder="Add a comment…" value={newComment} onChange={(e) => setNewComment(e.target.value)} />
        {!isClient && (
          <label style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
            <input type="checkbox" style={{ width: 'auto' }} checked={commentVisible} onChange={(e) => setCommentVisible(e.target.checked)} />
            client-visible
          </label>
        )}
        <button type="submit" disabled={!newComment}>Post</button>
      </form>

      <h3>Files</h3>
      {files.map((f) => (
        <div className="file-row" key={f.id}>
          <span>
            {f.filename}{' '}
            <span className={`badge ${f.is_client_visible ? 'visible' : 'internal'}`}>
              {f.is_client_visible ? 'client-visible' : 'internal'}
            </span>{' '}
            <span className="pill">{f.approval_status}</span>
          </span>
          {isClient && f.is_client_visible && f.approval_status === 'pending' && (
            <span>
              <button onClick={() => approve(f.id, true)}>Approve</button>{' '}
              <button className="danger" onClick={() => approve(f.id, false)}>Request changes</button>
            </span>
          )}
        </div>
      ))}
      {!isClient && <input type="file" onChange={upload} />}

      {!isClient && (
        <>
          <h3>Time entries</h3>
          {timeEntries.map((t) => (
            <div key={t.id} className="comment">{t.duration_minutes} min — {t.note || 'no note'}</div>
          ))}
          <form onSubmit={submitTime} style={{ display: 'flex', gap: 8 }}>
            <input placeholder="Minutes" type="number" value={timeMinutes} onChange={(e) => setTimeMinutes(e.target.value)} style={{ marginBottom: 0 }} />
            <button type="submit" disabled={!timeMinutes}>Log time</button>
          </form>
        </>
      )}
    </div>
  )
}
