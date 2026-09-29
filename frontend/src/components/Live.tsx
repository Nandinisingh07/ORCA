import { useEffect, useState } from 'react'
import { Fish, RefreshCw, ShieldAlert, Waves } from 'lucide-react'
import { Button, StatusPill } from './OrcaUI'
import { api } from '../lib/api'

type Props = {
  place?: string
}

function toneFor(level?: string): 'teal' | 'amber' | 'red' {
  if (level === 'unsafe') return 'red'
  if (level === 'safe') return 'teal'
  return 'amber'
}

export function LiveSnapshot({ place = 'Veraval, Gujarat' }: Props) {
  const [conditions, setConditions] = useState<any>(null)
  const [alerts, setAlerts] = useState<any>(null)
  const [fishing, setFishing] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    setError('')

    try {
      const [conditionData, alertData, fishingData] = await Promise.all([
        api.conditions(place, 'today'),
        api.alerts('all', 'all'),
        api.fishingZones(place),
      ])

      setConditions(conditionData)
      setAlerts(alertData)
      setFishing(fishingData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load the live snapshot.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [place])

  const activeAlerts = (alerts?.alerts ?? []).filter((item: any) => !item.is_sample)
  const firstZone = fishing?.zones?.[0]

  return (
    <div className="content-panel">
      <div className="panel-head">
        <div>
          <h2>Live intelligence snapshot</h2>
          <p className="panel-desc" style={{ margin: 0 }}>
            {place} · current ORCA backend signals
          </p>
        </div>

        <Button variant="outline" onClick={() => void load()} disabled={loading}>
          <RefreshCw size={15} />
          Refresh
        </Button>
      </div>

      {error && (
        <p className="source-line">
          Unable to load snapshot: {error}
        </p>
      )}

      {!error && (
        <div className="data-grid" style={{ marginTop: 18 }}>
          <div className="data-card">
            <small><Waves size={14} /> Ocean status</small>
            <strong>{conditions?.summary?.label ?? 'Loading'}</strong>
            <span>
              {conditions?.summary?.wave_m_max != null
                ? `${conditions.summary.wave_m_max.toFixed(2)} m max wave`
                : 'Forecast loading'}
            </span>
          </div>

          <div className="data-card">
            <small><ShieldAlert size={14} /> Active signals</small>
            <strong>{activeAlerts.length}</strong>
            <span>
              <StatusPill tone={toneFor(activeAlerts[0]?.severity)}>
                {activeAlerts[0]?.severity ?? 'No alert'}
              </StatusPill>
            </span>
          </div>

          <div className="data-card">
            <small><Fish size={14} /> Fishing context</small>
            <strong>{fishing?.zones?.length ?? '—'}</strong>
            <span>
              {firstZone?.distance_km != null
                ? `${firstZone.distance_km} km to nearest candidate`
                : 'No zone returned'}
            </span>
          </div>
        </div>
      )}

      <p className="source-line" style={{ marginTop: 16 }}>
        Conditions mode: {conditions?.data_mode ?? '—'} ·
        Alerts mode: {alerts?.data_mode ?? '—'} ·
        Fishing-zone mode: {fishing?.advisory?.is_sample ? 'sample/heuristic' : 'derived'}
      </p>
    </div>
  )
}
