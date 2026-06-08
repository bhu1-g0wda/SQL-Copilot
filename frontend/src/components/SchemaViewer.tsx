import { useState } from 'react'
import { Database, ChevronRight, Key, Link } from 'lucide-react'
import type { SchemaInfo } from '../api/client'

interface SchemaViewerProps {
  schema: SchemaInfo | null
}

export function SchemaViewer({ schema }: SchemaViewerProps) {
  const [openTables, setOpenTables] = useState<Set<string>>(new Set())

  const toggleTable = (name: string) => {
    setOpenTables((prev) => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  if (!schema) {
    return (
      <div className="schema-empty">
        <div className="schema-empty-icon">🗄️</div>
        <p>Connect to a database to explore its schema</p>
      </div>
    )
  }

  const tableNames = Object.keys(schema)

  if (tableNames.length === 0) {
    return (
      <div className="schema-empty">
        <div className="schema-empty-icon">📭</div>
        <p>No tables found in this database</p>
      </div>
    )
  }

  return (
    <div className="schema-tree">
      {tableNames.map((tableName) => {
        const tableInfo = schema[tableName]
        const isOpen = openTables.has(tableName)
        return (
          <div key={tableName} className="table-node">
            <div
              className={`table-header ${isOpen ? 'open' : ''}`}
              onClick={() => toggleTable(tableName)}
            >
              <ChevronRight
                size={14}
                className={`table-chevron ${isOpen ? 'open' : ''}`}
              />
              <Database size={14} className="table-icon" />
              <span className="table-name">{tableName}</span>
              <span className="table-count">{tableInfo.columns.length}</span>
            </div>
            {isOpen && (
              <div className="column-list">
                {tableInfo.columns.map((col) => {
                  const isPK = tableInfo.primary_keys.includes(col.name)
                  const isFK = tableInfo.foreign_keys.some((fk) =>
                    fk.constrained_columns.includes(col.name),
                  )
                  return (
                    <div key={col.name} className="column-item">
                      {isPK ? (
                        <Key size={11} className="column-icon pk" />
                      ) : isFK ? (
                        <Link size={11} className="column-icon" style={{ color: 'var(--accent-cyan)' }} />
                      ) : (
                        <span style={{ width: 11 }} />
                      )}
                      <span className="column-name">{col.name}</span>
                      <span className="column-type">
                        {col.type.length > 16
                          ? col.type.slice(0, 16) + '…'
                          : col.type}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
