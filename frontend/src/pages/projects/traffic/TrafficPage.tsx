import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
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
} from '@/components/ui/hugeIcons'
import { getPerformanceSummary } from '@/api/performance'
import type { PerformanceSummary } from '@/types'
import { Card } from '@/components/ui/Card'
import MetricCard from '@/components/ui/MetricCard'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'
import Button from '@/components/ui/Button'
import PeriodNavigator, { ExportButtons } from '@/components/ui/PeriodNavigator'
import { downloadJson, printReport } from '@/utils/exportReport'
import { currentPeriod, type PeriodMode, type PeriodRange } from '@/utils/periodNavigator'
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

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <p className="mb-3 text-[12px] font-semibold uppercase tracking-wide text-secondary">{children}</p>
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
  return (
    <MetricCard
      icon={icon}
      value={value}
      label={label}
      tone={tone}
      trend={variation != null ? `${variation >= 0 ? '+' : ''}${variation}%` : null}
      className="h-full"
    />
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
  if (data.total_views === 0) return []
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

function buildChannelTrend(data: PerformanceSummary): ChannelTrendPoint[] {
  return data.channel_trend_by_day ?? []
}

function trafficTick(period: PeriodMode, value: unknown) {
  const label = String(value)
  if (period === 'day') return label
  if (period === 'year') return label.slice(0, 7)
  if (period === 'quarter' || period === 'semester') return label
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

function trackingStatusMessage(status: PerformanceSummary['tracking_status'] | undefined) {
  if (status === 'not_configured') return 'Snippet non configuré.'
  if (status === 'configured_no_data') return 'Snippet connecté, aucune donnée reçue pour cette période.'
  if (status === 'error') return 'Impossible de lire l’état du tracking.'
  return 'Aucune donnée pour cette période.'
}

function ChartEmpty({ message }: { message: string }) {
  return (
    <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
      <span className="rounded-[6px] border border-border bg-surface px-3 py-2 text-[12px] text-secondary">
        {message}
      </span>
    </div>
  )
}

function InlineEmpty({ children }: { children: React.ReactNode }) {
  return <p className="rounded-[8px] bg-surface px-3 py-3 text-[13px] text-secondary">{children}</p>
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
    <div className="flex items-center gap-2.5 rounded-[6px] px-2 py-1 hover:bg-surface-soft">
      {rank !== undefined && <span className="w-4 shrink-0 text-[11px] font-medium text-tertiary">{rank}</span>}
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[6px] bg-surface-soft text-secondary">{leading}</span>
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
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-soft">
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
  const [period, setPeriod] = useState<PeriodRange>(() => currentPeriod('day'))
  const [data, setData] = useState<PerformanceSummary | null>(null)
  const [loadStatus, setLoadStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [tick, setTick] = useState(0)

  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    Promise.resolve().then(() => { if (!cancelled) setLoadStatus('loading') })
    getPerformanceSummary(projectId, { period_type: period.mode, start_date: period.startDate, end_date: period.endDate })
      .then((summary) => { if (!cancelled) { setData(summary); setLoadStatus('success') } })
      .catch(() => { if (!cancelled) setLoadStatus('error') })
    return () => { cancelled = true }
  }, [projectId, period, tick])

  const displayData = data
  const sources = useMemo(() => displayData ? buildSourceRows(displayData) : [], [displayData])
  const totalVisits = sources.reduce((sum, source) => sum + source.visits, 0)
  const channelTrend = useMemo(() => displayData ? buildChannelTrend(displayData) : [], [displayData])
  const topSource = sources[0]
  const topCountry = displayData ? [...displayData.countries].sort((a, b) => b.views - a.views)[0] : undefined
  const mobileViews = displayData?.devices.find((device) => device.device === 'mobile')?.views ?? 0
  const mobileShare = totalVisits ? percentOf(mobileViews, totalVisits) : 0
  const uniquePages = displayData?.unique_pages ?? null
  const visits = totalVisits || null
  const channels = ['Organic Search', 'Direct', 'Social', 'Referral'].map((channel) => ({
    channel,
    visits: sources.filter((source) => source.channel === channel).reduce((sum, source) => sum + source.visits, 0),
  })).filter((channel) => channel.visits > 0).sort((a, b) => b.visits - a.visits)
  const topChannel = channels[0]

  if (loadStatus === 'loading') return <LoadingState />
  if (loadStatus === 'error') return <ErrorState onRetry={() => setTick((t) => t + 1)} />
  if (!displayData) return <ErrorState onRetry={() => setTick((t) => t + 1)} />
  const summaryData = displayData

  const trackingMessage = trackingStatusMessage(summaryData.tracking_status)
  const hasRealTraffic = summaryData.total_views > 0
  const showPeriodEmpty = !hasRealTraffic
  const hasChannelTrend = hasRealTraffic && channelTrend.length > 0

  function handleExportJson() {
    downloadJson(`ideas-studio-traffic-${period.startDate}-${period.endDate}.json`, {
      project_id: projectId,
      period,
      exported_at: new Date().toISOString(),
      summary: summaryData,
      cards: {
        total_views: summaryData.total_views,
        unique_pages: uniquePages,
        counted_sources: visits,
        top_source: topSource ?? null,
        top_channel: topChannel ?? null,
        top_country: topCountry ?? null,
        mobile_share: mobileShare,
      },
      trend: channelTrend,
      sources,
      channels,
      pages: summaryData.top_pages,
      countries: summaryData.countries,
      devices: summaryData.devices,
    })
  }

  function handleExportPdf() {
    printReport('Ideas Studio - Trafic', period.label, [
      {
        title: 'Synthèse',
        rows: [
          ['Projet', projectId ?? '—'],
          ['Période', `${period.startDate} → ${period.endDate}`],
          ['Pages vues', formatMetric(summaryData.total_views)],
          ['Pages uniques', uniquePages !== null ? formatMetric(uniquePages) : '—'],
          ['Source principale', topSource?.label ?? '—'],
          ['Famille de trafic principale', topChannel?.channel ?? '—'],
          ['Pays principal', topCountry ? getCountryDisplay(topCountry.country).label : '—'],
          ['Part mobile', `${mobileShare}%`],
        ],
      },
      {
        title: 'Évolution par canal',
        rows: channelTrend.map((point) => [
          point.date,
          `Direct ${formatMetric(point.direct)} · Google ${formatMetric(point.organic)} · Social ${formatMetric(point.social)} · Referral ${formatMetric(point.referral)}`,
        ]),
      },
      {
        title: 'Sources',
        rows: sources.slice(0, 10).map((source) => [source.label, `${formatMetric(source.visits)} vues · ${source.share}%`]),
      },
      {
        title: 'Pages d’entrée',
        rows: summaryData.top_pages.length
          ? summaryData.top_pages.slice(0, 10).map((page) => [entryPageLabel(page.path), `${formatMetric(page.views)} vues`])
          : [['Aucune page d’entrée', '—']],
      },
      {
        title: 'Pays et appareils',
        rows: [
          ...summaryData.countries.slice(0, 8).map((country) => [getCountryDisplay(country.country).label, `${formatMetric(country.views)} vues`] as [string, string]),
          ...summaryData.devices.slice(0, 5).map((device) => [getDeviceLabel(device.device), `${formatMetric(device.views)} vues`] as [string, string]),
        ],
      },
    ])
  }

  return (
    <div className="project-page project-page--wide">
      <div className="project-page-header">
        <div>
          <h1 className="text-[20px] font-semibold tracking-tight text-primary">Trafic</h1>
          <p className="mt-0.5 text-[13px] text-secondary">Comprenez d’où viennent les visiteurs et quelles sources apportent le meilleur trafic.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="secondary" icon={<RefreshCw size={13} />} onClick={() => setTick((t) => t + 1)}>
            Rafraîchir
          </Button>
          <ExportButtons onJson={handleExportJson} onPdf={handleExportPdf} />
        </div>
      </div>
      <div className="mb-6">
        <PeriodNavigator value={period} onChange={setPeriod} />
      </div>

        <div className="flex flex-col gap-6">
          {showPeriodEmpty && (
            <div className="rounded-[8px] border border-border bg-surface px-4 py-3 text-[13px] text-secondary">
              {trackingMessage}
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <StatCard icon={<Users size={18} />} value={uniquePages !== null ? formatMetric(uniquePages) : '—'} label="Pages uniques" variation={null} tone="accent" />
            <StatCard icon={<TrendingUp size={18} />} value={visits !== null ? formatMetric(visits) : '—'} label="Sources comptées" variation={null} tone="success" />
            <StatCard icon={<EyeIcon />} value={formatMetric(displayData.total_views)} label="Pages vues" variation={null} tone="violet" />
            <StatCard icon={<Globe size={18} />} value={topCountry ? getCountryDisplay(topCountry.country).label : '—'} label="Pays principal" variation={null} tone="warning" />
            <StatCard icon={<Smartphone size={18} />} value={<SplitMetric value={mobileShare} suffix="%" />} label="Part mobile" variation={null} tone="danger" />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)] lg:items-stretch">
            <Card className="h-[360px]">
              <SectionTitle>Évolution du trafic par canal</SectionTitle>
              <div className="relative h-[245px]" style={{ minHeight: 0 }}>
                <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1} debounce={100}>
                  <LineChart data={channelTrend} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" vertical={false} />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#86868b' }} tickLine={false} axisLine={false} tickFormatter={(v) => trafficTick(period.mode, v)} interval="preserveStartEnd" />
                    <YAxis tick={{ fontSize: 11, fill: '#86868b' }} tickLine={false} axisLine={false} width={44} allowDecimals={false} domain={[0, 'dataMax']} tickFormatter={formatAxisTick} />
                    <Tooltip cursor={false} contentStyle={{ fontSize: 12, borderRadius: 10, border: '1px solid rgba(0,0,0,0.08)', boxShadow: 'none' }} formatter={(v) => [formatMetric(Number(v)), 'Visites']} />
                    <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
                    <Line type="monotone" dataKey="organic" name="Google" stroke="#34c759" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
                    <Line type="monotone" dataKey="direct" name="Direct" stroke="#007aff" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
                    <Line type="monotone" dataKey="social" name="Social" stroke="#5856d6" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
                    <Line type="monotone" dataKey="referral" name="Referral" stroke="#ff9500" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
                {!hasChannelTrend && <ChartEmpty message="Aucune évolution par canal disponible pour cette période." />}
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
              <StatCard icon={<BarSmallIcon />} value={formatMetric(displayData.top_pages.length)} label="Pages d’entrée" variation={null} tone="warning" />
              <StatCard icon={<ExternalLink size={18} />} value={topChannel?.channel ?? '—'} label="Famille de trafic" variation={null} tone="violet" />
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(280px,0.9fr)]">
            <Card>
              <SectionTitle>Sources de trafic</SectionTitle>
              <div className="grid gap-1">
                {sources.length ? sources.slice(0, 8).map((source, index) => (
                  <VisualRow
                    key={source.key}
                    rank={index + 1}
                    label={source.label}
                    value={source.visits}
                    total={totalVisits}
                    leading={<SourceMark referrer={source.raw} />}
                    meta={<span>{source.channel} · {source.share}% du trafic attribué</span>}
                  />
                )) : <InlineEmpty>Aucune source disponible pour cette période.</InlineEmpty>}
              </div>
            </Card>

            <Card>
              <SectionTitle>Canaux</SectionTitle>
              <div className="flex flex-col gap-1">
                {channels.length ? channels.map((channel) => (
                  <VisualRow
                    key={channel.channel}
                    label={channel.channel}
                    value={channel.visits}
                    total={totalVisits}
                    leading={channel.channel === 'Organic Search' ? <Globe size={15} /> : channel.channel === 'Direct' ? <MousePointer2 size={15} /> : channel.channel === 'Social' ? <Users size={15} /> : <ExternalLink size={15} />}
                  />
                )) : <InlineEmpty>Aucun canal disponible pour cette période.</InlineEmpty>}
              </div>
            </Card>
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <Card>
              <SectionTitle>Appareils</SectionTitle>
              {displayData.devices.length ? displayData.devices.map((device, index) => (
                <VisualRow key={device.device} rank={index + 1} label={getDeviceLabel(device.device)} value={device.views} total={totalVisits} leading={<DeviceIcon device={device.device} />} />
              )) : <InlineEmpty>Aucun appareil disponible pour cette période.</InlineEmpty>}
            </Card>
            <Card>
              <SectionTitle>Pays</SectionTitle>
              {displayData.countries.length ? displayData.countries.slice(0, 8).map((country, index) => (
                <VisualRow key={country.country} rank={index + 1} label={getCountryDisplay(country.country).label} value={country.views} total={totalVisits} leading={<span className="text-[15px] leading-none">{getCountryDisplay(country.country).flag}</span>} />
              )) : <InlineEmpty>Aucun pays disponible pour cette période.</InlineEmpty>}
            </Card>
            <Card>
              <SectionTitle>Trafic organique / mots-clés</SectionTitle>
              <p className="rounded-[8px] bg-surface px-3 py-3 text-[13px] text-secondary">
                Connectez Google Search Console depuis les <a href={`/projects/${projectId}/settings/integration`} className="text-accent hover:underline">paramètres du projet</a> pour voir les mots-clés organiques.
              </p>
            </Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <SectionTitle>Pages d’entrée</SectionTitle>
              {displayData.top_pages.length ? displayData.top_pages.slice(0, 8).map((page, index) => (
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
              )) : <InlineEmpty>Aucune page d’entrée disponible pour cette période.</InlineEmpty>}
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
                <p className="rounded-[8px] bg-surface px-3 py-3 text-[13px] text-secondary">Aucun référent externe disponible sur cette période.</p>
              )}
            </Card>
          </div>

          <Card>
            <SectionTitle>Qualité des sources</SectionTitle>
            <div className="overflow-x-auto">
              <div className="min-w-[860px]">
                <div className="grid grid-cols-[1.4fr_1fr_0.8fr_0.8fr] gap-3 border-b border-border px-2 pb-2 text-[11px] font-semibold uppercase tracking-wide text-tertiary">
                  <span>Source</span><span>Canal</span><span>Pages vues</span><span>Part</span>
                </div>
                {sources.length ? sources.slice(0, 8).map((source) => (
                  <div key={source.key} className="grid grid-cols-[1.4fr_1fr_0.8fr_0.8fr] gap-3 border-b border-border px-2 py-3 text-[12px] last:border-0">
                    <span className="flex min-w-0 items-center gap-2 font-medium text-primary"><span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-[6px] bg-surface-soft"><SourceMark referrer={source.raw} /></span><span className="truncate">{source.label}</span></span>
                    <span className="text-secondary">{source.channel}</span>
                    <span>{formatMetric(source.visits)}</span>
                    <span>{source.share}%</span>
                  </div>
                )) : (
                  <div className="px-2 py-3">
                    <InlineEmpty>Aucune source disponible pour cette période.</InlineEmpty>
                  </div>
                )}
              </div>
            </div>
          </Card>
        </div>
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
