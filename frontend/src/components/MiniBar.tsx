import { fmtM } from '../format'

interface Props {
  data: { name: string; value: number }[]
}

/** Horizontal diverging bar list used in chat answers and pinned cards. */
export default function MiniBar({ data }: Props) {
  const W = 360
  const rowH = 26
  const labelW = 118
  const valueW = 62
  const plotW = W - labelW - valueW - 10
  const H = data.length * rowH + 6

  const values = data.map((d) => d.value)
  const minV = Math.min(0, ...values)
  const maxV = Math.max(0, ...values)
  const span = maxV - minV || 1
  const x = (v: number) => labelW + ((v - minV) / span) * plotW
  const zeroX = x(0)

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="minibar"
      role="img"
      aria-label={data.map((d) => `${d.name} ${fmtM(d.value)}`).join(', ')}
    >
      <line x1={zeroX} x2={zeroX} y1={2} y2={H - 2} stroke="var(--baseline)" strokeWidth={1} />
      {data.map((d, i) => {
        const barX = Math.min(zeroX, x(d.value))
        const barW = Math.max(2, Math.abs(x(d.value) - zeroX))
        const name = d.name.length > 16 ? `${d.name.slice(0, 15)}…` : d.name
        return (
          <g key={d.name}>
            <title>{`${d.name}: ${fmtM(d.value)}`}</title>
            <text x={labelW - 8} y={i * rowH + 17} textAnchor="end" className="mb-name">
              {name}
            </text>
            <rect
              x={barX}
              y={i * rowH + 6}
              width={barW}
              height={14}
              rx={3}
              fill={d.value >= 0 ? 'var(--pos)' : 'var(--neg)'}
            />
            <text x={W - 2} y={i * rowH + 17} textAnchor="end" className="mb-value">
              {fmtM(d.value)}
            </text>
          </g>
        )
      })}
    </svg>
  )
}
