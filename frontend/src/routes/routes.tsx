import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'
import { Compass, Map, RefreshCw, ShieldCheck } from 'lucide-react'
import { Button, MiniMap, Notice, PageIntro, SectionHead, StatusPill } from '../components/OrcaUI'
import coast from '../assets/orca-coastline.jpg'
import { api } from '../lib/api'

export const Route = createFileRoute('/routes')({
  head: () => ({
    meta: [
      { title: 'Route Planning — ORCA' },
      {
        name: 'description',
        content: 'Assess a marine route using ORCA forecast and boundary checks.',
      },
    ],
  }),
  component: Routes,
})

const places = [
  'Veraval, Gujarat',
  'Mumbai, Maharashtra',
  'Panaji, Goa',
]

function toneFor(level?: string): 'teal' | 'amber' | 'red' {
  if (level === 'unsafe') return 'red'
  if (level === 'safe') return 'teal'
  return 'amber'
}

function Routes() {
  const [origin, setOrigin] = useState(places[0])
  const [distance, setDistance] = useState('20')
  const [day, setDay] = useState<'today' | 'tomorrow' | 'day_after'>('today')
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const planRoute = async () => {
    const distanceKm = Number(distance)

    if (!Number.isFinite(distanceKm) || distanceKm < 1 || distanceKm > 200) {
      setError('Distance must be between 1 and 200 km.')
      return
    }

    setLoading(true)
    setError('')

    try {
      setData(await api.route({
        origin,
        distance_km: distanceKm,
        day,
      }))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Route assessment failed.')
      setData(null)
    } finally {
      setLoading(false)
    }
  }

  const route = data?.route

  return (
    <>
      <PageIntro
        eyebrow="SAFER JOURNEYS AT SEA"
        title="Route planning"
        description="Run an ORCA route assessment that samples conditions along the journey and checks nearby configured boundary features."
        image={coast}
      />

      <div className="container page-content">
        <Notice>
          This is decision-support prototype output, not a navigable route.
          Never use it as a substitute for approved nautical charts or navigation equipment.
        </Notice>

        <div className="content-grid" style={{ marginTop: 22 }}>
          <div className="stack">
            <div className="content-panel">
              <div className="panel-head">
                <div>
                  <h2>Set your journey</h2>
                  <p className="panel-desc" style={{ margin: 0 }}>
                    The backend evaluates multiple sampled points across the requested distance.
                  </p>
                </div>

                {route && (
                  <StatusPill tone={toneFor(route.overall_level)}>
                    {route.overall_level}
                  </StatusPill>
                )}
              </div>

              <div className="field-row">
                <div>
                  <label className="field-label" htmlFor="route-origin">
                    Departure point
                  </label>
                  <select
                    id="route-origin"
                    className="select"
                    value={origin}
                    onChange={(e) => {
                      setOrigin(e.target.value)
                      setData(null)
                    }}
                  >
                    {places.map((value) => (
                      <option key={value}>{value}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="field-label" htmlFor="route-distance">
                    Distance offshore (km)
                  </label>
                  <input
                    id="route-distance"
                    className="field"
                    type="number"
                    min="1"
                    max="200"
                    value={distance}
                    onChange={(e) => {
                      setDistance(e.target.value)
                      setData(null)
                    }}
                  />
                </div>

                <div>
                  <label className="field-label" htmlFor="route-day">
                    Forecast day
                  </label>
                  <select
                    id="route-day"
                    className="select"
                    value={day}
                    onChange={(e) => {
                      setDay(e.target.value as typeof day)
                      setData(null)
                    }}
                  >
                    <option value="today">Today</option>
                    <option value="tomorrow">Tomorrow</option>
                    <option value="day_after">Day after</option>
                  </select>
                </div>
              </div>

              <div style={{ marginTop: 17 }}>
                <Button onClick={() => void planRoute()} disabled={loading}>
                  {loading ? <RefreshCw size={16} /> : <Compass size={16} />}
                  {loading ? 'Assessing…' : 'Assess route'}
                </Button>
              </div>

              {error && (
                <Notice>
                  Unable to assess the route: {error}
                </Notice>
              )}

              {route && (
                <>
                  <div className="data-grid" style={{ marginTop: 22 }}>
                    <div className="data-card">
                      <small>Overall result</small>
                      <strong>{route.overall_level}</strong>
                      <span>{route.compass} · {route.bearing_deg}°</span>
                    </div>

                    <div className="data-card">
                      <small>Peak wave</small>
                      <strong>{route.wave_m_max ?? '—'} m</strong>
                      <span>Across sampled points</span>
                    </div>

                    <div className="data-card">
                      <small>Peak wind</small>
                      <strong>{route.wind_kn_max ?? '—'} kn</strong>
                      <span>Across sampled points</span>
                    </div>
                  </div>

                  <p className="source-line">
                    Data mode: {data.data_mode} · confidence: {data.confidence?.level ?? '—'}
                    {route.recommended_bearing != null
                      ? ` · recommended bearing ${route.recommended_bearing}°`
                      : ''}
                  </p>
                </>
              )}
            </div>

            <div className="content-panel">
              <h2>Journey checkpoints</h2>

              {!route && (
                <p className="panel-desc">
                  Run an assessment to inspect the departure, midpoint and furthest-point checks.
                </p>
              )}

              {route?.samples?.map((sample: any) => (
                <div className="list-card" key={sample.name}>
                  <div className="list-meta">
                    <h3>{sample.name}</h3>
                    <StatusPill tone={toneFor(sample.outbound?.level)}>
                      Outbound {sample.outbound?.level}
                    </StatusPill>
                  </div>

                  <p>
                    Outbound: {sample.outbound?.wave_m_max ?? '—'} m waves ·{' '}
                    {sample.outbound?.wind_kn_max ?? '—'} kn wind
                  </p>

                  <p>
                    Return: {sample.return?.wave_m_max ?? '—'} m waves ·{' '}
                    {sample.return?.wind_kn_max ?? '—'} kn wind
                  </p>

                  <p className="source-line">
                    {sample.lat}, {sample.lon} · {sample.data_mode}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="stack">
            <div className="content-panel">
              <h2>Journey overview</h2>
              <MiniMap variant="route" />

              {route && (
                <p className="source-line">
                  Boundary result: {route.boundary?.level ?? '—'} ·
                  samples: {route.samples?.length ?? 0}
                </p>
              )}
            </div>

            <div className="content-panel">
              <h2>Route checks</h2>

              <div className="list-card">
                <div className="list-meta">
                  <h3>Conditions along the way</h3>
                  <StatusPill tone={toneFor(route?.conditions_level)}>
                    {route?.conditions_level ?? 'Pending'}
                  </StatusPill>
                </div>
                <p>Wave and wind forecasts are evaluated at multiple route checkpoints.</p>
              </div>

              <div className="list-card">
                <div className="list-meta">
                  <h3>Boundary proximity</h3>
                  <StatusPill tone={toneFor(route?.boundary?.level)}>
                    {route?.boundary?.level ?? 'Pending'}
                  </StatusPill>
                </div>
                <p>The configured boundary layer is checked across the interpolated route line.</p>
              </div>

              <div className="list-card">
                <div className="list-meta">
                  <h3>Return conditions</h3>
                  <StatusPill tone="amber">Checked</StatusPill>
                </div>
                <p>The outbound and return time windows are assessed separately.</p>
              </div>
            </div>

            {route && (
              <div className="callout">
                <strong><ShieldCheck size={16} /> Backend method note</strong>
                <p>{route.method_note}</p>
              </div>
            )}
          </div>
        </div>

        <div style={{ marginTop: 34 }}>
          <SectionHead
            eyebrow="THINK BEYOND THE STARTING POINT"
            title="A route assessment, not a static illustration"
            description="ORCA returns condition levels, boundary context, checkpoints and data mode from the backend rather than only drawing a sample route."
          />

          <div className="below-grid">
            <div className="detail-tile">
              <Compass size={22} />
              <h3>Multiple checkpoints</h3>
              <p>Conditions are sampled at the departure area, midpoint and furthest point.</p>
            </div>

            <div className="detail-tile">
              <Map size={22} />
              <h3>Geographic awareness</h3>
              <p>The route is checked against the configured boundary geometry.</p>
            </div>

            <div className="detail-tile">
              <ShieldCheck size={22} />
              <h3>Explainable output</h3>
              <p>The response carries levels, metrics, data mode and the assessment method.</p>
            </div>
          </div>
        </div>

        {data?.disclaimer && (
          <p className="source-line" style={{ marginTop: 24 }}>
            {data.disclaimer}
          </p>
        )}
      </div>
    </>
  )
}
