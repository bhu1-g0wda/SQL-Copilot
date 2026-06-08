import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

// ── Session state ─────────────────────────────────────────────────────────────
// After a successful /api/connect the server returns a session_id.
// All subsequent requests send this token instead of raw credentials.
let _sessionId: string | null = null

export function getSessionId(): string | null {
  return _sessionId
}

export function clearSession(): void {
  _sessionId = null
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ConnectionParams {
  db_type: string
  host?: string
  port?: number
  database: string
  username?: string
  password?: string
}

export interface ColumnInfo {
  name: string
  type: string
  nullable: boolean
}

export interface TableInfo {
  columns: ColumnInfo[]
  primary_keys: string[]
  foreign_keys: {
    constrained_columns: string[]
    referred_table: string
    referred_columns: string[]
  }[]
}

export interface SchemaInfo {
  [tableName: string]: TableInfo
}

export interface ConnectResponse {
  success: boolean
  session_id: string
  schema: SchemaInfo
  message: string
}

export interface QueryResponse {
  success: boolean
  sql: string
  columns: string[]
  rows: (string | number | boolean | null)[][]
  rowcount: number
  undo_sql?: string | null
}

// ── API functions ─────────────────────────────────────────────────────────────

/**
 * Connect to a database.
 * Stores the returned session_id for use in all subsequent requests.
 * Credentials are only ever sent in this one call.
 */
export const connectToDatabase = async (
  params: ConnectionParams,
): Promise<ConnectResponse> => {
  const { data } = await api.post<ConnectResponse>('/connect', params)
  _sessionId = data.session_id   // store — never send credentials again
  return data
}

/**
 * Disconnect: invalidate the server-side session.
 */
export const disconnectSession = async (): Promise<void> => {
  if (!_sessionId) return
  await api.delete(`/session/${_sessionId}`).catch(() => { /* best-effort */ })
  _sessionId = null
}

/**
 * Convert a natural-language query to SQL and execute it.
 * Sends session_id only — no credentials in transit.
 */
export const queryNaturalLanguage = async (
  query: string,
  _connection: ConnectionParams,   // kept for backward compat; session_id used instead
  schemaInfo?: SchemaInfo,
): Promise<QueryResponse> => {
  const { data } = await api.post<QueryResponse>('/query', {
    session_id: _sessionId,
    natural_language_query: query,
    ...(schemaInfo ? { schema_info: schemaInfo } : {}),
  })
  return data
}

/**
 * Execute raw SQL.
 * Sends session_id only — no credentials in transit.
 */
export const executeRawSQL = async (
  sql: string,
  _connection: ConnectionParams,   // kept for backward compat; session_id used instead
): Promise<QueryResponse> => {
  const { data } = await api.post<QueryResponse>('/execute', {
    session_id: _sessionId,
    sql,
  })
  return data
}

export const checkHealth = async (): Promise<{ status: string }> => {
  const { data } = await api.get('/health')
  return data
}
