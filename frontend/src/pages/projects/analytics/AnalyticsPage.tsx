import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts'
import {
  Eye,
  Globe,
  MousePointer2,
  RefreshCw,
  Smartphone,
  TrendingUp,
  Users,
  ExternalLink,
  AlertTriangle,
  BarChart3,
  Mail,
  Monitor,
  Tablet,
} from '@/components/ui/hugeIcons'
import { getPerformanceSummary, getArticlesPerformance } from '@/api/performance'
import type { ArticlePerformanceBrief, PerformanceSummary } from '@/types'
import { Card } from '@/components/ui/Card'
import MetricCard from '@/components/ui/MetricCard'
import Button from '@/components/ui/Button'
import ErrorState from '@/components/ui/ErrorState'
import LoadingState from '@/components/ui/LoadingState'
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

// ── Helpers ──────────────────────────────────────────────────────────────────

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <p className="mb-3 text-[12px] font-semibold uppercase tracking-wide text-secondary">{children}</p>
}

function InlineEmpty({ children }: { children: React.ReactNode }) {
  return <p className="rounded-[12px] bg-[#f9f9fb] px-3 py-3 text-[13px] text-secondary">{children}</p>
}

function ChartEmpty({ message }: { message: string }) {
  return (
    <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
      <span className="rounded-[10px] border border-border bg-surface px-3 py-2 text-[12px] text-secondary">{message}</span>
    </div>
  )
}

function VisualRow({
  rank,
  label,
  value,
  total,
  leading,
  meta,
}: {
  rank?: number
  label: string
  value: number
  total: number
  leading: React.ReactNode
  meta?: React.ReactNode
}) {
  const pct = percentOf(value, total)
  return (
    <div className="flex items-center gap-2.5 rounded-[10px] px-2 py-1 hover:bg-[#f9f9fb]">
      {rank !== undefined && <span className="w-4 shrink-0 text-[11px] font-medium text-tertiary">{rank}</span>}
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[9px] bg-[#f0f0f2] text-secondary">{leading}</span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-3">
          <span className="truncate text-[13px] font-medium text-primary" title={label}>{label}</span>
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

function SourceMark({ referrer }: { referrer: string }) {
  const source = getSourceDisplay(referrer)
  const favicon = getFaviconUrl(source.domain)
  const [failed, setFailed] = useState(false)
  if (source.kind === 'direct') return <MousePointer2 size={15} />
  if (favicon && !failed) return <img src={favicon} alt="" className="h-4 w-4 rounded-[4px]" onError={() => setFailed(true)} />
  if (source.domain.includes('newsletter')) return <Mail size={15} />
  return <Globe size={15} />
}

function DeviceIcon({ device }: { device: string }) {
  const n = device.toLowerCase()
  if (n === 'mobile') return <Smartphone size={15} />
  if (n === 'tablet') return <Tablet size={15} />
  return <Monitor size={15} />
}

function chartTick(period: PeriodMode, value: unknown) {
  const label = String(value)
  if (period === 'year') return label.slice(0, 7)
  return label.includes('-') ? label.slice(5) : label
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [period, setPeriod] = useState<PeriodRange>(() => currentPeriod('day'))
  const [summary, setSummary] = useState<PerformanceSummary | null>(null)
  const [articleMetrics, setArticleMetrics] = useState<ArticlePerformanceBrief[]>([])
  const [loadStatus, setLoadStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [tick, setTick] = useState(0)

  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    setLoadStatus('loading')
    const periodParams = { period_type: period.mode, start_date: period.startDate, end_date: period.endDate }
    Promise.all([
      getPerformanceSummary(projectId, periodParams),
      getArticlesPerformance(projectId, periodParams),
    ])
      .then(([s, a]) => {
        if (cancelled) return
        setSummary(s)
        setArticleMetrics(a)
        setLoadStatus('success')
      })
      .catch(() => { if (!cancelled) setLoadStatus('error') })
    return () => { cancelled = true }
  }, [projectId, period, tick])

  const sources = useMemo(() => {
    if (!summary) return []
    const rows = summary.referrers.length ? summary.referrers : [{ referrer: '', views: summary.total_views }]
    const totalVisits = Math.max(1, rows.reduce((sum, r) => sum + r.views, 0))
    return rows.map((r) => {
      const source = getSourceDisplay(r.referrer)
      return {
        key: r.referrer || 'direct',
        label: source.label,
        raw: r.referrer,
        channel: getSourceChannel(r.referrer),
        visits: r.views,
        share: percentOf(r.views, totalVisits),
      }
    }).sort((a, b) => b.visits - a.visits)
  }, [summary])

  const totalVisits = sources.reduce((sum, s) => sum + s.visits, 0)

  const channelTrend = summary?.channel_trend_by_day ?? []
  const hasChannelTrend = channelTrend.length > 0 && summary && summary.total_views > 0

  const avgSeoScore = useMemo(() => {
    const withScore = articleMetrics.filter((a) => a.seo_score !== null)
    if (withScore.length === 0) return null
    return Math.round(withScore.reduce((sum, a) => sum + (a.seo_score ?? 0), 0) / withScore.length)
  }, [articleMetrics])

  const toOptimize = useMemo(
    () => articleMetrics.filter((a) => (a.seo_score ?? 100) < 70).slice(0, 6),
    [articleMetrics],
  )

  function handleExportJson() {
    downloadJson(`ideas-studio-analytics-${period.startDate}-${period.endDate}.json`, {
      project_id: projectId,
      period,
      exported_at: new Date().toISOString(),
      summary,
      article_metrics: articleMetrics,
    })
  }

  function handleExportPdf() {
    if (!summary) return
    printReport('Ideas Studio - Analytics', period.label, [
      {
        title: 'Synthèse',
        rows: [
          ['Projet', projectId ?? '—'],
          ['Période', `${period.startDate} → ${period.endDate}`],
          ['Pages vues', formatMetric(summary.total_views)],
          ['Pages uniques', formatMetric(summary.unique_pages)],
          ['Articles suivis', String(articleMetrics.length)],
          ['Score SEO moyen', avgSeoScore !== null ? `${avgSeoScore}%` : '—'],
        ],
      },
      {
        title: 'Top articles',
        rows: articleMetrics.slice(0, 10).map((a) => [a.title, `${formatMetric(a.views)} vues`]),
      },
      {
        title: 'Sources',
        rows: sources.slice(0, 10).map((s) => [s.label, `${formatMetric(s.visits)} · ${s.share}%`]),
      },
    ])
  }

  if (loadStatus === 'loading') return <LoadingState />
  if (loadStatus === 'error' || !summary) return <ErrorState onRetry={() => setTick((t) => t + 1)} />

  const topArticles = [...articleMetrics].sort((a, b) => b.views - a.views).slice(0, 8)

  return (
    <div className="project-page project-page--wide">
      {/* Header */}
      <div className="project-page-header">
        <div>
          <h1 className="text-[20px] font-semibold tracking-tight text-primary">Analytics</h1>
          <p className="mt-0.5 text-[13px] text-secondary">Performance éditoriale et trafic du projet.</p>
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
        {/* Section 1 — 4 KPIs */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard icon={<Eye size={18} />} value={formatMetric(summary.total_views)} label="Vues totales" tone="accent" />
          <MetricCard icon={<Users size={18} />} value={formatMetric(summary.unique_pages)} label="Pages uniques" tone="success" />
          <MetricCard icon={<BarChart3 size={18} />} value={String(articleMetrics.length)} label="Articles suivis" tone="warning" />
          <MetricCard
            icon={<TrendingUp size={18} />}
            value={avgSeoScore !== null ? `${avgSeoScore}` : '—'}
            label="Score SEO moyen"
            tone="violet"
          />
        </div>

        {/* Section 2 — Évolution des vues */}
        <Card>
          <SectionTitle>Évolution du trafic par canal</SectionTitle>
          <div className="relative h-[220px]">
            <ResponsiveContainer width="100%" height="100%" debounce={100}>
              <LineChart data={channelTrend} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#86868b' }} tickLine={false} axisLine={false} tickFormatter={(v) => chartTick(period.mode, v)} interval="preserveStartEnd" />
                <YAxis tick={{ fontSize: 11, fill: '#86868b' }} tickLine={false} axisLine={false} width={40} allowDecimals={false} tickFormatter={formatAxisTick} />
                <Tooltip cursor={false} contentStyle={{ fontSize: 12, borderRadius: 10, border: '1px solid rgba(0,0,0,0.08)', boxShadow: 'none' }} formatter={(v) => [formatMetric(Number(v)), 'Visites']} />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
                <Line type="monotone" dataKey="organic" name="Google" stroke="#34c759" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
                <Line type="monotone" dataKey="direct" name="Direct" stroke="#007aff" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
                <Line type="monotone" dataKey="social" name="Social" stroke="#5856d6" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
                <Line type="monotone" dataKey="referral" name="Referral" stroke="#ff9500" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
            {!hasChannelTrend && <ChartEmpty message="Aucune donnée de trafic pour cette période." />}
          </div>
        </Card>

        {/* Section 3 — Top articles */}
        <Card>
          <SectionTitle>Top articles</SectionTitle>
          {topArticles.length === 0 ? (
            <InlineEmpty>Aucun article suivi pour cette période.</InlineEmpty>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[520px]">
                <thead>
                  <tr className="border-b border-border text-[11px] font-medium uppercase tracking-wide text-tertiary">
                    <th className="px-3 pb-2 text-left font-medium">Titre</th>
                    <th className="px-3 pb-2 text-right font-medium tabular-nums">Vues</th>
                    <th className="px-3 pb-2 text-right font-medium">Variation</th>
                    <th className="px-3 pb-2 text-right font-medium">Score SEO</th>
                  </tr>
                </thead>
                <tbody>
                  {topArticles.map((a) => (
                    <tr
                      key={a.article_id}
                      className="group border-b border-[#f0f0f0] text-[13px] transition-colors hover:bg-[#fafafa] last:border-0"
                    >
                      <td className="py-2.5 px-3">
                        <button
                          type="button"
                          onClick={() => navigate(`/projects/${projectId}/articles/${a.article_id}/edit`)}
                          className="truncate text-left font-medium text-primary hover:text-accent max-w-[280px] block"
                        >
                          {a.title}
                        </button>
                      </td>
                      <td className="py-2.5 px-3 text-right tabular-nums text-secondary">{formatMetric(a.views)}</td>
                      <td className="py-2.5 px-3 text-right">
                        {a.variation !== null ? (
                          <span className={`inline-flex items-center gap-0.5 text-[12px] font-medium ${a.variation >= 0 ? 'text-success' : 'text-danger'}`}>
                            {a.variation >= 0 ? '+' : ''}{a.variation}%
                          </span>
                        ) : <span className="text-tertiary">—</span>}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        {a.seo_score !== null ? (
                          <span className={`text-[12px] font-medium tabular-nums ${a.seo_score >= 80 ? 'text-success' : a.seo_score >= 60 ? 'text-warning' : 'text-danger'}`}>
                            {a.seo_score}
                          </span>
                        ) : <span className="text-tertiary">—</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        {/* Section 4 — Sources de trafic */}
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <SectionTitle>Sources de trafic</SectionTitle>
            <div className="flex flex-col gap-1">
              {sources.length ? sources.slice(0, 8).map((s, i) => (
                <VisualRow
                  key={s.key}
                  rank={i + 1}
                  label={s.label}
                  value={s.visits}
                  total={totalVisits}
                  leading={<SourceMark referrer={s.raw} />}
                  meta={<span>{s.channel} · {s.share}% du trafic</span>}
                />
              )) : <InlineEmpty>Aucune source disponible pour cette période.</InlineEmpty>}
            </div>
          </Card>
          <Card>
            <SectionTitle>Canaux</SectionTitle>
            <div className="flex flex-col gap-1">
              {(() => {
                const channels = ['Organic Search', 'Direct', 'Social', 'Referral'].map((ch) => ({
                  channel: ch,
                  visits: sources.filter((s) => s.channel === ch).reduce((sum, s) => sum + s.visits, 0),
                })).filter((ch) => ch.visits > 0).sort((a, b) => b.visits - a.visits)
                return channels.length ? channels.map((ch) => (
                  <VisualRow
                    key={ch.channel}
                    label={ch.channel}
                    value={ch.visits}
                    total={totalVisits}
                    leading={
                      ch.channel === 'Organic Search' ? <Globe size={15} /> :
                      ch.channel === 'Direct' ? <MousePointer2 size={15} /> :
                      ch.channel === 'Social' ? <Users size={15} /> :
                      <ExternalLink size={15} />
                    }
                  />
                )) : <InlineEmpty>Aucun canal disponible pour cette période.</InlineEmpty>
              })()}
            </div>
          </Card>
        </div>

        {/* Section 5 — Articles à optimiser */}
        {toOptimize.length > 0 && (
          <Card>
            <SectionTitle>Articles à optimiser (SEO &lt; 70)</SectionTitle>
            <div className="flex flex-col">
              {toOptimize.map((a) => (
                <div
                  key={a.article_id}
                  className="group flex items-center justify-between gap-3 border-b border-[#f0f0f0] px-2 py-2.5 transition-colors hover:bg-[#fafafa] last:border-0"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <AlertTriangle size={14} className="shrink-0 text-warning" />
                    <span className="truncate text-[13px] font-medium text-primary">{a.title}</span>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className={`text-[12px] font-medium tabular-nums ${a.seo_score !== null && a.seo_score < 60 ? 'text-danger' : 'text-warning'}`}>
                      SEO {a.seo_score ?? '—'}
                    </span>
                    <button
                      type="button"
                      onClick={() => navigate(`/projects/${projectId}/articles/${a.article_id}/edit`)}
                      className="flex h-6 w-6 items-center justify-center rounded-[8px] text-tertiary opacity-0 transition-opacity hover:text-primary group-hover:opacity-100"
                    >
                      <ExternalLink size={12} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Country + devices */}
        <div className="grid gap-4 sm:grid-cols-2">
          <Card>
            <SectionTitle>Pays</SectionTitle>
            {summary.countries.length ? summary.countries.slice(0, 8).map((c, i) => (
              <VisualRow
                key={c.country}
                rank={i + 1}
                label={getCountryDisplay(c.country).label}
                value={c.views}
                total={summary.total_views}
                leading={<span className="text-[15px] leading-none">{getCountryDisplay(c.country).flag}</span>}
              />
            )) : <InlineEmpty>Aucune donnée pays pour cette période.</InlineEmpty>}
          </Card>
          <Card>
            <SectionTitle>Appareils</SectionTitle>
            {summary.devices.length ? summary.devices.map((d, i) => (
              <VisualRow
                key={d.device}
                rank={i + 1}
                label={getDeviceLabel(d.device)}
                value={d.views}
                total={summary.total_views}
                leading={<DeviceIcon device={d.device} />}
              />
            )) : <InlineEmpty>Aucune donnée appareil pour cette période.</InlineEmpty>}
          </Card>
        </div>
      </div>
    </div>
  )
}
