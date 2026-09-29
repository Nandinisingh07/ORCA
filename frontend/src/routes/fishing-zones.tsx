import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { Fish, Satellite, ShieldCheck } from 'lucide-react'
import { MiniMap, Notice, PageIntro, SectionHead, StatusPill } from '../components/OrcaUI'
import fishing from '../assets/orca-fishing.jpg'
import { api } from '../lib/api'

export const Route = createFileRoute('/fishing-zones')({
  head: () => ({
    meta: [
      { title: 'Fishing Zones — ORCA' },
      { name: 'description', content: 'Explore potential fishing-zone advisories and coastal context with ORCA.' },
      { property: 'og:title', content: 'Fishing Zones — ORCA' },
      { property: 'og:description', content: 'Fishing-zone information with visible sources and coastal context.' },
      { property: 'og:type', content: 'website' },
      { name: 'twitter:card', content: 'summary_large_image' }
    ]
  }),
  component: FishingZones
})

function FishingZones() {
  const [coast, setCoast] = useState('Gujarat coast')
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true

    async function loadZones() {
      setLoading(true)
      setError('')

      try {
        const result = await api.fishingZones(coast)

        if (active) {
          setData(result)
        }
      } catch (err) {
        if (active) {
          setError('Fishing-zone data could not be loaded right now.')
          setData(null)
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    loadZones()

    return () => {
      active = false
    }
  }, [coast])

  const zones = data?.zones ?? []
  const advisory = data?.advisory
  const isSample = data?.advisory?.is_sample ?? true

  return (
    <>
      <PageIntro
        eyebrow="POTENTIAL FISHING ZONES"
        title="Fishing zones"
        description="Explore how satellite observations and official advisories can help make fishing information easier to find and understand."
        image={fishing}
      />

      <div className="container page-content">
        <Notice>
          {loading
            ? 'Loading the latest ORCA fishing-zone information...'
            : isSample
              ? 'ORCA sample PFZ-like data is shown below. It is NOT an INCOIS bulletin or an official fishing recommendation.'
              : 'Fishing-zone information is available. Always verify the original official advisory before departure.'}
        </Notice>

        {error && (
          <div className="callout" style={{ marginTop: 18 }}>
            <strong>Unable to load advisory</strong>
            <p>{error}</p>
          </div>
        )}

        <div className="content-grid" style={{ marginTop: 22 }}>
          <div className="stack">
            <div className="content-panel">
              <div className="panel-head">
                <h2>Explore an advisory area</h2>
                <StatusPill tone={isSample ? 'amber' : 'teal'}>
                  {loading ? 'Loading' : isSample ? 'Sample data' : 'Live'}
                </StatusPill>
              </div>

              <label htmlFor="fish-coast" className="field-label">
                Select coastline
              </label>

              <select
                id="fish-coast"
                className="select"
                value={coast}
                onChange={e => setCoast(e.target.value)}
              >
                <option>Gujarat coast</option>
                <option>Maharashtra coast</option>
                <option>Goa coast</option>
                <option>Kerala coast</option>
              </select>

              <div style={{ marginTop: 18 }}>
                <MiniMap variant="zones" />
              </div>

              {zones.length > 0 ? (
                <div style={{ marginTop: 18 }}>
                  <h3>Potential zones returned by ORCA</h3>

                  {zones.map((zone: any, index: number) => (
                    <div className="list-card" key={zone.id ?? index}>
                      <div className="list-meta">
                        <h3>Candidate {index + 1}</h3>
                        <StatusPill tone="amber">
                          {zone.compass}
                        </StatusPill>
                      </div>

                      <p>
                        Approximately <strong>{zone.distance_km} km</strong> offshore,
                        bearing <strong>{zone.bearing_deg}° ({zone.compass})</strong>.
                      </p>

                      <span className="source-line">
                        Centre: {zone.centre?.lat}, {zone.centre?.lon}{zone.mean_chl_mg_m3 ? ` \u00B7 Chlorophyll ${zone.mean_chl_mg_m3} mg/m\u00B3 \u00B7 SST ${zone.sst_c} \u00B0C` : ''}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                !loading && (
                  <p className="source-line">
                    No fishing zones were returned for this coastline.
                  </p>
                )
              )}

              <p className="source-line">
                {advisory?.source ?? `ORCA advisory information for ${coast}.`}
              </p>
            </div>

            <div className="content-panel">
              <h2>What an official advisory can tell you</h2>
              <p className="panel-desc">
                A Potential Fishing Zone (PFZ) bulletin gives location guidance
                associated with a coastal landing centre. It should be read together
                with marine safety information.
              </p>

              <div style={{ overflowX: 'auto' }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Information</th>
                      <th>Why it matters</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>Satellite data date</td>
                      <td>{data?.eo?.available ? `${data.eo.chl.obs_time.slice(0,10)} (${data.eo.chl.age_days} days old)` : (advisory?.date ?? 'Not available')}</td>
                    </tr>
                    <tr>
                      <td>Landing centre</td>
                      <td>
                        {advisory?.landing_centre
                          ? `${advisory.landing_centre.lat}, ${advisory.landing_centre.lon}`
                          : 'Not available'}
                      </td>
                    </tr>
                    <tr>
                      <td>Location & bearing</td>
                      <td>Distance and direction from the coast</td>
                    </tr>
                    <tr>
                      <td>Marine warning</td>
                      <td>Safety takes priority over fishing potential</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div className="stack">
            <div className="content-panel">
              <h2>Advisory status</h2>

              <div className="list-card">
                <div className="list-meta">
                  <h3>{coast}</h3>
                  <StatusPill tone="amber">
                    {isSample ? 'Sample zones' : 'Satellite-derived (heuristic)'}
                  </StatusPill>
                </div>

                <p>
                  {advisory?.source ??
                    'ORCA would surface the most recent advisory here.'}
                </p>

                {advisory?.official_source && (
                  <a
                    className="text-link"
                    href={advisory.official_source}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Visit official INCOIS source →
                  </a>
                )}
              </div>

              <div className="list-card">
                <h3>Sea-state context</h3>

                <p>
                  Current ORCA sea-state assessment:{' '}
                  <strong>{data?.sea_state?.label ?? 'Unavailable'}</strong>
                </p>

                <span className="source-line">
                  Fishing potential is separate from the marine safety assessment.
                </span>
              </div>
            </div>

            <div className="callout">
              <strong>Fishing potential is not a safety verdict</strong>
              <p>
                An area may be promising for fishing yet unsafe to reach. Always
                check the marine forecast and official warnings separately.
              </p>
            </div>
          </div>
        </div>

        <div style={{ marginTop: 34 }}>
          <SectionHead
            eyebrow="THE SCIENCE BEHIND THE VIEW"
            title="Signals from sea and space"
            description="Potential fishing-zone advisories often use ocean-colour and temperature patterns to identify productive waters."
          />

          <div className="below-grid">
            <div className="detail-tile">
              <Satellite size={22} />
              <h3>Satellite observations</h3>
              <p>
                Remote sensing can reveal changing ocean surface patterns across
                large areas.
              </p>
            </div>

            <div className="detail-tile">
              <Fish size={22} />
              <h3>Productive water</h3>
              <p>
                Indicators such as chlorophyll and sea-surface temperature help
                identify potential zones.
              </p>
            </div>

            <div className="detail-tile">
              <ShieldCheck size={22} />
              <h3>Safety comes first</h3>
              <p>
                Advisory areas must always be considered alongside the latest
                official warnings.
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
