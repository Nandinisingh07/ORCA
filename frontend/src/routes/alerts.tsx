import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { Bell, CloudLightning, RefreshCw, Waves } from 'lucide-react'
import { Button, Notice, PageIntro, SectionHead, StatusPill } from '../components/OrcaUI'
import coast from '../assets/orca-coastline.jpg'
import { api } from '../lib/api'

export const Route = createFileRoute('/alerts')({
  head: () => ({
    meta: [
      { title: 'Safety Alerts — ORCA' },
      {
        name: 'description',
        content: 'Live ORCA marine and weather alert intelligence for India’s coasts.',
      },
    ],
  }),
  component: Alerts,
})

const regions = ['All coasts', 'West coast', 'East coast']
const filters = ['All', 'Weather', 'Sea']

function toneFor(level: string): 'teal' | 'amber' | 'red' {
  if (level === 'unsafe' || level === 'critical') return 'red'
  if (level === 'safe' || level === 'low') return 'teal'
  return 'amber'
}

function formatTime(value?: string | null) {
  if (!value) return '—'
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString()
}

function Alerts() {
  const [region, setRegion] = useState('All coasts')
  const [filter, setFilter] = useState('All')
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const result = await api.alerts(region, filter)
      setData(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load alerts.')
      setData(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [region, filter])

  const alerts = data?.alerts ?? []

  return (
    <>
      <PageIntro
        eyebrow="COASTAL SAFETY"
        title="Safety alerts"
        description="Current ORCA risk signals across selected coastal regions, with the evidence, time window and data mode attached."
        image={coast}
      />

      <div className="container page-content">
        <Notice>
          ORCA alert results are generated from the configured forecast/rule-engine pipeline.
          Always verify urgent decisions with official IMD and INCOIS advisories.
        </Notice>

        <div className="content-grid" style={{ marginTop: 22 }}>
          <div className="stack">
            <div className="content-panel">
              <div className="panel-head">
                <div>
                  <h2>Alert centre</h2>
                  <p className="panel-desc" style={{ margin: 0 }}>
                    {loading ? 'Refreshing forecast signals…' : `${alerts.length} alert item(s) returned`}
                  </p>
                </div>

                <Button variant="outline" onClick={() => void load()} disabled={loading}>
                  <RefreshCw size={15} />
                  Refresh
                </Button>
              </div>

              <div className="field-row" style={{ marginTop: 18 }}>
                <div>
                  <label className="field-label" htmlFor="alerts-region">
                    Coastal region
                  </label>
                  <select
                    className="select"
                    id="alerts-region"
                    value={region}
                    onChange={(e) => setRegion(e.target.value)}
                  >
                    {regions.map((value) => (
                      <option key={value}>{value}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <span className="field-label">Alert type</span>
                  <div className="tab-row" style={{ marginBottom: 0 }}>
                    {filters.map((value) => (
                      <Button
                        key={value}
                        variant={filter === value ? 'primary' : 'outline'}
                        onClick={() => setFilter(value)}
                      >
                        {value}
                      </Button>
                    ))}
                  </div>
                </div>
              </div>

              {error && (
                <Notice>
                  Unable to load live alerts: {error}
                </Notice>
              )}

              {!error && !loading && alerts.length === 0 && (
                <div className="inline-success" style={{ marginTop: 18 }}>
                  No alert records matched the selected filters.
                </div>
              )}

              <div style={{ marginTop: 20 }}>
                {alerts.map((item: any) => (
                  <div className="list-card" key={item.id}>
                    <div className="list-meta">
                      <div>
                        <h3>{item.title}</h3>
                        <small>
                          {item.area} · {item.region ?? 'all'}
                        </small>
                      </div>
                      <StatusPill tone={toneFor(item.severity)}>
                        {item.is_sample ? 'Sample' : item.severity}
                      </StatusPill>
                    </div>

                    <p>{item.detail}</p>

                    <p className="source-line">
                      Valid from {formatTime(item.valid_from)} · peak {formatTime(item.peak_at)}
                      {' · '}
                      {item.source}
                      {' · '}
                      {item.data_mode}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="stack">
            <div className="content-panel">
              <h2>What this feed tells you</h2>

              <div className="list-card">
                <h3><Waves size={16} /> Marine conditions</h3>
                <p>Wave-related breaches are surfaced from the ORCA rule engine.</p>
              </div>

              <div className="list-card">
                <h3><CloudLightning size={16} /> Weather signals</h3>
                <p>Wind, gust and thunderstorm signals are included where forecast data supports them.</p>
              </div>

              <div className="list-card">
                <h3><Bell size={16} /> Source context</h3>
                <p>Every returned item carries source and data-mode information so cached/demo records are distinguishable.</p>
              </div>
            </div>

            <div className="callout">
              <strong>Important</strong>
              <p>
                A sample IMD-style alert can appear in the feed, but it is explicitly labelled as sample data and is not an active warning.
              </p>
            </div>
          </div>
        </div>

        <div style={{ marginTop: 34 }}>
          <SectionHead
            eyebrow="SAFETY BY DESIGN"
            title="Signals with context"
            description="ORCA keeps severity, location, timing, source and data mode together instead of presenting an unexplained warning."
          />
        </div>
      </div>
    </>
  )
}
