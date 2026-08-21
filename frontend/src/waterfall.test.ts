import { describe, expect, it } from 'vitest'
import { extent, layoutWaterfall } from './waterfall'

const buckets = [
  { key: 'a', label: 'A', value: 10 },
  { key: 'b', label: 'B', value: -4 },
  { key: 'c', label: 'C', value: 6 },
]
const total = { key: 'total', label: 'Total', value: 12 }

describe('layoutWaterfall', () => {
  it('stacks bars cumulatively and appends the total from zero', () => {
    const bars = layoutWaterfall(buckets, total)
    expect(bars.map((b) => [b.start, b.end])).toEqual([
      [0, 10],
      [10, 6],
      [6, 12],
      [0, 12],
    ])
    expect(bars.map((b) => b.kind)).toEqual(['pos', 'neg', 'pos', 'total'])
    expect(bars[2].end).toBe(total.value)
  })

  it('extent always includes zero', () => {
    const bars = layoutWaterfall(
      [{ key: 'x', label: 'X', value: -5 }],
      { key: 'total', label: 'Total', value: -5 },
    )
    expect(extent(bars)).toEqual([-5, 0])
  })
})
