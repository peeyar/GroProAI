import type { ChartSpec, PinnedCard } from '../types'
import MiniBar from './MiniBar'
import Waterfall from './Waterfall'

interface Props {
  cards: PinnedCard[]
  onRemove: (id: string) => void
}

function PinnedChart({ chart }: { chart: ChartSpec }) {
  if (chart.chartType === 'waterfall') {
    return (
      <Waterfall
        compact
        buckets={chart.data.map((d) => ({ key: d.name, label: d.name, value: d.value }))}
        total={{
          key: 'total',
          label: 'Total',
          value: chart.total ?? chart.data.reduce((s, d) => s + d.value, 0),
        }}
      />
    )
  }
  return <MiniBar data={chart.data} />
}

export default function MyView({ cards, onRemove }: Props) {
  if (cards.length === 0) return null
  return (
    <div className="card">
      <h2 className="card-title">My View — pinned ({cards.length})</h2>
      <p className="hint">
        Pins persist in this browser. Per-user server-side layouts arrive in Phase 4.
      </p>
      <div className="myview-grid">
        {cards.map((card) => (
          <div key={card.id} className="pin-card">
            <div className="pin-head">
              <span className="pin-title" title={card.title}>
                {card.title}
              </span>
              <button
                className="ghost-btn small"
                onClick={() => onRemove(card.id)}
                title="Unpin"
                aria-label={`Unpin ${card.title}`}
              >
                ✕
              </button>
            </div>
            <PinnedChart chart={card.chart} />
            <span className="pin-tag">from {card.createdFrom}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
