import { useRef, useState } from 'react'
import { fmtM } from '../format'
import type { WaterfallBar, WaterfallInput } from '../waterfall'
import { extent, layoutWaterfall } from '../waterfall'

interface Props {
  buckets: WaterfallInput[]
  total: WaterfallInput
  selectedKey?: string | null
  onSelect?: (key: string) => void
  descriptions?: Record<string, string>
  compact?: boolean
}

interface Tip {
  x: number
  y: number
  label: string
  value: number
  description?: string
}

export default function Waterfall({
  buckets,
  total,
  selectedKey,
  onSelect,
  descriptions,
  compact = false,
}: Props) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const [tip, setTip] = useState<Tip | null>(null)

  const bars = layoutWaterfall(buckets, total)
  const [lo, hi] = extent(bars)
  const W = 760
  const H = compact ? 220 : 300
  const M = { top: 26, right: 8, bottom: 44, left: 8 }
  const plotW = W - M.left - M.right
  const plotH = H - M.top - M.bottom
  const span = hi - lo || 1
  const y = (v: number) => M.top + ((hi - v) / span) * plotH
  const slot = plotW / bars.length
  const barW = Math.min(76, slot * 0.6)

  const showTip = (e: React.MouseEvent, b: WaterfallBar) => {
    const rect = wrapRef.current?.getBoundingClientRect()
    if (!rect) return
    setTip({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
      label: b.label,
      value: b.value,
      description: descriptions?.[b.key],
    })
  }

  return (
    <div className="viz-wrap" ref={wrapRef}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="waterfall"
        role="img"
        aria-label={`Revenue bridge waterfall: ${bars
          .map((b) => `${b.label} ${fmtM(b.value)}`)
          .join(', ')}`}
      >
        {[0.25, 0.5, 0.75].map((t) => (
          <line
            key={t}
            x1={M.left}
            x2={W - M.right}
            y1={M.top + t * plotH}
            y2={M.top + t * plotH}
            stroke="var(--grid)"
            strokeWidth={1}
          />
        ))}
        <line
          x1={M.left}
          x2={W - M.right}
          y1={y(0)}
          y2={y(0)}
          stroke="var(--baseline)"
          strokeWidth={1.5}
        />

        {bars.map((b, i) => {
          const x = M.left + i * slot + (slot - barW) / 2
          const yTop = y(Math.max(b.start, b.end))
          const h = Math.max(2, Math.abs(y(b.end) - y(b.start)))
          const fill =
            b.kind === 'pos' ? 'var(--pos)' : b.kind === 'neg' ? 'var(--neg)' : 'var(--total-bar)'
          const dimmed = selectedKey != null && selectedKey !== b.key
          const labelWords = b.label.split(' ')
          const line1 = labelWords[0]
          const line2 = labelWords.slice(1).join(' ')
          const valueY = b.value >= 0 || b.kind === 'total' ? yTop - 7 : yTop + h + 15

          return (
            <g key={b.key}>
              {i < bars.length - 1 && (
                <line
                  x1={x + barW}
                  x2={M.left + (i + 1) * slot + (slot - barW) / 2}
                  y1={y(b.end)}
                  y2={y(b.end)}
                  stroke="var(--baseline)"
                  strokeWidth={1}
                  strokeDasharray="3 3"
                />
              )}
              <rect
                x={x}
                y={yTop}
                width={barW}
                height={h}
                rx={3}
                fill={fill}
                opacity={dimmed ? 0.4 : 1}
                className={onSelect ? 'wf-bar clickable' : 'wf-bar'}
                role={onSelect ? 'button' : undefined}
                tabIndex={onSelect ? 0 : undefined}
                aria-label={`${b.label}: ${fmtM(b.value)}`}
                onClick={() => onSelect?.(b.key)}
                onKeyDown={(e) => e.key === 'Enter' && onSelect?.(b.key)}
                onMouseMove={(e) => showTip(e, b)}
                onMouseLeave={() => setTip(null)}
              />
              <text x={x + barW / 2} y={valueY} textAnchor="middle" className="wf-value">
                {fmtM(b.value)}
              </text>
              <text x={x + barW / 2} y={H - M.bottom + 16} textAnchor="middle" className="wf-name">
                <tspan x={x + barW / 2}>{line1}</tspan>
                {line2 && (
                  <tspan x={x + barW / 2} dy={12}>
                    {line2}
                  </tspan>
                )}
              </text>
            </g>
          )
        })}
      </svg>
      {tip && (
        <div className="tooltip" style={{ left: tip.x, top: tip.y }}>
          <strong>
            {tip.label} · {fmtM(tip.value)}
          </strong>
          {tip.description && <p>{tip.description}</p>}
        </div>
      )}
    </div>
  )
}
