export type Flavor = 'yoy' | 'seq'

export interface BridgeBucket {
  key: string
  label: string
  value: number
  description: string
}

export interface BridgeResponse {
  flavor: Flavor
  period: { current: string; comparison: string }
  buckets: BridgeBucket[]
  total: BridgeBucket
}

export interface DrillRow {
  name: string
  values: Record<string, number>
  total: number
}

export interface DrillResponse {
  level: string
  label: string
  nextLevel: string | null
  rows: DrillRow[]
  note: string | null
}

export interface NarrativeResponse {
  flavor: Flavor
  text: string
  demo: boolean
}

export interface ChartSpec {
  chartType: 'bar' | 'waterfall'
  title: string
  data: { name: string; value: number }[]
  total?: number
}

export interface ChatResponse {
  reply: string
  chart: ChartSpec | null
  demo: boolean
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  text: string
  chart?: ChartSpec | null
}

export interface FreshnessResponse {
  period: string
  mode: string
  message: string
}

export interface MetadataResponse {
  model: string
  buckets: { key: string; label: string }[]
  drillPath: { level: string; label: string }[]
  periods: { current: string; priorYear: string; priorQuarter: string }
}

export interface PinnedCard {
  id: string
  title: string
  chart: ChartSpec
  createdFrom: 'chat' | 'drill'
}
