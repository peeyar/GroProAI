/** Pure layout for the bridge waterfall: cumulative running positions. */

export interface WaterfallInput {
  key: string
  label: string
  value: number
}

export interface WaterfallBar extends WaterfallInput {
  start: number
  end: number
  kind: 'pos' | 'neg' | 'total'
}

export function layoutWaterfall(buckets: WaterfallInput[], total: WaterfallInput): WaterfallBar[] {
  let cumulative = 0
  const bars: WaterfallBar[] = buckets.map((b) => {
    const start = cumulative
    cumulative += b.value
    return { ...b, start, end: cumulative, kind: b.value >= 0 ? 'pos' : 'neg' }
  })
  bars.push({ ...total, start: 0, end: total.value, kind: 'total' })
  return bars
}

export function extent(bars: WaterfallBar[]): [number, number] {
  const values = bars.flatMap((b) => [b.start, b.end])
  return [Math.min(0, ...values), Math.max(0, ...values)]
}
