import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts'
import {
  ExternalLink,
  BarChart3,
  Globe,
  Mail,
  Monitor,
  MousePointer2,
  RefreshCw,
  Smartphone,
  Tablet,
  TrendingUp,
  Users,
} from 'lucide-react'
import { getPerformanceSummary } from '@/api/performance'
import type { PerformanceSummary } from '@/types'
import { Card } from '@/components/ui/Card'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'
import Button from '@/components/ui/Button'
import {
  formatAxisTick,
  formatMetric,
  getCountryDisplay,
  getDeviceLabel,
  getFaviconUrl,
  getSourceChannel,
  getSourceDisplay,
  percentOf,
} from '@/utils/trafficDisplay'

type Period = '1d' | '7d' | '30d' | '90d' | '180d' | '365d'

type ChannelTrendPoint = {
  date: string
  direct: number
  organic: number
  social: number
  referral: number
}

type SourceRow = {
  key: string
  label: string
  raw: string
  channel: string
  visits: number
  visitors: number | null
  variation: number | null
  share: number
}

const PERIODS: { value: Period; label: string }[] = [
  { value: '1d', label: '1 jour' },
  { value: '7d', label: '7 jours' },
  { value: '30d', label: '30 jours' },
  { value: '90d', label: '90 jours' },
  { value: '180d', label: '6 mois' },
  { value: '365d', label: '1 an' },
]

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <p className="mb-3 text-[12px] font-semibold uppercase tracking-wide text-secondary">{children}</p>
}

function VariationBadge({ value }: { value: number | null | undefined }) {
  if (value === null || value === undefined) return <span className="text-[12px] text-tertiary">—</span>
  const positive = value >= 0
  return <span className={`text-[12px] font-semibold ${positive ? 'text-success' : 'text-danger'}`}>{positive ? '+' : ''}{value}%</span>
}

function StatCard({
  icon,
  value,
  label,
  variation,
  tone = 'accent',
}: {
  icon: React.ReactNode
  value: React.ReactNode
  label: string
  variation?: number | null
  tone?: 'accent' | 'success' | 'warning' | 'danger' | 'violet'
}) {
  const toneClass = {
    accent: 'bg-accent/10 text-accent',
    success: 'bg-success/10 text-success',
    warning: 'bg-warning/12 text-[#b46a00]',
    danger: 'bg-danger/10 text-danger',
    violet: 'bg-[#eef2ff] text-[#4f46e5]',
  }[tone]
  return (
    <Card padding="sm" className="flex h-full flex-col justify-between gap-2">
      <span className={`flex h-8 w-8 items-center justify-center rounded-[10px] ${toneClass}`}>{icon}</span>
      <div>
        <p className="truncate text-[22px] font-semibold tracking-tight text-primary">{value}</p>
        <div className="mt-0.5 flex items-center justify-between gap-2">
          <p className="text-[12px] text-tertiary">{label}</p>
          {variation !== undefined && <VariationBadge value={variation} />}
        </div>
      </div>
    </Card>
  )
}

function DeviceIcon({ device }: { device: string }) {
  const normalized = device.toLowerCase()
  if (normalized === 'mobile') return <Smartphone size={15} />
  if (normalized === 'tablet') return <Tablet size={15} />
  return <Monitor size={15} />
}

function SourceMark({ referrer }: { referrer: string }) {
  const source = getSourceDisplay(referrer)
  const favicon = getFaviconUrl(source.domain)
  const [faviconFailed, setFaviconFailed] = useState(false)

  if (source.kind === 'direct') return <MousePointer2 size={15} />
  if (favicon && !faviconFailed) return <img src={favicon} alt="" className="h-4 w-4 rounded-[4px]" onError={() => setFaviconFailed(true)} />
  if (source.domain.includes('newsletter')) return <Mail size={15} />
  return <Globe size={15} />
}

function buildSourceRows(data: PerformanceSummary): SourceRow[] {
  const rows = data.referrers.length ? data.referrers : [{ referrer: '', views: data.total_views }]
  const totalVisits = Math.max(1, rows.reduce((sum, item) => sum + item.views, 0))
  return rows.map((item) => {
    const source = getSourceDisplay(item.referrer)
    return {
      key: item.referrer || 'direct',
      label: source.label,
      raw: item.referrer,
      channel: getSourceChannel(item.referrer),
      visits: item.views,
      visitors: null,
      variation: null,
      share: percentOf(item.views, totalVisits),
    }
  }).sort((a, b) => b.visits - a.visits)
}

function buildChannelTrend(data: PerformanceSummary, sources: SourceRow[]): ChannelTrendPoint[] {
  const trend = data.trend_by_day
  const totals = sources.reduce<Record<string, number>>((acc, source) => {
    const key = source.channel === 'Organic Search' ? 'organic' : source.channel.toLowerCase()
    acc[key] = (acc[key] ?? 0) + source.visits
    return acc
  }, {})
  const total = Math.max(1, Object.values(totals).reduce((sum, value) => sum + value, 0))
  return trend.map((point) => {
    return {
      date: point.date,
      direct: Math.round(point.views * ((totals.direct ?? 0) / total)),
      organic: Math.round(point.views * ((totals.organic ?? 0) / total)),
      social: Math.round(point.views * ((totals.social ?? 0) / total)),
      referral: Math.round(point.views * ((totals.referral ?? 0) / total)),
    }
  })
}

function trafficTick(period: Period, value: unknown) {
  const label = String(value)
  if (period === '1d' || period === '90d' || period === '180d' || period === '365d') return label
  return label.includes('-') ? label.slice(5) : label
}

function entryPageLabel(path: string) {
  const lowerPath = path.toLowerCase()
  if (lowerPath.includes('roi')) return 'ROI'
  return path
    .replace(/^\/blog\//, '')
    .replace(/^\/+/, '')
    .split(/[/?#]/)[0]
    .split('-')
    .filter(Boolean)
    .slice(0, 4)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ') || path
}

function entryPageHref(path: string) {
  return path.startsWith('http') ? path : path
}

function VisualRow({
  rank,
  label,
  value,
  total,
  leading,
  meta,
  href,
}: {
  rank?: number
  label: string
  value: number
  total: number
  leading: React.ReactNode
  meta?: React.ReactNode
  href?: string
}) {
  const pct = percentOf(value, total)
  return (
    <div className="flex items-center gap-2.5 rounded-[10px] px-2 py-1 hover:bg-[#f9f9fb]">
      {rank !== undefined && <span className="w-4 shrink-0 text-[11px] font-medium text-tertiary">{rank}</span>}
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[9px] bg-[#f0f0f2] text-secondary">{leading}</span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-3">
          {href ? (
            <a href={href} className="truncate text-[13px] font-medium text-primary hover:text-accent" title={label}>
              {label}
            </a>
          ) : (
            <span className="truncate text-[13px] font-medium text-primary" title={label}>{label}</span>
          )}
          <span className="shrink-0 text-[12px] font-semibold text-secondary">{formatMetric(value)}</span>
        </div>
        <div className="mt-1 flex items-center gap-2">
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[#f0f0f2]">
            <div className="h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
          </div>
          <span className="w-8 text-right text-[11px] text-tertiary">{pct}%</span>
        </div>
        {meta && <div className="mt-0.5 text-[11px] text-tertiary">{meta}</div>}
      </div>
    </div>
  )
}

export default function TrafficPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [period, setPeriod] = useState<Period>('1d')
  const [data, setData] = useState<PerformanceSummary | null>(null)
  const [loadStatus, setLoadStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [tick, setTick] = useState(0)

  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    Promise.resolve().then(() => { if (!cancelled) setLoadStatus('loading') })
    getPerformanceSummary(projectId, period)
      .then((summary) => { if (!cancelled) { setData(summary); setLoadStatus('success') } })
      .catch(() => { if (!cancelled) setLoadStatus('error') })
    return () => { cancelled = true }
  }, [projectId, period, tick])

  const hasRealData = Boolean(data && data.total_views > 0)
  const displayData = data
  const hasData = Boolean(hasRealData)
  const sources = useMemo(() => displayData ? buildSourceRows(displayData) : [], [displayData])
  const totalVisits = sources.reduce((sum, source) => sum + source.visits, 0)
  const channelTrend = useMemo(() => displayData ? buildChannelTrend(displayData, sources) : [], [displayData, sources])
  const topSource = sources[0]
  const topCountry = displayData ? [...displayData.countries].sort((a, b) => b.views - a.views)[0] : undefined
  const mobileViews = displayData?.devices.find((device) => device.device === 'mobile')?.views ?? 0
  const mobileShare = totalVisits ? percentOf(mobileViews, totalVisits) : 0
  const uniqueVisitors = displayData?.unique_pages ?? null
  const visits = totalVisits || null
  const pagesPerSession = visits && displayData ? (displayData.total_views / visits).toFixed(1).replace('.', ',') : null
  const channels = ['Organic Search', 'Direct', 'Social', 'Referral'].map((channel) => ({
    channel,
    visits: sources.filter((source) => source.channel === channel).reduce((sum, source) => sum + source.visits, 0),
  })).filter((channel) => channel.visits > 0)

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[20px] font-semibold tracking-tight text-primary">Trafic</h1>
          <p className="mt-0.5 text-[13px] text-secondary">Comprenez d’où viennent les visiteurs et quelles sources apportent le meilleur trafic.</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex overflow-hidden rounded-[10px] border border-border bg-surface">
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
          <Button size="sm" variant="secondary" icon={<RefreshCw size={13} />} onClick={() => setTick((t) => t + 1)}>
            Rafraîchir
          </Button>
        </div>
      </div>

      {loadStatus === 'loading' && <LoadingState />}
      {loadStatus === 'error' && <ErrorState onRetry={() => setTick((t) => t + 1)} />}

      {loadStatus === 'success' && !hasData && (
        <div className="flex flex-col items-center gap-4 py-20 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-[16px] bg-[#f0f0f2] text-tertiary">
            <TrendingUp size={22} />
          </div>
          <div>
            <p className="text-[15px] font-medium text-primary">Aucune donnée disponible pour le moment</p>
            <p className="mt-1 max-w-xs text-[13px] text-secondary">
              Connectez votre site pour commencer à collecter les statistiques.
            </p>
          </div>
          <button onClick={() => navigate(`/projects/${projectId}/settings/integration`)} className="flex items-center gap-1.5 rounded-[10px] bg-accent px-4 py-2 text-[13px] font-medium text-white hover:bg-accent/90">
            <ExternalLink size={13} />
            Voir le snippet
          </button>
        </div>
      )}

      {loadStatus === 'success' && hasData && displayData && (
        <div className="flex flex-col gap-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <StatCard icon={<Users size={18} />} value={uniqueVisitors !== null ? formatMetric(uniqueVisitors) : '—'} label="Visiteurs uniques" variation={null} tone="accent" />
            <StatCard icon={<TrendingUp size={18} />} value={visits !== null ? formatMetric(visits) : '—'} label="Visites" variation={null} tone="success" />
            <StatCard icon={<EyeIcon />} value={formatMetric(displayData.total_views)} label="Pages vues" variation={null} tone="violet" />
            <StatCard icon={<Users size={18} />} value="—" label="Nouveaux visiteurs" variation={null} tone="warning" />
            <StatCard icon={<RefreshCw size={18} />} value="—" label="Taux de retour" variation={null} tone="danger" />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)] lg:items-stretch">
            <Card className="h-[360px]">
              <SectionTitle>Évolution du trafic par canal</SectionTitle>
              <div className="h-[245px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={channelTrend} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" vertical={false} />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#86868b' }} tickLine={false} axisLine={false} tickFormatter={(v) => trafficTick(period, v)} interval="preserveStartEnd" />
                    <YAxis tick={{ fontSize: 11, fill: '#86868b' }} tickLine={false} axisLine={false} width={44} allowDecimals={false} domain={[0, 'dataMax']} tickFormatter={formatAxisTick} />
                    <Tooltip cursor={false} contentStyle={{ fontSize: 12, borderRadius: 10, border: '1px solid rgba(0,0,0,0.08)', boxShadow: 'none' }} formatter={(v) => [formatMetric(Number(v)), 'Visites']} />
                    <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
                    <Line type="monotone" dataKey="organic" name="Google" stroke="#34c759" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
                    <Line type="monotone" dataKey="direct" name="Direct" stroke="#007aff" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
                    <Line type="monotone" dataKey="social" name="Social" stroke="#5856d6" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
                    <Line type="monotone" dataKey="referral" name="Referral" stroke="#ff9500" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-2 grid gap-1 text-[11px] text-tertiary sm:grid-cols-2">
                <span><strong className="text-secondary">Google</strong> : recherche organique</span>
                <span><strong className="text-secondary">Direct</strong> : accès sans référent</span>
                <span><strong className="text-secondary">Social</strong> : réseaux sociaux</span>
                <span><strong className="text-secondary">Referral</strong> : sites externes</span>
              </div>
            </Card>
            <div className="grid grid-cols-2 gap-3 lg:h-[360px]">
              <StatCard icon={<SourceMark referrer={topSource?.raw ?? ''} />} value={topSource?.label ?? '—'} label="Source principale" variation={topSource?.variation ?? null} tone="success" />
              <StatCard
                icon={<span className="text-[15px] leading-none">{topCountry ? getCountryDisplay(topCountry.country).flag : '•'}</span>}
                value={topCountry ? getCountryDisplay(topCountry.country).label : '—'}
                label="Pays principal"
                variation={null}
                tone="accent"
              />
              <StatCard icon={<Smartphone size={18} />} value={<SplitMetric value={mobileShare} suffix="%" />} label="Part mobile" variation={null} tone="violet" />
              <StatCard icon={<BarSmallIcon />} value={pagesPerSession ? <SplitMetric value={pagesPerSession} suffix="pages/session" /> : '—'} label="Pages/session" variation={null} tone="warning" />
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(280px,0.9fr)]">
            <Card>
              <SectionTitle>Sources de trafic</SectionTitle>
              <div className="grid gap-1">
                {sources.slice(0, 8).map((source, index) => (
                  <VisualRow
                    key={source.key}
                    rank={index + 1}
                    label={source.label}
                    value={source.visits}
                    total={totalVisits}
                    leading={<SourceMark referrer={source.raw} />}
                    meta={<span>{source.channel} · visiteurs {source.visitors !== null ? formatMetric(source.visitors) : '—'} · évolution <VariationBadge value={source.variation} /></span>}
                  />
                ))}
              </div>
            </Card>

            <Card>
              <SectionTitle>Canaux</SectionTitle>
              <div className="flex flex-col gap-1">
                {channels.map((channel) => (
                  <VisualRow
                    key={channel.channel}
                    label={channel.channel}
                    value={channel.visits}
                    total={totalVisits}
                    leading={channel.channel === 'Organic Search' ? <Globe size={15} /> : channel.channel === 'Direct' ? <MousePointer2 size={15} /> : channel.channel === 'Social' ? <Users size={15} /> : <ExternalLink size={15} />}
                  />
                ))}
              </div>
            </Card>
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <Card>
              <SectionTitle>Appareils</SectionTitle>
              {displayData.devices.map((device, index) => (
                <VisualRow key={device.device} rank={index + 1} label={getDeviceLabel(device.device)} value={device.views} total={totalVisits} leading={<DeviceIcon device={device.device} />} />
              ))}
            </Card>
            <Card>
              <SectionTitle>Pays</SectionTitle>
              {displayData.countries.slice(0, 8).map((country, index) => (
                <VisualRow key={country.country} rank={index + 1} label={getCountryDisplay(country.country).label} value={country.views} total={totalVisits} leading={<span className="text-[15px] leading-none">{getCountryDisplay(country.country).flag}</span>} />
              ))}
            </Card>
            <Card>
              <SectionTitle>Trafic organique / mots-clés</SectionTitle>
              <p className="rounded-[12px] bg-[#f9f9fb] px-3 py-3 text-[13px] text-secondary">
                Données Search Console bientôt disponibles. Cette zone affichera les mots-clés organiques liés aux pages d’entrée Google.
              </p>
            </Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <SectionTitle>Pages d’entrée</SectionTitle>
              {displayData.top_pages.slice(0, 8).map((page, index) => (
                <VisualRow
                  key={page.path}
                  rank={index + 1}
                  label={entryPageLabel(page.path)}
                  value={page.views}
                  total={displayData.total_views}
                  leading={<ExternalLink size={15} />}
                  href={entryPageHref(page.path)}
                  meta={<span>{topSource?.label ?? '—'}</span>}
                />
              ))}
            </Card>
            <Card>
              <SectionTitle>Référents</SectionTitle>
              {sources.filter((source) => source.channel === 'Referral' || source.channel === 'Social').slice(0, 8).map((source, index) => (
                <VisualRow
                  key={source.key}
                  rank={index + 1}
                  label={source.label}
                  value={source.visits}
                  total={totalVisits}
                  leading={<SourceMark referrer={source.raw} />}
                  meta={<span>Entrée : {displayData.top_pages[0] ? entryPageLabel(displayData.top_pages[0].path) : '—'}</span>}
                />
              ))}
              {!sources.some((source) => source.channel === 'Referral' || source.channel === 'Social') && (
                <p className="rounded-[12px] bg-[#f9f9fb] px-3 py-3 text-[13px] text-secondary">Aucun référent externe disponible sur cette période.</p>
              )}
            </Card>
          </div>

          <Card>
            <SectionTitle>Qualité des sources</SectionTitle>
            <div className="overflow-x-auto">
              <div className="min-w-[860px]">
                <div className="grid grid-cols-[1.1fr_1fr_0.8fr_0.8fr_0.9fr_0.9fr_0.8fr_1.4fr_0.8fr] gap-3 border-b border-border px-2 pb-2 text-[11px] font-semibold uppercase tracking-wide text-tertiary">
                  <span>Source</span><span>Canal</span><span>Visiteurs</span><span>Pages vues</span><span>Temps moyen</span><span>Pages/session</span><span>Retour</span><span>Meilleure entrée</span><span>Évolution</span>
                </div>
                {sources.slice(0, 8).map((source, index) => (
                  <div key={source.key} className="grid grid-cols-[1.1fr_1fr_0.8fr_0.8fr_0.9fr_0.9fr_0.8fr_1.4fr_0.8fr] gap-3 border-b border-border px-2 py-3 text-[12px] last:border-0">
                    <span className="flex min-w-0 items-center gap-2 font-medium text-primary"><span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-[8px] bg-[#f0f0f2]"><SourceMark referrer={source.raw} /></span><span className="truncate">{source.label}</span></span>
                    <span className="text-secondary">{source.channel}</span>
                    <span>{source.visitors !== null ? formatMetric(source.visitors) : '—'}</span>
                    <span>{formatMetric(source.visits)}</span>
                    <span>—</span>
                    <span>—</span>
                    <span>—</span>
                    <span className="truncate text-secondary">{displayData.top_pages[index % Math.max(1, displayData.top_pages.length)] ? entryPageLabel(displayData.top_pages[index % displayData.top_pages.length].path) : '—'}</span>
                    <VariationBadge value={source.variation} />
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}

function EyeIcon() {
  return <TrendingUp size={18} />
}

function BarSmallIcon() {
  return <BarChart3 size={18} />
}

function SplitMetric({ value, suffix }: { value: React.ReactNode; suffix: string }) {
  return (
    <span className="inline-flex items-baseline gap-0.5">
      <span>{value}</span>
      <span className="text-[13px] font-medium text-tertiary">{suffix}</span>
    </span>
  )
}
