import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { CloudSun, Clock3, Waves } from 'lucide-react'
import {
  Button,
  MiniMap,
  Notice,
  PageIntro,
  SectionHead,
  StatusPill,
} from '../components/OrcaUI'
import coast from '../assets/orca-coastline.jpg'
import { api } from '../lib/api'

export const Route = createFileRoute('/conditions')({
  head: () => ({
    meta: [
      { title: 'Ocean Conditions — ORCA' },
      {
        name: 'description',
        content:
          'Explore marine conditions, wave and wind information, location maps and forecast context in the ORCA concept.',
      },
    ],
  }),
  component: ConditionsPage,
})

const places = [
  'Veraval, Gujarat',
  'Mumbai, Maharashtra',
  'Panaji, Goa',
  'Kochi, Kerala',
]

function ConditionsPage() {
  const [place, setPlace] = useState(places[0])
  const [period, setPeriod] = useState('Today')
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const day = period === 'Today' ? 'today' : 'tomorrow'

  useEffect(() => {
    let cancelled = false

    setLoading(true)
    setError('')

    api.conditions(place ?? '', day)
      .then((result) => {
        if (!cancelled) {
          setData(result)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err?.message || 'Unable to load marine conditions.')
          setData(null)
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [place, day])

  const summary = data?.summary
  const periods = data?.periods ?? []

  return (
    <>
      <PageIntro
        eyebrow="MARINE OBSERVATIONS & FORECASTS"
        title="Ocean conditions"
        description="A place to read the sea at a glance — with marine conditions, coastal context and the evidence behind every forecast."
        image={coast}
      />

      <div className="container page-content">
        {loading && (
          <Notice>
            Loading live marine conditions for {place}...
          </Notice>
        )}

        {error && (
          <Notice>
            Unable to load live data: {error}
          </Notice>
        )}

        {!loading && !error && data && (
          <Notice>
            Live forecast connected · {data.sources?.marine?.name} ·
            Updated {new Date(data.sources?.marine?.fetched_at).toLocaleString()}
          </Notice>
        )}

        <div className="content-grid" style={{ marginTop: 22 }}>
          <div className="stack">
            <div className="content-panel">
              <div className="panel-head">
                <h2>Coastal overview</h2>
                <StatusPill tone={summary?.level === 'safe' ? 'teal' : 'amber'}>
                  {summary?.label ?? 'Loading'}
                </StatusPill>
              </div>

              <div className="field-row">
                <div>
                  <label
                    className="field-label"
                    htmlFor="conditions-place"
                  >
                    Coastal location
                  </label>

                  <select
                    id="conditions-place"
                    className="select"
                    value={place}
                    onChange={(e) => setPlace(e.target.value)}
                  >
                    {places.map((p) => (
                      <option key={p}>{p}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <span className="field-label">Forecast period</span>

                  <div className="tab-row" style={{ marginBottom: 0 }}>
                    {['Today', 'Tomorrow'].map((p) => (
                      <Button
                        key={p}
                        variant={period === p ? 'primary' : 'outline'}
                        onClick={() => setPeriod(p)}
                      >
                        {p}
                      </Button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="data-grid" style={{ marginTop: 22 }}>
                <div className="data-card">
                  <small>Significant wave height</small>
                  <strong>
                    {summary?.wave_m_max != null
                      ? `${summary.wave_m_max.toFixed(2)} m`
                      : '—'}
                  </strong>
                  <span>
                    Max wave · Swell {summary?.swell_m_max ?? '—'} m
                  </span>
                </div>

                <div className="data-card">
                  <small>Surface wind</small>
                  <strong>
                    {summary?.wind_kn_max != null
                      ? `${summary.wind_kn_max.toFixed(1)} kn`
                      : '—'}
                  </strong>
                  <span>
                    Gusts up to {summary?.gust_kn_max ?? '—'} kn
                  </span>
                </div>

                <div className="data-card">
                  <small>Sea temperature</small>
                  <strong>
                    {summary?.sst_c_mean != null
                      ? `${summary.sst_c_mean.toFixed(1)}°C`
                      : '—'}
                  </strong>
                  <span>
                    Precipitation {summary?.precip_pct_max ?? '—'}%
                  </span>
                </div>
              </div>

              <p className="source-line">
                Selected: {place} · {period} · Data mode:{' '}
                {data?.data_mode ?? '—'} · Confidence:{' '}
                {data?.confidence?.level ?? '—'}
              </p>
            </div>

            <div className="content-panel">
              <h2>Conditions through the day</h2>

              <p className="panel-desc">
                Compare wave and wind conditions across the day before
                planning a trip.
              </p>

              <div style={{ overflowX: 'auto' }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Period</th>
                      <th>Waves</th>
                      <th>Wind</th>
                      <th>Assessment</th>
                    </tr>
                  </thead>

                  <tbody>
                    {periods.map((row: any) => (
                      <tr key={row.period}>
                        <td>{row.period}</td>
                        <td>
                          {row.wave_m_max != null
                            ? `${row.wave_m_max.toFixed(2)} m`
                            : '—'}
                        </td>
                        <td>
                          {row.wind_kn_max != null
                            ? `${row.wind_kn_max.toFixed(1)} kn`
                            : '—'}
                        </td>
                        <td>{row.label ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div className="stack">
            <div className="content-panel">
              <h2>Location on the coast</h2>

              <p className="panel-desc">
                Approximate forecast sampling point for the selected
                coastal area.
              </p>

              <MiniMap />

              <p className="source-line">
                Forecast point:{' '}
                {data?.forecast_point
                  ? `${data.forecast_point.lat}, ${data.forecast_point.lon}`
                  : '—'}
              </p>
            </div>

            <div className="content-panel">
              <h2>What to look for</h2>

              <div className="list-card">
                <h3>Wave height & swell</h3>
                <p>
                  High or rapidly rising seas can change operating
                  conditions quickly.
                </p>
              </div>

              <div className="list-card">
                <h3>Wind speed & direction</h3>
                <p>
                  Consider both the outward journey and the conditions
                  expected on return.
                </p>
              </div>

              <div className="list-card">
                <h3>Official warnings</h3>
                <p>
                  Always verify conditions with official INCOIS/IMD
                  advisories before going to sea.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div style={{ marginTop: 34 }}>
          <SectionHead
            eyebrow="HOW TO READ THE FORECAST"
            title="A complete picture of the sea"
            description="Marine decisions need several signals together, with a clear time and location attached to each one."
          />

          <div className="below-grid">
            <div className="detail-tile">
              <Waves size={22} />
              <h3>Sea state</h3>
              <p>
                Wave height, period and swell help explain how the
                surface may feel offshore.
              </p>
            </div>

            <div className="detail-tile">
              <CloudSun size={22} />
              <h3>Weather context</h3>
              <p>
                Wind and changing weather should be interpreted
                alongside marine conditions.
              </p>
            </div>

            <div className="detail-tile">
              <Clock3 size={22} />
              <h3>Timing matters</h3>
              <p>
                Conditions can vary within the day. Always check the
                latest issue time.
              </p>
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
