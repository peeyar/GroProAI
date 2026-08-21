import type {
  BridgeResponse,
  ChatResponse,
  DrillResponse,
  Flavor,
  FreshnessResponse,
  MetadataResponse,
  NarrativeResponse,
} from './types'

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`)
  return res.json() as Promise<T>
}

export const fetchMetadata = () => getJson<MetadataResponse>('/api/metadata')

export const fetchFreshness = () => getJson<FreshnessResponse>('/api/freshness')

export const fetchBridge = (flavor: Flavor) =>
  getJson<BridgeResponse>(`/api/bridge?flavor=${flavor}`)

export const fetchNarrative = (flavor: Flavor) =>
  getJson<NarrativeResponse>(`/api/narrative?flavor=${flavor}`)

export const fetchDrill = (flavor: Flavor, level: string, path: Record<string, string>) =>
  getJson<DrillResponse>(
    `/api/drill?flavor=${flavor}&level=${level}&path=${encodeURIComponent(JSON.stringify(path))}`,
  )

export async function sendChat(message: string): Promise<ChatResponse> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  })
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`)
  return res.json() as Promise<ChatResponse>
}
