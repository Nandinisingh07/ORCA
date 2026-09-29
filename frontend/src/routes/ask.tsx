import { createFileRoute } from '@tanstack/react-router'
import { useState, type FormEvent } from 'react'
import { ArrowRight, Info, MessageCircle, Send, ShieldCheck, Waves } from 'lucide-react'
import { Button, PageIntro, SectionHead, MiniMap, Notice, StatusPill } from '../components/OrcaUI'
import coast from '../assets/orca-coastline.jpg'
export const Route = createFileRoute('/ask')({ head: () => ({ meta: [{ title:'Ask ORCA — Coastal Questions & Answers' },{ name:'description',content:'Explore an illustrative ORCA conversation with clear coastal information, maps and source context.' },{ property:'og:title',content:'Ask ORCA — Coastal Questions & Answers' },{ property:'og:description',content:'Ask a coastal question and see a clear, evidence-led response.' },{ property:'og:type',content:'website' },{ name:'twitter:card',content:'summary_large_image' }] }), component: AskPage })
const prompts = ['Is it safe to go to sea tomorrow?', 'What are conditions near Veraval?', 'How can I check fishing zones?']
const API_BASE: string = (import.meta as any).env?.VITE_API_URL ?? 'http://localhost:8000'
type Level = 'safe' | 'caution' | 'unsafe' | 'unknown'
type DataMode = 'live' | 'cached' | 'mock'
interface ChatResponse {
  session_id: string
  place: { key: string; name: string; assumed: boolean }
  verdict: { level: Level; label: string; reasons: any[] }
  answer: string
  evidence: { label: string; value: number | string; unit: string | null; at: string | null; source: string; data_mode: DataMode; fetched_at: string | null }[]
  confidence: { level: string; note: string }
  data_mode: DataMode
  map: { center: [number, number] }
  trace: { agent: string; ms: number }[]
  total_ms: number
}
const api = {
  chat: async (b: Record<string, unknown>): Promise<ChatResponse> => {
    const r = await fetch(`${API_BASE}/api/chat`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) })
    if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`)
    return r.json()
  },
}
const fmtTime = (iso?: string | null) => { if (!iso) return ''; const d = new Date(iso); return isNaN(d.getTime()) ? iso : d.toLocaleString([], { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) }
function DataModeBadge({ mode }: { mode?: DataMode }) {
  if (!mode) return null
  if (mode === 'live') return <StatusPill tone="teal">Live forecast</StatusPill>
  if (mode === 'cached') return <StatusPill tone="amber">Saved forecast (live source unreachable)</StatusPill>
  return <StatusPill tone="amber">Demo sample data, not a forecast</StatusPill>
}
function LevelBadge({ level, label }: { level?: Level; label?: string }) {
  if (!level) return null
  return <StatusPill tone={level === 'safe' ? 'teal' : level === 'unsafe' ? 'red' : 'amber'}>{label ?? level}</StatusPill>
}
const places = ['Veraval, Gujarat', 'Mumbai, Maharashtra', 'Panaji, Goa', 'Kochi, Kerala', 'Chennai, Tamil Nadu', 'Visakhapatnam, Andhra Pradesh']
type Turn = { q: string; res?: ChatResponse; err?: string }
function AskPage() {
  const [question, setQuestion] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const [busy, setBusy] = useState(false)
  const [sid, setSid] = useState<string>()
  const [mode, setMode] = useState<'simple' | 'technical'>('simple')
  const [language, setLanguage] = useState('English')
  const [place, setPlace] = useState<string>(places[0] ?? '')
  const last = [...turns].reverse().find(t => t.res)?.res
  const patchLast = (p: Partial<Turn>) => setTurns(t => t.map((x, i) => (i === t.length - 1 ? { ...x, ...p } : x)))
  const submit = async (e?: FormEvent) => {
    e?.preventDefault()
    const q = question.trim()
    if (!q || busy) return
    setQuestion(''); setBusy(true); setTurns(t => [...t, { q }])
    try {
      const res = await api.chat({ message: q, session_id: sid, language, mode, place })
      setSid(res.session_id); patchLast({ res })
    } catch (err) {
      patchLast({ err: 'Could not reach the ORCA backend. Check that it is running and VITE_API_URL is correct. ' + (err instanceof Error ? err.message : '') })
    } finally { setBusy(false) }
  }
  return <><PageIntro eyebrow="CONVERSATIONAL OCEAN GUIDANCE" title="Ask ORCA" description="Ask in everyday language. ORCA plans the question, gathers marine and weather data, applies safety rules and shows the evidence behind its answer." image={coast}/>
    <div className="container page-content">
      <Notice>Demo prototype. Every answer shows whether its data is live, saved or a demo sample. Safety thresholds are demo values. Always verify with official INCOIS and IMD advisories before going to sea.</Notice>
      <div className="content-grid" style={{ marginTop: 22 }}>
        <div className="stack">
          <div className="content-panel">
            <div className="panel-head"><div><h2>Your conversation</h2><p className="panel-desc" style={{ margin: 0 }}>Follow-up questions keep their context ("what about the day after?").</p></div><MessageCircle size={22} color="var(--primary)"/></div>
            <div className="conversation">
              {turns.length === 0 ? <div className="empty-chat"><Waves size={30}/><strong>What would you like to know?</strong>Choose a question below or write your own.</div> : turns.map((t, index) => <div key={index} className="stack">
                <div className="chat-bubble chat-question">{t.q}</div>
                <div className="chat-bubble chat-answer">
                  {t.err ? <p style={{ margin: 0 }}>{t.err}</p> : !t.res ? <p style={{ margin: 0 }}>ORCA agents are working on it…</p> : <>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}><LevelBadge level={t.res.verdict.level} label={t.res.verdict.label}/><DataModeBadge mode={t.res.data_mode}/></div>
                    <p style={{ margin: '8px 0' }}>{t.res.answer}</p>
                    {t.res.evidence.length > 0 && <details style={{ marginTop: 8 }}><summary style={{ cursor: 'pointer', fontWeight: 600 }}>Evidence ({t.res.evidence.length})</summary>
                      <ul style={{ margin: '8px 0 0', paddingLeft: 18 }}>{t.res.evidence.map((ev, i) => <li key={i} style={{ marginBottom: 6 }}><strong>{ev.label}:</strong> {String(ev.value)}{ev.unit ? ' ' + ev.unit : ''}{ev.at ? ' · ' + fmtTime(ev.at) : ''}<br/><span className="source-line">{ev.source} · {ev.data_mode}{ev.fetched_at ? ' · fetched ' + fmtTime(ev.fetched_at) : ''}</span></li>)}</ul></details>}
                    {t.res.verdict.reasons.length > 0 && <details style={{ marginTop: 6 }}><summary style={{ cursor: 'pointer', fontWeight: 600 }}>Why this verdict</summary>
                      <ul style={{ margin: '8px 0 0', paddingLeft: 18 }}>{t.res.verdict.reasons.map((r: any, i: number) => <li key={i}>{r.metric.replace('_', ' ')} peaked at {r.value} {r.unit} ({r.level}; caution above {r.caution_above ?? '-'}, unsafe above {r.unsafe_above ?? '-'})</li>)}</ul></details>}
                    <span className="source-line">Confidence: {t.res.confidence.level}. {t.res.confidence.note} Agents: {t.res.trace.map(a => a.agent).join(' → ')} · {t.res.total_ms} ms</span>
                  </>}
                </div>
              </div>)}
            </div>
            <form onSubmit={submit} className="chat-composer"><input className="field" aria-label="Your coastal question" placeholder="Ask a question about the sea..." value={question} onChange={e => setQuestion(e.target.value)}/><Button type="submit" aria-label="Send question" disabled={busy}><Send size={16}/></Button></form>
            <div className="chips" style={{ marginTop: 12 }}>{prompts.map(p => <button className="chip" key={p} onClick={() => setQuestion(p)}>{p}</button>)}</div>
          </div>
          <div className="content-panel"><h2>Location context</h2><p className="panel-desc">Position used for the latest answer.</p><MiniMap/>
            <p className="source-line">{last ? `${last.place.name}${last.place.assumed ? ' (assumed, no place given)' : ''} · forecast point ${last.map.center[0].toFixed(2)}, ${last.map.center[1].toFixed(2)}` : 'Schematic view. Ask a question to see the location used.'} · Not for navigation.</p></div>
        </div>
        <div className="stack">
          <div className="content-panel"><h2>Make it yours</h2><p className="panel-desc">Choose location, language and level of detail.</p>
            <div className="field-row">
              <div><label className="field-label" htmlFor="ask-place">Location</label><select id="ask-place" className="select" value={place} onChange={e => setPlace(e.target.value)}>{places.map(p => <option key={p}>{p}</option>)}</select></div>
              <div><label className="field-label" htmlFor="ask-language">Response language</label><select id="ask-language" className="select" value={language} onChange={e => setLanguage(e.target.value)}><option>English</option><option>हिन्दी (Hindi)</option><option>ગુજરાતી (Gujarati)</option><option>தமிழ் (Tamil)</option></select></div>
              <div><span className="field-label">Level of detail</span><div className="tab-row" style={{ marginBottom: 0 }}><Button variant={mode === 'simple' ? 'primary' : 'outline'} onClick={() => setMode('simple')}>Plain language</Button><Button variant={mode === 'technical' ? 'primary' : 'outline'} onClick={() => setMode('technical')}>Technical</Button></div></div>
            </div>
            <p className="source-line">If you write in Hindi, Gujarati or Tamil, ORCA answers in that language. Answers use fixed templates, not a full translation service, and should be reviewed by native speakers.</p></div>
          <div className="callout"><strong>How ORCA answers</strong><p>A planner routes your question to weather, ocean, geospatial and boundary agents. A rule engine (not a language model) produces the Safe / Caution / Unsafe verdict, and every number is shown with its source and time.</p></div>
          <div className="content-panel"><h2>What an answer shows</h2><div className="list-card"><h3><ShieldCheck size={16}/> A clear safety conclusion</h3><p>With the thresholds and uncertainty explained, never a guess.</p></div><div className="list-card"><h3><Info size={16}/> Evidence you can inspect</h3><p>Numbers, source, location, time and whether the data was live.</p></div><div className="list-card"><h3><ArrowRight size={16}/> A useful next step</h3><p>Where to confirm with official advisories before deciding.</p></div></div>
        </div>
      </div>
      <div style={{ marginTop: 34 }}><SectionHead eyebrow="BUILT FOR TRUST" title="Answers with context, not just conclusions" description="Conversation combined with visible evidence and meaningful uncertainty."/></div>
    </div></>
}
