// Shared API client for the ORCA frontend.
const BASE: string = (import.meta as any).env?.VITE_API_URL ?? 'http://localhost:8000'

export type DataMode = 'live' | 'cached' | 'mock'
export type Level = 'safe' | 'caution' | 'unsafe' | 'unknown'
export interface Evidence { label: string; value: number | string; unit: string | null; at: string | null; source: string; data_mode: DataMode; fetched_at: string | null }
export interface ChatResponse {
  session_id: string; language: string; detected_language: string; intent: string
  place: { key: string; name: string; assumed: boolean }; day: number
  verdict: { level: Level; label: string; reasons: any[]; metrics: Record<string, any> }
  answer: string; evidence: Evidence[]; confidence: { level: string; note: string }
  data_mode: DataMode; data_notes: string[]
  map: { center: [number, number]; markers: any[]; zones: number[][][]; boundaries: any | null; route: number[][] | null }
  trace: { agent: string; ms: number }[]; disclaimer: string
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { headers: { 'Content-Type': 'application/json' }, ...init })
  if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`)
  return r.json()
}
const qs = (o: Record<string, string | number | boolean | undefined>) =>
  '?' + new URLSearchParams(Object.entries(o).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)])).toString()

export const api = {
  chat: (b: { message: string; session_id?: string; language?: string; mode?: 'simple' | 'technical'; place?: string; lat?: number; lon?: number; scenario?: 'calm' | 'rough' | 'storm' }) =>
    req<ChatResponse>('/api/chat', { method: 'POST', body: JSON.stringify(b) }),
  conditions: (place: string, day: 'today' | 'tomorrow' | 'day_after' = 'today') => req<any>('/api/conditions' + qs({ place, day })),
  fishingZones: (place: string) => req<any>('/api/fishing-zones' + qs({ place })),               // accepts "Gujarat coast"
  alerts: (region = 'all', type = 'all') => req<any>('/api/alerts' + qs({ region, type })),      // accepts "West coast"
  route: (b: { origin: string; distance_km: number; bearing_deg?: number; day?: string }) => req<any>('/api/route', { method: 'POST', body: JSON.stringify(b) }),
  boundaries: (layer: string) => req<any>('/api/boundaries' + qs({ layer })),                    // accepts "Protected area awareness"
  boundaryCheck: (lat: number, lon: number) => req<any>('/api/boundaries/check', { method: 'POST', body: JSON.stringify({ lat, lon }) }),
  briefing: (place: string, lang = 'en', mode: 'simple' | 'technical' = 'simple') => req<any>('/api/briefing' + qs({ place, lang, mode })),
}
