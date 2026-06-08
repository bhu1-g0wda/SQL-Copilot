import { useState, useRef, useEffect } from 'react'
import { Sparkles, Code2, Play, RotateCcw, Undo2 } from 'lucide-react'

interface QueryInputProps {
  mode: 'nl' | 'sql'
  onModeChange: (mode: 'nl' | 'sql') => void
  onSubmit: (query: string, mode: 'nl' | 'sql') => void
  onRevert: () => void
  undoCount: number
  undoLabel: string
  loading: boolean
  disabled: boolean
  initialSql?: string
}

export function QueryInput({
  mode,
  onModeChange,
  onSubmit,
  onRevert,
  undoCount,
  undoLabel,
  loading,
  disabled,
  initialSql = '',
}: QueryInputProps) {
  const [nlQuery,  setNlQuery]  = useState('')
  const [rawSql,   setRawSql]   = useState(initialSql)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (initialSql) setRawSql(initialSql)
  }, [initialSql])

  const currentValue    = mode === 'nl' ? nlQuery : rawSql
  const setCurrentValue = mode === 'nl' ? setNlQuery : setRawSql

  const handleSubmit = () => {
    if (!currentValue.trim() || loading || disabled) return
    onSubmit(currentValue.trim(), mode)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleClear = () => {
    setCurrentValue('')
    textareaRef.current?.focus()
  }

  const placeholder =
    mode === 'nl'
      ? 'Ask anything in plain English…\ne.g. "Show me the top 10 customers by total revenue" or "How many orders were placed last month?"'
      : 'Write your SQL query here…\ne.g. SELECT customer_id, SUM(amount) FROM orders GROUP BY customer_id ORDER BY 2 DESC LIMIT 10;'

  return (
    <div className="query-area">
      {/* Mode Toggle */}
      <div className="query-mode-toggle" role="group" aria-label="Query mode">
        <button
          id="nl-mode-btn"
          className={`mode-btn ${mode === 'nl' ? 'active' : ''}`}
          onClick={() => onModeChange('nl')}
          type="button"
          aria-pressed={mode === 'nl'}
        >
          <Sparkles size={13} />
          Natural Language
        </button>
        <button
          id="sql-mode-btn"
          className={`mode-btn ${mode === 'sql' ? 'active' : ''}`}
          onClick={() => onModeChange('sql')}
          type="button"
          aria-pressed={mode === 'sql'}
        >
          <Code2 size={13} />
          Raw SQL
        </button>
      </div>

      {/* Textarea */}
      <div className="query-input-wrapper">
        <textarea
          ref={textareaRef}
          id={mode === 'nl' ? 'nl-query-input' : 'sql-query-input'}
          className={`query-textarea ${mode === 'sql' ? 'mono' : ''}`}
          placeholder={placeholder}
          value={currentValue}
          onChange={(e) => setCurrentValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled || loading}
          rows={mode === 'nl' ? 4 : 6}
          spellCheck={mode === 'nl'}
          aria-label={mode === 'nl' ? 'Natural language query' : 'SQL query'}
        />
      </div>

      {/* Actions */}
      <div className="query-actions">
        <span className="query-hint">
          <kbd className="kbd">Ctrl</kbd>+<kbd className="kbd">Enter</kbd> to run
          {mode === 'nl' && <>&nbsp;·&nbsp;AI will generate SQL for you</>}
        </span>

        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {/* Clear */}
          {currentValue && (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={handleClear}
              id="clear-query-btn"
              aria-label="Clear query"
            >
              <RotateCcw size={12} />
              Clear
            </button>
          )}

          {/* ── Revert button ─────────────────────────────────────────── */}
          <div className="revert-btn-wrap" title={undoCount > 0 ? `Revert: ${undoLabel}` : ''}>
            <button
              id="revert-btn"
              type="button"
              className="btn btn-revert"
              onClick={onRevert}
              disabled={undoCount === 0 || loading || disabled}
              aria-label={`Revert last operation (${undoCount} available)`}
            >
              {loading && undoCount > 0 ? (
                <span className="spinner" />
              ) : (
                <Undo2 size={13} />
              )}
              Revert
              {undoCount > 0 && (
                <span className="revert-badge" aria-label={`${undoCount} operations to revert`}>
                  {undoCount}
                </span>
              )}
            </button>
          </div>

          {/* Run */}
          <button
            id="run-query-btn"
            type="button"
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={!currentValue.trim() || loading || disabled}
            aria-label="Run query"
          >
            {loading ? (
              <>
                <span className="spinner" />
                {mode === 'nl' ? 'Generating SQL…' : 'Executing…'}
              </>
            ) : (
              <>
                <Play size={13} />
                {mode === 'nl' ? 'Generate & Run' : 'Execute SQL'}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
