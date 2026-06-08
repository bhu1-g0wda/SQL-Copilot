import { useState } from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Copy, Check, Play, ChevronLeft, ChevronRight } from 'lucide-react'

const PAGE_SIZE = 50

interface ResultsTableProps {
  sql: string
  columns: string[]
  rows: (string | number | boolean | null)[][]
  rowcount: number
  onRerunSQL: (sql: string) => void
  isNLResult: boolean
}

export function ResultsTable({
  sql,
  columns,
  rows,
  rowcount,
  onRerunSQL,
  isNLResult,
}: ResultsTableProps) {
  const [copied,  setCopied]  = useState(false)
  const [page,    setPage]    = useState(0)

  const totalPages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE))
  const pagedRows  = rows.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(sql)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const formatCell = (val: string | number | boolean | null): string => {
    if (val === null || val === undefined) return 'NULL'
    if (typeof val === 'boolean') return val ? 'true' : 'false'
    return String(val)
  }

  const isNull = (val: string | number | boolean | null) =>
    val === null || val === undefined

  return (
    <>
      {/* ── SQL Block ──────────────────────────────────────────────────── */}
      <div className="sql-block">
        <div className="sql-block-header">
          <div className="sql-block-label">
            <span className="dot" />
            {isNLResult ? 'Generated SQL' : 'Executed SQL'}
          </div>
          <div className="sql-block-actions">
            <button
              id="copy-sql-btn"
              className="btn btn-secondary btn-sm"
              onClick={handleCopy}
              aria-label="Copy SQL to clipboard"
            >
              {copied ? <Check size={12} /> : <Copy size={12} />}
              {copied ? 'Copied!' : 'Copy'}
            </button>
            {isNLResult && (
              <button
                id="rerun-sql-btn"
                className="btn btn-secondary btn-sm"
                onClick={() => onRerunSQL(sql)}
                aria-label="Edit and re-run this SQL"
              >
                <Play size={12} />
                Edit &amp; Re-run
              </button>
            )}
          </div>
        </div>

        <SyntaxHighlighter
          language="sql"
          style={vscDarkPlus}
          customStyle={{
            margin: 0,
            background: 'transparent',
            padding: '16px',
            fontSize: '13px',
            lineHeight: '1.7',
            fontFamily: 'var(--font-mono)',
          }}
          wrapLongLines
        >
          {sql}
        </SyntaxHighlighter>
      </div>

      {/* ── Results Table ──────────────────────────────────────────────── */}
      <div className="results-card">
        <div className="results-card-header">
          <div className="results-meta">
            {columns.length > 0 ? (
              <span className="results-badge">
                ✓ {rowcount} {rowcount === 1 ? 'row' : 'rows'}
              </span>
            ) : (
              <span className="affected-badge">
                ⚡ {rowcount} {rowcount === 1 ? 'row' : 'rows'} affected
              </span>
            )}
            {columns.length > 0 && (
              <span>{columns.length} columns</span>
            )}
          </div>
          {totalPages > 1 && (
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Page {page + 1} of {totalPages}
            </span>
          )}
        </div>

        {columns.length > 0 ? (
          <>
            <div className="table-wrapper" role="region" aria-label="Query results">
              <table className="data-table" id="results-data-table">
                <thead>
                  <tr>
                    <th className="row-idx">#</th>
                    {columns.map((col) => (
                      <th key={col} title={col}>{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {pagedRows.map((row, ri) => (
                    <tr key={ri}>
                      <td className="row-idx">{page * PAGE_SIZE + ri + 1}</td>
                      {row.map((cell, ci) => (
                        <td
                          key={ci}
                          className={isNull(cell) ? 'null-val' : ''}
                          title={formatCell(cell)}
                        >
                          {formatCell(cell)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="pagination">
                <span className="pagination-info">
                  Showing {page * PAGE_SIZE + 1}–
                  {Math.min((page + 1) * PAGE_SIZE, rows.length)} of {rows.length} rows
                </span>
                <div className="pagination-controls" aria-label="Pagination">
                  <button
                    id="prev-page-btn"
                    className="page-btn"
                    onClick={() => setPage((p) => p - 1)}
                    disabled={page === 0}
                    aria-label="Previous page"
                  >
                    <ChevronLeft size={14} />
                  </button>
                  {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                    const pg = totalPages <= 7
                      ? i
                      : page < 4
                        ? i
                        : page > totalPages - 5
                          ? totalPages - 7 + i
                          : page - 3 + i
                    return (
                      <button
                        key={pg}
                        className={`page-btn ${pg === page ? 'active' : ''}`}
                        onClick={() => setPage(pg)}
                        aria-label={`Page ${pg + 1}`}
                        aria-current={pg === page ? 'page' : undefined}
                      >
                        {pg + 1}
                      </button>
                    )
                  })}
                  <button
                    id="next-page-btn"
                    className="page-btn"
                    onClick={() => setPage((p) => p + 1)}
                    disabled={page >= totalPages - 1}
                    aria-label="Next page"
                  >
                    <ChevronRight size={14} />
                  </button>
                </div>
              </div>
            )}
          </>
        ) : (
          <div style={{ padding: '24px 16px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: 13 }}>
            Query executed successfully — {rowcount} {rowcount === 1 ? 'row' : 'rows'} affected
          </div>
        )}
      </div>
    </>
  )
}
