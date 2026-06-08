import { useState } from 'react'
import { Database, Plug, Eye, EyeOff } from 'lucide-react'
import type { ConnectionParams, SchemaInfo } from '../api/client'
import { connectToDatabase } from '../api/client'

interface ConnectionFormProps {
  onConnect: (params: ConnectionParams, schema: SchemaInfo) => void
  isConnected: boolean
  currentConnection: ConnectionParams | null
}

const DB_DEFAULTS: Record<string, { port: number; placeholder: string }> = {
  postgresql: { port: 5432, placeholder: 'localhost' },
  mysql:      { port: 3306, placeholder: 'localhost' },
  sqlite:     { port: 0,    placeholder: '/path/to/database.db' },
}

export function ConnectionForm({ onConnect, isConnected, currentConnection }: ConnectionFormProps) {
  const [dbType,   setDbType]   = useState(currentConnection?.db_type   ?? 'postgresql')
  const [host,     setHost]     = useState(currentConnection?.host       ?? 'localhost')
  const [port,     setPort]     = useState<string>(
    currentConnection?.port?.toString() ?? '5432',
  )
  const [database, setDatabase] = useState(currentConnection?.database  ?? '')
  const [username, setUsername] = useState(currentConnection?.username  ?? '')
  const [password, setPassword] = useState(currentConnection?.password  ?? '')
  const [showPass, setShowPass] = useState(false)
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState<string | null>(null)

  const isSQLite = dbType === 'sqlite'

  const handleDbTypeChange = (t: string) => {
    setDbType(t)
    setPort(DB_DEFAULTS[t]?.port?.toString() ?? '')
    setError(null)
  }

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const params: ConnectionParams = {
        db_type: dbType,
        database,
        ...(isSQLite ? {} : {
          host,
          port: port ? parseInt(port) : undefined,
          username,
          password,
        }),
      }
      const result = await connectToDatabase(params)
      onConnect(params, result.schema)
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Connection failed. Check credentials and try again.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form className="conn-form" onSubmit={handleConnect} id="connection-form">
      {/* DB Type */}
      <div className="form-group">
        <label className="form-label" htmlFor="db-type-select">Database</label>
        <select
          id="db-type-select"
          className="form-select"
          value={dbType}
          onChange={(e) => handleDbTypeChange(e.target.value)}
        >
          <option value="postgresql">PostgreSQL</option>
          <option value="mysql">MySQL</option>
          <option value="sqlite">SQLite</option>
        </select>
      </div>

      {/* Database / File */}
      <div className="form-group">
        <label className="form-label" htmlFor="database-input">
          {isSQLite ? 'File Path' : 'Database Name'}
        </label>
        <input
          id="database-input"
          className="form-input"
          type="text"
          placeholder={isSQLite ? '/path/to/db.sqlite' : 'my_database'}
          value={database}
          onChange={(e) => setDatabase(e.target.value)}
          required
        />
      </div>

      {!isSQLite && (
        <>
          {/* Host + Port */}
          <div className="form-row">
            <div className="form-group">
              <label className="form-label" htmlFor="host-input">Host</label>
              <input
                id="host-input"
                className="form-input"
                type="text"
                placeholder="localhost"
                value={host}
                onChange={(e) => setHost(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="port-input">Port</label>
              <input
                id="port-input"
                className="form-input"
                type="number"
                placeholder={DB_DEFAULTS[dbType]?.port?.toString()}
                value={port}
                onChange={(e) => setPort(e.target.value)}
              />
            </div>
          </div>

          {/* User */}
          <div className="form-group">
            <label className="form-label" htmlFor="username-input">Username</label>
            <input
              id="username-input"
              className="form-input"
              type="text"
              placeholder="postgres"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>

          {/* Password */}
          <div className="form-group">
            <label className="form-label" htmlFor="password-input">Password</label>
            <div style={{ position: 'relative' }}>
              <input
                id="password-input"
                className="form-input"
                type={showPass ? 'text' : 'password'}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{ paddingRight: 36 }}
              />
              <button
                type="button"
                onClick={() => setShowPass((p) => !p)}
                style={{
                  position: 'absolute',
                  right: 8,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: 'var(--text-muted)',
                  display: 'flex',
                  alignItems: 'center',
                }}
                aria-label={showPass ? 'Hide password' : 'Show password'}
              >
                {showPass ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
          </div>
        </>
      )}

      {error && (
        <div className="alert alert-error" role="alert">
          <Database size={14} style={{ flexShrink: 0, marginTop: 1 }} />
          <span>{error}</span>
        </div>
      )}

      <button
        type="submit"
        id="connect-btn"
        className="btn btn-primary"
        disabled={loading || !database}
        style={{ marginTop: 4 }}
      >
        {loading ? (
          <>
            <span className="spinner" />
            Connecting…
          </>
        ) : (
          <>
            <Plug size={14} />
            {isConnected ? 'Reconnect' : 'Connect'}
          </>
        )}
      </button>

      {isConnected && (
        <div className="alert alert-success" role="status">
          ✓ Connected to <strong>{currentConnection?.database.replace(/.*[\\/]/, '')}</strong>
        </div>
      )}
    </form>
  )
}
