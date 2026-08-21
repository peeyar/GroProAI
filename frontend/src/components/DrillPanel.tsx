import { fmtM } from '../format'
import type { DrillResponse, DrillRow } from '../types'

interface Crumb {
  level: string
  name: string
}

interface Props {
  data: DrillResponse | null
  loading: boolean
  crumbs: Crumb[]
  rootLabel: string
  metric: { key: string; label: string }
  onCrumbClick: (index: number) => void
  onDescend: (name: string) => void
  onPin: () => void
}

export default function DrillPanel({
  data,
  loading,
  crumbs,
  rootLabel,
  metric,
  onCrumbClick,
  onDescend,
  onPin,
}: Props) {
  const rows = data?.rows ?? []
  const metricValue = (row: DrillRow) =>
    metric.key === 'total' ? row.total : (row.values[metric.key] ?? 0)
  const maxAbs = Math.max(...rows.map((r) => Math.abs(metricValue(r))), 1)
  const canDescend = Boolean(data?.nextLevel)

  return (
    <div>
      <div className="panel-head">
        <div>
          <h2 className="card-title">Drill-down — {metric.label}</h2>
          <div className="crumbs">
            <button className="crumb" onClick={() => onCrumbClick(-1)}>
              All {rootLabel.toLowerCase()}s
            </button>
            {crumbs.map((c, i) => (
              <span key={`${c.level}:${c.name}`}>
                <span className="crumb-sep">›</span>
                <button className="crumb" onClick={() => onCrumbClick(i)}>
                  {c.name}
                </button>
              </span>
            ))}
          </div>
        </div>
        {rows.length > 0 && (
          <button className="ghost-btn" onClick={onPin} title="Pin this view to My View">
            📌 Pin
          </button>
        )}
      </div>

      {loading && <p className="hint">Loading…</p>}
      {!loading && data?.note && <div className="banner-info">{data.note}</div>}

      {!loading && rows.length > 0 && (
        <div className="drill-table" role="table" aria-label={`${metric.label} by ${data?.label}`}>
          <div className="drill-row drill-header" role="row">
            <span>{data?.label}</span>
            <span />
            <span className="num">{metric.label}</span>
            <span className="num muted">Total</span>
          </div>
          {rows.map((row) => {
            const v = metricValue(row)
            const widthPct = (Math.abs(v) / maxAbs) * 100
            return (
              <button
                key={row.name}
                className={`drill-row${canDescend ? ' clickable' : ''}`}
                role="row"
                onClick={canDescend ? () => onDescend(row.name) : undefined}
                title={
                  canDescend ? `Open ${row.name}` : `${row.name} — deepest level (item)`
                }
              >
                <span className="drill-name">{row.name}</span>
                <span className="drill-track" aria-hidden="true">
                  <span
                    className="drill-fill"
                    style={{
                      width: `${Math.max(widthPct, 1.5)}%`,
                      background: v >= 0 ? 'var(--pos)' : 'var(--neg)',
                    }}
                  />
                </span>
                <span className="num">{fmtM(v)}</span>
                <span className="num muted">{fmtM(row.total)}</span>
              </button>
            )
          })}
        </div>
      )}

      {!loading && canDescend && rows.length > 0 && (
        <p className="hint">Click a row to drill into {data?.nextLevel} level.</p>
      )}
    </div>
  )
}
