import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { Anchor, MapPin, RefreshCw, ShieldAlert } from 'lucide-react'
import { Button, MiniMap, Notice, PageIntro, SectionHead, StatusPill } from '../components/OrcaUI'
import coast from '../assets/orca-coastline.jpg'
import { api } from '../lib/api'

export const Route = createFileRoute('/boundaries')({
  head: () => ({
    meta: [
      { title: 'Marine Boundaries — ORCA' },
      {
        name: 'description',
        content: 'Explore ORCA boundary layers and proximity-awareness checks.',
      },
    ],
  }),
  component: Boundaries,
})

const layerOptions = [
  { label: 'Reference boundary', value: 'reference' },
  { label: 'Protected area awareness', value: 'protected' },
  { label: 'Coastal reference', value: 'coastal' },
]

function Boundaries() {
  const [layer, setLayer] = useState('reference')
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [lat, setLat] = useState('')
  const [lon, setLon] = useState('')
  const [checking, setChecking] = useState(false)
  const [checkResult, setCheckResult] = useState<any>(null)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      setData(await api.boundaries(layer))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load boundary data.')
      setData(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [layer])

  const checkPosition = async (e: React.FormEvent) => {
    e.preventDefault()

    const la = Number(lat)
    const lo = Number(lon)

    if (!Number.isFinite(la) || !Number.isFinite(lo) || la < -90 || la > 90 || lo < -180 || lo > 180) {
      setCheckResult({ error: 'Enter a valid latitude (-90 to 90) and longitude (-180 to 180).' })
      return
    }

    setChecking(true)
    setCheckResult(null)

    try {
      setCheckResult(await api.boundaryCheck(la, lo))
    } catch (err) {
      setCheckResult({
        error: err instanceof Error ? err.message : 'Boundary check failed.',
      })
    } finally {
      setChecking(false)
    }
  }

  const features = data?.features ?? []

  return (
    <>
      <PageIntro
        eyebrow="GEOGRAPHIC AWARENESS"
        title="Marine boundaries"
        description="Inspect the configured boundary layer and test a coordinate against ORCA’s proximity-awareness endpoint."
        image={coast}
      />

      <div className="container page-content">
        <Notice>
          Boundary geometry is illustrative unless validated GeoJSON has been loaded.
          It is not a legal boundary or navigation chart.
        </Notice>

        <div className="content-grid" style={{ marginTop: 22 }}>
          <div className="stack">
            <div className="content-panel">
              <div className="panel-head">
                <div>
                  <h2>Boundary explorer</h2>
                  <p className="panel-desc" style={{ margin: 0 }}>
                    {loading ? 'Loading layer…' : `${features.length} feature(s) returned`}
                  </p>
                </div>

                <Button variant="outline" onClick={() => void load()} disabled={loading}>
                  <RefreshCw size={15} />
                  Refresh
                </Button>
              </div>

              <label className="field-label" htmlFor="boundary-layer">
                Map layer
              </label>

              <select
                className="select"
                id="boundary-layer"
                value={layer}
                onChange={(e) => setLayer(e.target.value)}
              >
                {layerOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>

              <div style={{ marginTop: 17 }}>
                <MiniMap variant="boundary" />
              </div>

              {error && <Notice>Unable to load boundary layer: {error}</Notice>}

              {!error && data && (
                <p className="source-line">
                  Layer: {data.layer} · illustrative: {String(data.is_illustrative)} · legal validity: {data.legal_validity}
                </p>
              )}

              {features.map((feature: any) => (
                <div className="list-card" key={feature.properties?.id ?? feature.properties?.name}>
                  <div className="list-meta">
                    <h3>{feature.properties?.name ?? 'Unnamed feature'}</h3>
                    <StatusPill tone={feature.properties?.is_illustrative ? 'amber' : 'teal'}>
                      {feature.properties?.is_illustrative ? 'Illustrative' : 'Loaded'}
                    </StatusPill>
                  </div>
                  <p>{feature.properties?.description ?? 'Boundary feature returned by the backend.'}</p>
                </div>
              ))}
            </div>

            <div className="content-panel">
              <h2>Check a position</h2>
              <p className="panel-desc">
                Send a latitude/longitude pair to the ORCA boundary-check endpoint.
              </p>

              <form onSubmit={checkPosition}>
                <div className="field-row">
                  <div>
                    <label className="field-label" htmlFor="boundary-lat">Latitude</label>
                    <input
                      id="boundary-lat"
                      className="field"
                      type="number"
                      step="any"
                      value={lat}
                      onChange={(e) => setLat(e.target.value)}
                      placeholder="e.g. 20.90"
                    />
                  </div>

                  <div>
                    <label className="field-label" htmlFor="boundary-lon">Longitude</label>
                    <input
                      id="boundary-lon"
                      className="field"
                      type="number"
                      step="any"
                      value={lon}
                      onChange={(e) => setLon(e.target.value)}
                      placeholder="e.g. 70.36"
                    />
                  </div>
                </div>

                <div style={{ marginTop: 16 }}>
                  <Button type="submit" disabled={checking}>
                    <MapPin size={15} />
                    {checking ? 'Checking…' : 'Check proximity'}
                  </Button>
                </div>
              </form>

              {checkResult && (
                <div className="callout" style={{ marginTop: 18 }}>
                  {checkResult.error ? (
                    <strong>{checkResult.error}</strong>
                  ) : (
                    <>
                      <strong>
                        Proximity level: {checkResult.level}
                      </strong>
                      <p>
                        Alert radius: {checkResult.alert_within_km} km.
                      </p>

                      {(checkResult.nearest ?? []).slice(0, 3).map((item: any) => (
                        <p className="source-line" key={item.id}>
                          {item.name} · {item.distance_km} km · inside: {String(item.inside)}
                        </p>
                      ))}
                    </>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="stack">
            <div className="content-panel">
              <h2>How proximity awareness works</h2>

              <div className="mini-steps">
                <div className="mini-step">
                  <b>1</b>
                  <div>
                    <strong>Capture a position</strong>
                    Use a reliable, permission-based location source.
                  </div>
                </div>

                <div className="mini-step">
                  <b>2</b>
                  <div>
                    <strong>Compare with the layer</strong>
                    ORCA checks the point against configured geographic features.
                  </div>
                </div>

                <div className="mini-step">
                  <b>3</b>
                  <div>
                    <strong>Explain the result</strong>
                    Show proximity, feature name and the configured alert radius.
                  </div>
                </div>
              </div>
            </div>

            <div className="content-panel">
              <h2>Important boundaries</h2>

              <div className="list-card">
                <h3><ShieldAlert size={16} /> Maritime boundaries</h3>
                <p>Legal definitions must come from authoritative maritime datasets and approved charts.</p>
              </div>

              <div className="list-card">
                <h3><Anchor size={16} /> Protected areas</h3>
                <p>Protected-area restrictions can vary by location, season and activity.</p>
              </div>

              <Notice>
                Backend responses explicitly indicate whether the configured geometry is illustrative.
              </Notice>
            </div>
          </div>
        </div>

        <div style={{ marginTop: 34 }}>
          <SectionHead
            eyebrow="LOCATION WITH RESPONSIBILITY"
            title="Geographic awareness with a clear source"
            description="A proximity signal is only useful when the underlying geometry and legal interpretation are verified."
          />
        </div>
      </div>
    </>
  )
}
