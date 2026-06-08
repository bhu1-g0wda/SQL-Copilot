import { useState, useCallback, useRef, useEffect } from 'react'
import { Zap, AlertTriangle } from 'lucide-react'
import {
  queryNaturalLanguage,
  executeRawSQL,
  type ConnectionParams,
  type SchemaInfo,
  type QueryResponse,
} from './api/client'
import { ConnectionForm } from './components/ConnectionForm'
import { SchemaViewer }   from './components/SchemaViewer'
import { QueryInput }     from './components/QueryInput'
import { ResultsTable }   from './components/ResultsTable'

// Patterns that indicate a destructive SQL statement
const DESTRUCTIVE_PATTERN = /^\s*(DELETE|DROP|TRUNCATE|UPDATE)\b/i

/** Extract a human-readable message from any Axios/HTTP error. */
function extractError(err: unknown): string {
  // Axios error with a response
  const axiosErr = err as {
    response?: { data?: { detail?: unknown }; status?: number }
    message?: string
  }
  const detail = axiosErr?.response?.data?.detail
  if (detail) {
    // FastAPI/Pydantic 422: detail is an array of validation errors
    if (Array.isArray(detail)) {
      return detail
        .map((d: { msg?: string; loc?: string[] }) =>
          [d.loc?.slice(-1)[0], d.msg].filter(Boolean).join(': ')
        )
        .join(' | ')
    }
    // Normal string detail
    if (typeof detail === 'string') return detail
  }
  // Network error (no response)
  if (axiosErr?.message) return axiosErr.message
  return 'An unexpected error occurred. Please try again.'
}

const SIDEBAR_MIN  = 200
const SIDEBAR_MAX  = 560
const SIDEBAR_DEFAULT = 300

const QUERY_MIN    = 120
const QUERY_MAX    = 520
const QUERY_DEFAULT = 220   // px – initial query panel height

interface ConfirmModal {
  sql: string
  resolve: (ok: boolean) => void
}

// ── Generic drag-resize hook ─────────────────────────────────────────────────
function useHorizontalResize(initial: number) {
  const [width, setWidth] = useState(initial)
  const dragging = useRef(false)
  const startX   = useRef(0)
  const startW   = useRef(initial)

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    dragging.current = true
    startX.current   = e.clientX
    startW.current   = width
    document.body.style.cursor    = 'col-resize'
    document.body.style.userSelect = 'none'
  }, [width])

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging.current) return
      const delta = e.clientX - startX.current
      const next  = Math.min(SIDEBAR_MAX, Math.max(SIDEBAR_MIN, startW.current + delta))
      setWidth(next)
    }
    const onUp = () => {
      if (!dragging.current) return
      dragging.current = false
      document.body.style.cursor    = ''
      document.body.style.userSelect = ''
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup',   onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup',   onUp)
    }
  }, [])

  return { width, onMouseDown }
}

function useVerticalResize(initial: number) {
  const [height, setHeight] = useState(initial)
  const dragging = useRef(false)
  const startY   = useRef(0)
  const startH   = useRef(initial)

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    dragging.current = true
    startY.current   = e.clientY
    startH.current   = height
    document.body.style.cursor    = 'row-resize'
    document.body.style.userSelect = 'none'
  }, [height])

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging.current) return
      const delta = e.clientY - startY.current
      const next  = Math.min(QUERY_MAX, Math.max(QUERY_MIN, startH.current + delta))
      setHeight(next)
    }
    const onUp = () => {
      if (!dragging.current) return
      dragging.current = false
      document.body.style.cursor    = ''
      document.body.style.userSelect = ''
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup',   onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup',   onUp)
    }
  }, [])

  return { height, onMouseDown }
}

// ── App ──────────────────────────────────────────────────────────────────────
function App() {
  const [connection,   setConnection]   = useState<ConnectionParams | null>(null)
  const [schema,       setSchema]       = useState<SchemaInfo | null>(null)
  const [queryMode,    setQueryMode]    = useState<'nl' | 'sql'>('nl')
  const [result,       setResult]       = useState<QueryResponse | null>(null)
  const [isNLResult,   setIsNLResult]   = useState(true)
  const [loading,      setLoading]      = useState(false)
  const [error,        setError]        = useState<string | null>(null)
  const [confirm,      setConfirm]      = useState<ConfirmModal | null>(null)
  const [pendingSQL,   setPendingSQL]   = useState<string>('')

  // Undo stack — each entry is the SQL needed to reverse a prior DML operation
  const [undoStack, setUndoStack] = useState<{ sql: string; label: string }[]>([])

  // Resizable panels
  const sidebar = useHorizontalResize(SIDEBAR_DEFAULT)
  const query   = useVerticalResize(QUERY_DEFAULT)

  const handleConnect = useCallback((params: ConnectionParams, dbSchema: SchemaInfo) => {
    setConnection(params)
    setSchema(dbSchema)
    setResult(null)
    setError(null)
  }, [])

  const askConfirmation = (sql: string): Promise<boolean> =>
    new Promise((resolve) => setConfirm({ sql, resolve }))

  const handleConfirm = (ok: boolean) => {
    confirm?.resolve(ok)
    setConfirm(null)
  }

  const handleSubmit = async (q: string, mode: 'nl' | 'sql') => {
    if (!connection) return
    setError(null)
    setLoading(true)
    try {
      let res: QueryResponse
      if (mode === 'nl') {
        res = await queryNaturalLanguage(q, connection, schema ?? undefined)
        setIsNLResult(true)
      } else {
        if (DESTRUCTIVE_PATTERN.test(q)) {
          const ok = await askConfirmation(q)
          if (!ok) { setLoading(false); return }
        }
        res = await executeRawSQL(q, connection)
        setIsNLResult(false)
      }
      setResult(res)
      // Push undo entry when the server captured one
      if (res.undo_sql) {
        const label = mode === 'nl' ? q.slice(0, 48) : res.sql.slice(0, 48)
        setUndoStack((prev) => [...prev, { sql: res.undo_sql!, label }])
      }
    } catch (err: unknown) {
      setError(extractError(err))
    } finally {
      setLoading(false)
    }
  }

  // Pop the top of the undo stack and execute it
  const handleRevert = async () => {
    if (!connection || undoStack.length === 0) return
    const top = undoStack[undoStack.length - 1]
    setUndoStack((prev) => prev.slice(0, -1))
    setError(null)
    setLoading(true)
    try {
      const res = await executeRawSQL(top.sql, connection)
      setResult({ ...res, sql: top.sql })
      setIsNLResult(false)
      // If the revert itself can be reversed, push that too
      if (res.undo_sql) {
        setUndoStack((prev) => [...prev, { sql: res.undo_sql!, label: `Undo of: ${top.label}` }])
      }
    } catch (err: unknown) {
      setError(`Revert failed: ${extractError(err)}`)
      // Put the entry back so user can try again
      setUndoStack((prev) => [...prev, top])
    } finally {
      setLoading(false)
    }
  }

  const handleRerunSQL = (sql: string) => {
    setPendingSQL(sql)
    setQueryMode('sql')
  }

  const isConnected = connection !== null

  return (
    <div className="app-shell">
      {/* ── Top Bar ─────────────────────────────────────────────────────── */}
      <header className="topbar" role="banner">
        <div className="topbar-logo">
          <div className="logo-icon" aria-hidden="true">
            <Zap size={18} color="#fff" />
          </div>
          <span>SQL Copilot</span>
          <span style={{ color: 'var(--text-muted)', fontWeight: 400, fontSize: 13 }}>
            AI-Powered SQL Assistant
          </span>
        </div>
        <div className="topbar-status" aria-live="polite">
          <span
            className={`status-dot ${isConnected ? 'connected' : ''}`}
            role="img"
            aria-label={isConnected ? 'Connected' : 'Disconnected'}
          />
          {isConnected
            ? `${connection.db_type.toUpperCase()} · ${connection.database.replace(/.*[\\/]/, '')}`
            : 'Not connected'}
        </div>
      </header>

      {/* ── Main ────────────────────────────────────────────────────────── */}
      <div className="main-content">

        {/* ── Sidebar (resizable width) ──────────────────────────────────── */}
        <aside
          className="sidebar"
          style={{ width: sidebar.width, minWidth: sidebar.width, maxWidth: sidebar.width }}
          aria-label="Database connection and schema"
        >
          <div className="sidebar-section">
            <h3>Connection</h3>
            <ConnectionForm
              onConnect={handleConnect}
              isConnected={isConnected}
              currentConnection={connection}
            />
          </div>
          <div className="sidebar-section" style={{ borderBottom: 'none', paddingBottom: 0 }}>
            <h3>Schema {schema && `(${Object.keys(schema).length} tables)`}</h3>
          </div>
          <SchemaViewer schema={schema} />
        </aside>

        {/* ── Horizontal drag handle ──────────────────────────────────────── */}
        <div
          className="resize-handle resize-handle--vertical"
          onMouseDown={sidebar.onMouseDown}
          title="Drag to resize sidebar"
          role="separator"
          aria-label="Resize sidebar"
          aria-orientation="vertical"
        >
          <div className="resize-handle__grip" />
        </div>

        {/* ── Workspace ──────────────────────────────────────────────────── */}
        <main className="workspace" id="main-workspace" aria-label="Query workspace">

          {/* Query Input (resizable height) */}
          <div style={{ height: query.height, minHeight: query.height, flexShrink: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <QueryInput
              mode={queryMode}
              onModeChange={setQueryMode}
              onSubmit={handleSubmit}
              onRevert={handleRevert}
              undoCount={undoStack.length}
              undoLabel={undoStack.length > 0 ? undoStack[undoStack.length - 1].label : ''}
              loading={loading}
              disabled={!isConnected}
              initialSql={pendingSQL}
            />
          </div>

          {/* ── Vertical drag handle ──────────────────────────────────────── */}
          <div
            className="resize-handle resize-handle--horizontal"
            onMouseDown={query.onMouseDown}
            title="Drag to resize query panel"
            role="separator"
            aria-label="Resize query panel"
            aria-orientation="horizontal"
          >
            <div className="resize-handle__grip resize-handle__grip--h" />
          </div>

          {/* Results (takes remaining space) */}
          <div className="results-area" aria-live="polite" aria-label="Query results">
            {error && (
              <div className="alert alert-error" role="alert">
                <AlertTriangle size={14} style={{ flexShrink: 0, marginTop: 1 }} />
                <div>
                  <strong>Error</strong>
                  <p style={{ marginTop: 2, opacity: 0.85 }}>{error}</p>
                </div>
              </div>
            )}

            {loading && (
              <div className="loading-state" aria-label="Loading">
                <div className="spinner spinner-lg" />
                <p>
                  {queryMode === 'nl'
                    ? 'Claude is generating your SQL…'
                    : 'Executing SQL…'}
                </p>
              </div>
            )}

            {!loading && result && (
              <ResultsTable
                sql={result.sql}
                columns={result.columns}
                rows={result.rows}
                rowcount={result.rowcount}
                onRerunSQL={handleRerunSQL}
                isNLResult={isNLResult}
              />
            )}

            {!loading && !result && !error && (
              <div className="results-empty" aria-label="No results yet">
                <div className="results-empty-icon" aria-hidden="true">
                  <Zap size={24} color="var(--accent-blue)" />
                </div>
                <h3>Ready to query</h3>
                <p>
                  {isConnected
                    ? 'Type a question in plain English or write raw SQL, then hit Run.'
                    : 'Connect to a database using the panel on the left to get started.'}
                </p>
                {isConnected && (
                  <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 8, width: '100%', maxWidth: 400 }}>
                    {[
                      'Show me all tables and their row counts',
                      'Find the top 10 records with the highest values',
                      'What are the most recent entries?',
                    ].map((hint) => (
                      <button
                        key={hint}
                        className="btn btn-secondary"
                        style={{ fontSize: 12, justifyContent: 'flex-start', textAlign: 'left' }}
                        onClick={() => { setQueryMode('nl'); handleSubmit(hint, 'nl') }}
                      >
                        <span style={{ opacity: 0.5 }}>✦</span> {hint}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </main>
      </div>

      {/* ── Destructive SQL Confirmation Modal ──────────────────────────── */}
      {confirm && (
        <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
          <div className="modal">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
              <AlertTriangle size={20} color="var(--accent-red)" />
              <h3 id="confirm-title" style={{ color: 'var(--accent-red)' }}>
                Destructive Operation
              </h3>
            </div>
            <p>
              This SQL statement may modify or delete data. Please review carefully before executing.
            </p>
            <div className="sql-block" style={{ marginBottom: 20, fontSize: 13 }}>
              <pre style={{ padding: '12px 16px', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', overflowX: 'auto' }}>
                {confirm.sql}
              </pre>
            </div>
            <div className="modal-actions">
              <button id="cancel-confirm-btn"  className="btn btn-secondary" onClick={() => handleConfirm(false)}>Cancel</button>
              <button id="proceed-confirm-btn" className="btn btn-danger"    onClick={() => handleConfirm(true)}>Yes, Execute</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
