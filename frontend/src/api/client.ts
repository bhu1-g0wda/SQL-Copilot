import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

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
  schema: SchemaInfo
  message: string
}

export interface QueryResponse {
  success: boolean
  sql: string
  columns: string[]
  rows: (string | number | boolean | null)[][]
  rowcount: number
  undo_sql?: string | null   // present for INSERT/UPDATE/DELETE; null for SELECT or if capture failed
}

export const connectToDatabase = async (
  params: ConnectionParams,
): Promise<ConnectResponse> => {
  const { data } = await api.post<ConnectResponse>('/connect', params)
  return data
}

export const queryNaturalLanguage = async (
  query: string,
  connection: ConnectionParams,
  schemaInfo?: SchemaInfo,
): Promise<QueryResponse> => {
  const { data } = await api.post<QueryResponse>('/query', {
    natural_language_query: query,
    ...connection,
    schema_info: schemaInfo,
  })
  return data
}

export const executeRawSQL = async (
  sql: string,
  connection: ConnectionParams,
): Promise<QueryResponse> => {
  const { data } = await api.post<QueryResponse>('/execute', {
    sql,
    ...connection,
  })
  return data
}

export const checkHealth = async (): Promise<{ status: string }> => {
  const { data } = await api.get('/health')
  return data
}
