/** "$ in millions" display formatting. Numbers are only ever formatted here —
 * never computed: every value comes from the backend's guarded query path. */
export function fmtM(value: number, { signed = true }: { signed?: boolean } = {}): string {
  const sign = value > 0 ? (signed ? '+' : '') : value < 0 ? '-' : ''
  return `${sign}$${(Math.abs(value) / 1e6).toFixed(1)}M`
}
