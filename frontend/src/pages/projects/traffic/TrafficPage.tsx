import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts'
import { Users, Globe, Smartphone, ExternalLink, RefreshCw, TrendingUp, FlaskConical } from 'lucide-react'
import { getPerformanceSummary } from '@/api/performance'
import type { PerformanceSummary } from '@/types'
import { Card } from '@/components/ui/Card'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'
import Button from '@/components/ui/Button'

type Period = '7d' | '30d' | '90d' | '180d' | '365d'

type DeviceTrendPoint = { date: string; desktop: number; mobile: number; tablet: number }

function buildDeviceTrend(period: Period): DeviceTrendPoint[] {
  const count = period === '7d' ? 7 : period === '30d' ? 30 : period === '90d' ? 90 : period === '180d' ? 180 : 365
  const BASE = new Date('2026-05-06')
  return Array.from({ length: count }, (_, i) => {
    const d = new Date(BASE)
    d.setDate(BASE.getDate() - (count - 1 - i))
    const total = Math.floor(40 + 35 * Math.abs(Math.sin(i * 0.4 + 1)) + 15 * Math.abs(Math.sin(i * 0.13)))
    return {
      date: d.toISOString().slice(0, 10),
      desktop: Math.floor(total * 0.52),
      mobile: Math.floor(total * 0.41),
      tablet: Math.floor(total * 0.07),
    }
  })
}

function buildDemoData(period: Period): PerformanceSummary {
  const count = period === '7d' ? 7 : period === '30d' ? 30 : period === '90d' ? 90 : period === '180d' ? 180 : 365
  const BASE = new Date('2026-05-06')
  const trend_by_day = Array.from({ length: count }, (_, i) => {
    const d = new Date(BASE)
    d.setDate(BASE.getDate() - (count - 1 - i))
    const v = Math.floor(40 + 35 * Math.abs(Math.sin(i * 0.4 + 1)) + 15 * Math.abs(Math.sin(i * 0.13)))
    return { date: d.toISOString().slice(0, 10), views: v }
  })
  const total_views = trend_by_day.reduce((s, d) => s + d.views, 0)
  return {
    period,
    total_views,
    unique_pages: Math.floor(total_views * 0.6),
    trend_by_day,
    top_pages: [
      { path: '/blog/optimiser-seo-2025', views: Math.floor(total_views * 0.22) },
      { path: '/blog/core-web-vitals', views: Math.floor(total_views * 0.17) },
      { path: '/blog/schema-markup', views: Math.floor(total_views * 0.13) },
      { path: '/blog/backlinks-guide', views: Math.floor(total_views * 0.10) },
      { path: '/blog/seo-local', views: Math.floor(total_views * 0.08) },
    ],
    referrers: [
      { referrer: '', views: Math.floor(total_views * 0.38) },
      { referrer: 'google.com', views: Math.floor(total_views * 0.32) },
      { referrer: 'twitter.com', views: Math.floor(total_views * 0.12) },
      { referrer: 'linkedin.com', views: Math.floor(total_views * 0.08) },
      { referrer: 'reddit.com', views: Math.floor(total_views * 0.05) },
    ],
    countries: [
      { country: 'France', views: Math.floor(total_views * 0.54) },
      { country: 'Belgique', views: Math.floor(total_views * 0.14) },
      { country: 'Suisse', views: Math.floor(total_views * 0.09) },
      { country: 'Canada', views: Math.floor(total_views * 0.07) },
      { country: 'Maroc', views: Math.floor(total_views * 0.04) },
    ],
    devices: [
      { device: 'desktop', views: Math.floor(total_views * 0.52) },
      { device: 'mobile', views: Math.floor(total_views * 0.41) },
      { device: 'tablet', views: Math.floor(total_views * 0.07) },
    ],
  }
}

const PERIODS: { value: Period; label: string }[] = [
  { value: '7d', label: '7 j' },
  { value: '30d', label: '30 j' },
  { value: '90d', label: '90 j' },
  { value: '180d', label: '6 m' },
  { value: '365d', label: '1 an' },
]

const DEVICE_LABELS: Record<string, string> = {
  desktop: 'Ordinateur',
  mobile: 'Mobile',
  tablet: 'Tablette',
  unknown: 'Inconnu',
}

function StatCard({ icon, value, label }: { icon: React.ReactNode; value: string | number; label: string }) {
  return (
    <Card padding="sm" className="flex flex-col gap-2">
      <span className="text-tertiary">{icon}</span>
      <div>
        <p className="text-[22px] font-semibold text-primary tracking-tight">{value}</p>
        <p className="text-[12px] text-tertiary">{label}</p>
      </div>
    </Card>
  )
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <p className="text-[12px] font-semibold text-secondary uppercase tracking-wide mb-3">{children}</p>
}

function RankRow({ rank, label, value, total }: { rank: number; label: string; value: number; total: number }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0
  return (
    <div className="flex items-center gap-3 py-1.5 border-b border-border last:border-0">
      <span className="text-[11px] font-medium text-tertiary w-4 shrink-0">{rank}</span>
      <span className="flex-1 text-[13px] text-primary truncate" title={label}>{label || 'Direct / Inconnu'}</span>
      <div className="flex items-center gap-2 shrink-0">
        <div className="h-1.5 w-16 rounded-full bg-[#f0f0f2] overflow-hidden">
          <div className="h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
        </div>
        <span className="text-[11px] text-tertiary w-7 text-right">{pct}%</span>
        <span className="text-[12px] font-medium text-secondary w-10 text-right">{value.toLocaleString('fr-FR')}</span>
      </div>
    </div>
  )
}

export default function TrafficPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [period, setPeriod] = useState<Period>('30d')
  const [data, setData] = useState<PerformanceSummary | null>(null)
  const [loadStatus, setLoadStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [tick, setTick] = useState(0)

  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    Promise.resolve().then(() => { if (!cancelled) setLoadStatus('loading') })
    getPerformanceSummary(projectId, period)
      .then((d) => { if (!cancelled) { setData(d); setLoadStatus('success') } })
      .catch(() => { if (!cancelled) setLoadStatus('error') })
    return () => { cancelled = true }
  }, [projectId, period, tick])

  const hasRealData = data && (data.total_views > 0 || data.trend_by_day.length > 0)
  const isDemoMode = import.meta.env.DEV && loadStatus === 'success' && !hasRealData
  const displayData: PerformanceSummary | null = isDemoMode ? buildDemoData(period) : data
  const hasData = isDemoMode || hasRealData
  const topDevice = displayData?.devices.sort((a, b) => b.views - a.views)[0]
  const topCountry = displayData?.countries.sort((a, b) => b.views - a.views)[0]
  const deviceTrend: DeviceTrendPoint[] = isDemoMode ? buildDeviceTrend(period) : []

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-6 flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div>
            <h1 className="text-[20px] font-semibold text-primary tracking-tight">Trafic</h1>
            <p className="mt-0.5 text-[13px] text-secondary">Comportement des visiteurs et sources de trafic.</p>
          </div>
          {isDemoMode && (
            <span className="flex items-center gap-1 rounded-full bg-warning/10 px-2.5 py-1 text-[11px] font-medium text-[#c07000]">
              <FlaskConical size={11} />
              Données de démonstration
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-[10px] border border-border bg-surface overflow-hidden">
            {PERIODS.map((p) => (
              <button
                key={p.value}
                onClick={() => setPeriod(p.value)}
                className={`px-3 py-1.5 text-[12px] font-medium transition-colors ${
                  period === p.value ? 'bg-accent text-white' : 'text-secondary hover:bg-[#f0f0f2] hover:text-primary'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
          <Button size="sm" variant="secondary" icon={<RefreshCw size={13} />} onClick={() => setTick(t => t + 1)}>
            Rafraîchir
          </Button>
        </div>
      </div>

      {loadStatus === 'loading' && <LoadingState />}
      {loadStatus === 'error' && <ErrorState onRetry={() => setTick(t => t + 1)} />}

      {loadStatus === 'success' && !hasData && (
        <div className="flex flex-col items-center gap-4 py-20 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-[16px] bg-[#f0f0f2] text-tertiary">
            <TrendingUp size={22} />
          </div>
          <div>
            <p className="text-[15px] font-medium text-primary">Aucune donnée de trafic</p>
            <p className="mt-1 max-w-xs text-[13px] text-secondary">
              Installez le snippet de tracking pour commencer à collecter des données visiteurs.
            </p>
          </div>
          <button
            onClick={() => navigate(`/projects/${projectId}/settings/integration`)}
            className="flex items-center gap-1.5 rounded-[10px] bg-accent px-4 py-2 text-[13px] font-medium text-white hover:bg-accent/90 transition-colors"
          >
            <ExternalLink size={13} />
            Voir le snippet
          </button>
        </div>
      )}

      {loadStatus === 'success' && hasData && displayData && (
        <div className="flex flex-col gap-6">
          {/* Graph + Stats 2x2 row */}
          {(deviceTrend.length > 0 || displayData.trend_by_day.length > 0) && (
            <div className="flex gap-4">
              <Card className="flex-[2]">
                <SectionTitle>Visites par appareil ({period})</SectionTitle>
              <ResponsiveContainer width="100%" height={220}>
                {deviceTrend.length > 0 ? (
                  <LineChart data={deviceTrend} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" vertical={false} />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 11, fill: '#86868b' }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v) => v.slice(5)}
                      interval="preserveStartEnd"
                    />
                    <YAxis tick={{ fontSize: 11, fill: '#86868b' }} tickLine={false} axisLine={false} width={30} />
                    <Tooltip
                      contentStyle={{ fontSize: 12, borderRadius: 10, border: '1px solid rgba(0,0,0,0.08)', boxShadow: 'none' }}
                      labelStyle={{ color: '#1d1d1f', fontWeight: 600 }}
                      formatter={(v, name) => [Number(v).toLocaleString('fr-FR'), DEVICE_LABELS[name as string] ?? name]}
                    />
                    <Legend
                      iconType="circle"
                      iconSize={8}
                      wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
                      formatter={(v) => DEVICE_LABELS[v] ?? v}
                    />
                    <Line type="monotone" dataKey="desktop" stroke="#007aff" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
                    <Line type="monotone" dataKey="mobile" stroke="#34c759" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
                    <Line type="monotone" dataKey="tablet" stroke="#ff9500" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
                  </LineChart>
                ) : (
                  <LineChart data={displayData.trend_by_day} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" vertical={false} />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#86868b' }} tickLine={false} axisLine={false} tickFormatter={(v) => v.slice(5)} interval="preserveStartEnd" />
                    <YAxis tick={{ fontSize: 11, fill: '#86868b' }} tickLine={false} axisLine={false} width={30} />
                    <Tooltip contentStyle={{ fontSize: 12, borderRadius: 10, border: '1px solid rgba(0,0,0,0.08)', boxShadow: 'none' }} formatter={(v) => [Number(v).toLocaleString('fr-FR'), 'Vues']} />
                    <Line type="monotone" dataKey="views" stroke="#007aff" strokeWidth={2} dot={false} activeDot={{ r: 4, fill: '#007aff' }} />
                  </LineChart>
                )}
              </ResponsiveContainer>
              </Card>
              {/* Stats 2x2 right */}
              <div className="grid grid-cols-2 gap-3 flex-1 content-start">
                <StatCard icon={<Users size={18} />} value={displayData.total_views.toLocaleString('fr-FR')} label="Pages vues" />
                <StatCard icon={<Globe size={18} />} value={displayData.unique_pages.toLocaleString('fr-FR')} label="Pages uniques" />
                <StatCard icon={<Smartphone size={18} />} value={topDevice ? DEVICE_LABELS[topDevice.device] ?? topDevice.device : '—'} label="Appareil top" />
                <StatCard icon={<Globe size={18} />} value={topCountry?.country || '—'} label="Pays top" />
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            {/* Sources */}
            {displayData.referrers.length > 0 && (
              <Card>
                <SectionTitle>Sources de trafic</SectionTitle>
                {displayData.referrers.slice(0, 10).map((r, i) => (
                  <RankRow
                    key={r.referrer}
                    rank={i + 1}
                    label={r.referrer || 'Direct'}
                    value={r.views}
                    total={displayData.total_views}
                  />
                ))}
              </Card>
            )}

            {/* Pays */}
            {displayData.countries.length > 0 && (
              <Card>
                <SectionTitle>Pays</SectionTitle>
                {displayData.countries.slice(0, 10).map((c, i) => (
                  <RankRow
                    key={c.country}
                    rank={i + 1}
                    label={c.country || 'Inconnu'}
                    value={c.views}
                    total={displayData.total_views}
                  />
                ))}
              </Card>
            )}

            {/* Appareils */}
            {displayData.devices.length > 0 && (
              <Card>
                <SectionTitle>Appareils</SectionTitle>
                {displayData.devices.map((d, i) => (
                  <RankRow
                    key={d.device}
                    rank={i + 1}
                    label={DEVICE_LABELS[d.device] ?? d.device}
                    value={d.views}
                    total={displayData.total_views}
                  />
                ))}
              </Card>
            )}

            {/* Pages visitées */}
            {displayData.top_pages.length > 0 && (
              <Card>
                <SectionTitle>Pages les plus visitées</SectionTitle>
                {displayData.top_pages.slice(0, 10).map((p, i) => (
                  <RankRow
                    key={p.path}
                    rank={i + 1}
                    label={p.path}
                    value={p.views}
                    total={displayData.total_views}
                  />
                ))}
              </Card>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
