import { useEffect, useMemo, useState } from 'react'
import { fetchBridge, fetchDrill, fetchFreshness, fetchMetadata, fetchNarrative } from './api'
import DrillPanel from './components/DrillPanel'
import ChatPanel from './components/ChatPanel'
import MyView from './components/MyView'
import Waterfall from './components/Waterfall'
import { fmtM } from './format'
import type {
  BridgeResponse,
  ChartSpec,
  DrillResponse,
  Flavor,
  FreshnessResponse,
  MetadataResponse,
  PinnedCard,
} from './types'

const OFFLINE =
  'The demo backend is not reachable. Start it with: cd backend && .venv/bin/uvicorn app.main:app'

const PINS_KEY = 'gropro-pins'

interface Crumb {
  level: string
  name: string
}

export default function App() {
  const [flavor, setFlavor] = useState<Flavor>('yoy')
  const [meta, setMeta] = useState<MetadataResponse | null>(null)
  const [bridge, setBridge] = useState<BridgeResponse | null>(null)
  const [narrative, setNarrative] = useState('')
  const [freshness, setFreshness] = useState<FreshnessResponse | null>(null)
  const [selected, setSelected] = useState('total')
  const [crumbs, setCrumbs] = useState<Crumb[]>([])
  const [drill, setDrill] = useState<DrillResponse | null>(null)
  const [drillLoading, setDrillLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pins, setPins] = useState<PinnedCard[]>(() => {
    try {
      return JSON.parse(localStorage.getItem(PINS_KEY) ?? '[]') as PinnedCard[]
    } catch {
      return []
    }
  })

  useEffect(() => {
    localStorage.setItem(PINS_KEY, JSON.stringify(pins))
  }, [pins])

  useEffect(() => {
    fetchMetadata().then(setMeta).catch(() => setError(OFFLINE))
    fetchFreshness().then(setFreshness).catch(() => undefined)
  }, [])

  useEffect(() => {
    setSelected('total')
    setCrumbs([])
    setError(null)
    fetchBridge(flavor).then(setBridge).catch(() => setError(OFFLINE))
    fetchNarrative(flavor)
      .then((r) => setNarrative(r.text))
      .catch(() => setNarrative(''))
  }, [flavor])

  useEffect(() => {
    if (!meta) return
    const level = meta.drillPath[crumbs.length]?.level
    if (!level) return
    const path = Object.fromEntries(crumbs.map((c) => [c.level, c.name]))
    setDrillLoading(true)
    fetchDrill(flavor, level, path)
      .then(setDrill)
      .catch(() => setDrill(null))
      .finally(() => setDrillLoading(false))
  }, [meta, flavor, crumbs])

  const metric = useMemo(() => {
    if (selected === 'total' || !bridge) return { key: 'total', label: 'Total change' }
    const bucket = bridge.buckets.find((b) => b.key === selected)
    return bucket ? { key: bucket.key, label: bucket.label } : { key: 'total', label: 'Total change' }
  }, [selected, bridge])

  const descriptions = useMemo(() => {
    if (!bridge) return {}
    const map: Record<string, string> = { total: bridge.total.description }
    for (const b of bridge.buckets) map[b.key] = b.description
    return map
  }, [bridge])

  const addPin = (chart: ChartSpec, createdFrom: PinnedCard['createdFrom']) => {
    setPins((p) => [
      ...p,
      { id: `${Date.now()}-${p.length}`, title: chart.title, chart, createdFrom },
    ])
  }

  const pinDrill = () => {
    if (!drill || drill.rows.length === 0) return
    const where = crumbs.length ? ` — ${crumbs.map((c) => c.name).join(' › ')}` : ''
    addPin(
      {
        chartType: 'bar',
        title: `${metric.label} (${flavor.toUpperCase()}) by ${drill.label}${where}`,
        data: drill.rows.map((r) => ({
          name: r.name,
          value: metric.key === 'total' ? r.total : (r.values[metric.key] ?? 0),
        })),
      },
      'drill',
    )
  }

  const total = bridge?.total.value ?? 0

  return (
    <div className="page">
      <header className="topbar">
        <div className="brand">
          GroPro <span>Revenue Bridge</span>
        </div>
        {freshness && (
          <span className="freshness" title={freshness.message}>
            <span className="dot" /> {freshness.period} · demo data
          </span>
        )}
        <div className="toggle" role="tablist" aria-label="Comparison flavor">
          {(['yoy', 'seq'] as Flavor[]).map((f) => (
            <button
              key={f}
              role="tab"
              aria-selected={flavor === f}
              className={flavor === f ? 'active' : ''}
              onClick={() => setFlavor(f)}
              title={f === 'yoy' ? 'Versus the same quarter last year' : 'Versus the prior quarter'}
            >
              {f === 'yoy' ? 'Year over year' : 'Sequential'}
            </button>
          ))}
        </div>
      </header>

      {error && <div className="banner-error">{error}</div>}

      <main className="layout">
        <section className="main-col">
          <div className="card">
            <h2 className="card-title">
              What happened{bridge && ` — ${bridge.period.current} vs ${bridge.period.comparison}`}
            </h2>
            {bridge && (
              <div className={`hero ${total >= 0 ? 'up' : 'down'}`}>{fmtM(total)}</div>
            )}
            <p className="narr-text">{narrative || 'Loading the story…'}</p>
          </div>

          <div className="card">
            <h2 className="card-title">Revenue bridge — click a bar to drill into it</h2>
            {bridge ? (
              <Waterfall
                buckets={bridge.buckets}
                total={bridge.total}
                selectedKey={selected}
                onSelect={setSelected}
                descriptions={descriptions}
              />
            ) : (
              <p className="hint">Loading…</p>
            )}
          </div>

          <div className="card">
            <DrillPanel
              data={drill}
              loading={drillLoading}
              crumbs={crumbs}
              rootLabel={meta?.drillPath[0]?.label ?? 'Business unit'}
              metric={metric}
              onCrumbClick={(i) => setCrumbs((c) => c.slice(0, i + 1))}
              onDescend={(name) => {
                if (drill?.nextLevel) setCrumbs((c) => [...c, { level: drill.level, name }])
              }}
              onPin={pinDrill}
            />
          </div>

          <MyView cards={pins} onRemove={(id) => setPins((p) => p.filter((c) => c.id !== id))} />
        </section>

        <aside className="chat-col">
          <ChatPanel onPin={(chart) => addPin(chart, 'chat')} />
        </aside>
      </main>

      <footer className="foot">
        Demo build — every number is served from stub fixtures through the mock Power BI client.
        Live DAX queries (Phase 1) and real AI chat (Phase 3) plug into the same endpoints.
      </footer>
    </div>
  )
}
