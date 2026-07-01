import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  BarChart, Bar, Cell,
  XAxis, YAxis,
  CartesianGrid,
} from 'recharts'
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
  type ChartConfig,
} from '@/components/ui/chart'
import {
  RefreshCw,
  AlertTriangle,
  Eye,
} from '@/components/ui/hugeIcons'
import { SeoRadialCard, AreaMetricCard, SimpleMetricCard } from '@/components/charts/TrendCards'
import { getPerformanceSummary, getArticlesPerformance } from '@/api/performance'
import type { ArticlePerformanceBrief, PerformanceSummary } from '@/types'
import { Card } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import ErrorState from '@/components/ui/ErrorState'
import LoadingState from '@/components/ui/LoadingState'
import PeriodNavigator, { ExportButtons } from '@/components/ui/PeriodNavigator'
import { downloadJson, printReport } from '@/utils/exportReport'
import { currentPeriod, type PeriodRange } from '@/utils/periodNavigator'
import { getPeriodBarLayout, getPeriodBucketKey, getPeriodBuckets } from '@/utils/periodChart'
import {
  formatAxisTick,
  formatMetric,
  getCountryDisplay,
  getDeviceLabel,
  getSourceDisplay,
  getSourceChannel,
} from '@/utils/trafficDisplay'
import { NEUTRAL_CHART_COLORS, SEMANTIC_COLORS, COUNTRY_PALETTE as SHARED_COUNTRY_PALETTE, DEVICE_COLORS, scoreColor } from '@/utils/chartPalette'

// ── Types ────────────────────────────────────────────────────────────────────

type AuditItem = {
  id: string
  article_id: string
  title: string
  reason: string
  priority: 'high' | 'medium' | 'info'
  seo_score: number | null
  views: number
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <p className="mb-3 text-[12px] font-semibold uppercase tracking-wide text-secondary">{children}</p>
}

function InlineEmpty({ children }: { children: React.ReactNode }) {
  return <p className="rounded-[12px] border-2 border-border bg-transparent px-3 py-3 text-[14px] text-secondary">{children}</p>
}

function ChartEmpty({ message }: { message: string }) {
  return (
    <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
      <span className="rounded-[10px] border border-border bg-surface px-3 py-2 text-[12px] text-secondary">{message}</span>
    </div>
  )
}

function deviceColor(device: string) {
  return (DEVICE_COLORS as Record<string, string>)[device.toLowerCase()] ?? NEUTRAL_CHART_COLORS.tertiary
}

function emptyTrend(period: PeriodRange, maxPoints = 30): number {
  if (period.mode === 'day') return Math.min(24, maxPoints)
  if (period.mode === 'week') return Math.min(7, maxPoints)
  if (period.mode === 'month') {
    const days = Math.ceil((new Date(period.endDate).getTime() - new Date(period.startDate).getTime()) / 86400000) + 1
    return Math.min(Math.max(1, days), maxPoints)
  }
  return Math.min(12, maxPoints)
}

function articleSignal(a: ArticlePerformanceBrief) {
  if (a.views === 0 && a.seo_score === null) return { label: 'Nouveau', color: 'text-tertiary' }
  if (a.seo_score !== null && a.seo_score < 60) return { label: 'À optimiser', color: 'text-danger' }
  if (a.variation !== null && a.variation < -10) return { label: 'En baisse', color: 'text-danger' }
  if (a.seo_score !== null && a.seo_score < 70) return { label: 'À optimiser', color: 'text-warning' }
  if (a.seo_score !== null && a.seo_score < 80) return { label: 'À surveiller', color: 'text-warning' }
  if (a.views === 0) return { label: 'Nouveau', color: 'text-tertiary' }
  return { label: 'Performant', color: 'text-success' }
}

// ── Constants ────────────────────────────────────────────────────────────────

const COUNTRY_PALETTE = SHARED_COUNTRY_PALETTE
const TRAFFIC_CHANNELS = [
  { key: 'direct', label: 'Direct', color: NEUTRAL_CHART_COLORS.primary },
  { key: 'organic', label: 'Google', color: NEUTRAL_CHART_COLORS.secondary },
  { key: 'referral', label: 'Referral', color: NEUTRAL_CHART_COLORS.tertiary },
  { key: 'social', label: 'Social', color: NEUTRAL_CHART_COLORS.muted },
] as const
const DEVICE_ORDER = ['desktop', 'mobile', 'tablet']
const PRIORITY_RANK: Record<string, number> = { high: 0, medium: 1, info: 2 }

const trafficOriginConfig = {
  views: {
    label: "Vues",
    color: NEUTRAL_CHART_COLORS.secondary,
  },
  label: {
    color: "var(--background)",
  },
} satisfies ChartConfig

const trafficChartConfig = {
  direct: { label: "Direct", color: NEUTRAL_CHART_COLORS.primary },
  organic: { label: "Google", color: NEUTRAL_CHART_COLORS.secondary },
  referral: { label: "Referral", color: NEUTRAL_CHART_COLORS.tertiary },
  social: { label: "Social", color: NEUTRAL_CHART_COLORS.muted },
} satisfies ChartConfig

const countryChartConfig = {
  views: { label: "Vues", color: NEUTRAL_CHART_COLORS.secondary },
} satisfies ChartConfig

const deviceChartConfig = {
  desktop: { label: "Desktop", color: DEVICE_COLORS.desktop },
  mobile: { label: "Mobile", color: DEVICE_COLORS.mobile },
  tablet: { label: "Tablette", color: DEVICE_COLORS.tablet },
} satisfies ChartConfig

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
    queueMicrotask(() => {
      if (!cancelled) setLoadStatus('loading')
    })
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

  // ── Derived data (useMemo) ─────────────────────────────────────────────────

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
        visits: r.views,
        share: Math.round((r.views / totalVisits) * 100),
      }
    }).sort((a, b) => b.visits - a.visits)
  }, [summary])

  const channelTrend = useMemo(() => {
    const buckets = getPeriodBuckets(period)
    const rows = buckets.map((bucket) => ({
      date: bucket.label,
      direct: 0,
      organic: 0,
      referral: 0,
      social: 0,
    }))
    const byKey = new Map(buckets.map((bucket, index) => [bucket.key, rows[index]]))

    for (const point of summary?.channel_trend_by_day ?? []) {
      const key = getPeriodBucketKey(point.date, period)
      const row = key ? byKey.get(key) : null
      if (!row) continue
      row.direct += point.direct
      row.organic += point.organic
      row.referral += point.referral
      row.social += point.social
    }

    return rows
  }, [period, summary])

  const hasChannelTrend = useMemo(
    () => channelTrend.some((point) => point.direct + point.organic + point.referral + point.social > 0),
    [channelTrend],
  )

  const channelBarLayout = useMemo(
    () => getPeriodBarLayout(channelTrend.length),
    [channelTrend.length],
  )

  const viewsTrend = useMemo(
    () => {
      const raw = summary?.trend_by_day
      if (raw && raw.length > 0) return raw.map((d) => ({ v: d.views }))
      const count = emptyTrend(period)
      return Array.from({ length: count }, () => ({ v: 0 }))
    },
    [summary, period],
  )

  const viewsChange = useMemo(() => {
    const points = summary?.trend_by_day ?? []
    if (points.length < 2) return null
    const diff = points[points.length - 1].views - points[points.length - 2].views
    return diff >= 0 ? `+${formatMetric(diff)}` : `-${formatMetric(Math.abs(diff))}`
  }, [summary])

  const avgSeoScore = useMemo(() => {
    const withScore = articleMetrics.filter((a) => a.seo_score !== null)
    if (withScore.length === 0) return null
    return Math.round(withScore.reduce((sum, a) => sum + (a.seo_score ?? 0), 0) / withScore.length)
  }, [articleMetrics])

  const seoTrend = useMemo(
    () => {
      const withScore = articleMetrics.filter((a) => a.seo_score !== null)
      if (withScore.length === 0) {
        const count = emptyTrend(period)
        return Array.from({ length: count }, () => ({ v: 0 }))
      }
      return withScore
        .sort((a, b) => (a.published_at ?? '').localeCompare(b.published_at ?? ''))
        .map((a) => ({ v: a.seo_score ?? 0 }))
    },
    [articleMetrics, period],
  )

  const seoChangePts = useMemo(() => {
    if (seoTrend.length < 2) return 0
    return seoTrend[seoTrend.length - 1].v - seoTrend[seoTrend.length - 2].v
  }, [seoTrend])

  const optimizeCount = useMemo(
    () => articleMetrics.filter((a) => (a.seo_score ?? 100) < 70).length,
    [articleMetrics],
  )

  const topArticles = useMemo(
    () => [...articleMetrics].sort((a, b) => b.views - a.views).slice(0, 8),
    [articleMetrics],
  )

  const countryChartData = useMemo(
    () => (summary?.countries ?? []).slice(0, 8).map((country, i) => {
      const display = getCountryDisplay(country.country)
      return {
        key: country.country,
        flag: display.flag,
        label: display.label,
        views: country.views,
        fill: COUNTRY_PALETTE[i % COUNTRY_PALETTE.length],
      }
    }),
    [summary],
  )

  const devicePeriodData = useMemo(() => {
    const trend = summary?.trend_by_day ?? []
    const devices = summary?.devices ?? []
    if (!trend.length || !devices.length) return []
    const totalViews = Math.max(1, devices.reduce((sum, d) => sum + d.views, 0))
    const shares = devices.map((d) => ({ key: d.device.toLowerCase(), share: d.views / totalViews }))
    const buckets = getPeriodBuckets(period)
    const totals = new Map(buckets.map((bucket) => [bucket.key, 0]))
    for (const point of trend) {
      const key = getPeriodBucketKey(point.date, period)
      if (!key || !totals.has(key)) continue
      totals.set(key, (totals.get(key) ?? 0) + point.views)
    }

    return buckets.map((bucket) => {
      const total = totals.get(bucket.key) ?? 0
      const entry: Record<string, string | number> = { date: bucket.label }
      for (const { key, share } of shares) {
        entry[key] = Math.round(total * share)
      }
      return entry
    })
  }, [period, summary])

  const deviceKeys = useMemo(() => {
    const keys = new Set<string>()
    for (const row of devicePeriodData) {
      Object.keys(row).forEach((key) => {
        if (key !== 'date') keys.add(key)
      })
    }
    return [
      ...DEVICE_ORDER.filter((key) => keys.has(key)),
      ...Array.from(keys).filter((key) => !DEVICE_ORDER.includes(key)),
    ]
  }, [devicePeriodData])

  const deviceBarLayout = useMemo(
    () => getPeriodBarLayout(devicePeriodData.length),
    [devicePeriodData.length],
  )

  const auditItems = useMemo(() => {
    const withMetrics = articleMetrics.filter((a) => a.views > 0 || a.seo_score !== null)
    if (withMetrics.length === 0) return []
    const sortedByViews = [...withMetrics].sort((a, b) => a.views - b.views)
    const medianViews = sortedByViews.length > 0
      ? sortedByViews[Math.floor(sortedByViews.length / 2)].views
      : 0

    const scored = withMetrics.map((a): AuditItem | null => {
      let priority: 'high' | 'medium' | 'info' = 'info'
      let reason = ''

      if (a.seo_score !== null && a.seo_score < 60) {
        priority = 'high'
        reason = 'Score SEO critique'
      } else if (a.seo_score !== null && a.seo_score < 70) {
        priority = 'medium'
        reason = 'Score SEO insuffisant'
      } else if (a.variation !== null && a.variation < -15) {
        priority = 'medium'
        reason = 'Trafic en baisse'
      } else if (a.views === 0) {
        priority = 'info'
        reason = 'Aucun trafic détecté'
      } else if (a.views >= medianViews && a.seo_score !== null && a.seo_score < 80) {
        priority = 'high'
        reason = 'Fort potentiel SEO'
      }

      if (!reason) return null

      return {
        id: a.article_id,
        article_id: a.article_id,
        title: a.title,
        reason,
        priority,
        seo_score: a.seo_score,
        views: a.views,
      }
    }).filter((item): item is AuditItem => item !== null)

    return scored.sort((a, b) => PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority]).slice(0, 5)
  }, [articleMetrics])

  const sourceChannels = useMemo(() => {
    if (!summary?.referrers?.length) return []
    const map = new Map<string, number>()
    for (const ref of summary.referrers) {
      const channel = getSourceChannel(ref.referrer)
      map.set(channel, (map.get(channel) ?? 0) + ref.views)
    }
    const total = Math.max(1, Array.from(map.values()).reduce((s, v) => s + v, 0))
    return Array.from(map.entries())
      .map(([channel, views]) => ({
        channel,
        label: TRAFFIC_CHANNELS.find((item) => item.key === channel)?.label ?? channel,
        views,
        share: Math.round((views / total) * 100),
      }))
      .sort((a, b) => b.views - a.views)
      .slice(0, 4)
  }, [summary])

  // ── Export handlers ──────────────────────────────────────────────────────

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

  // ── Loading / Error states ───────────────────────────────────────────────

  if (loadStatus === 'loading') return <LoadingState />
  if (loadStatus === 'error' || !summary) return <ErrorState onRetry={() => setTick((t) => t + 1)} />

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="project-page project-page--wide">
      {/* Header */}
      <div className="project-page-header">
        <div>
          <h1 className="text-[20px] font-semibold tracking-tight text-primary">Analytics</h1>
          <p className="mt-0.5 text-[14px] text-secondary">Performance éditoriale et trafic du projet.</p>
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
        {/* Section 1 — 5 KPIs uniformes */}
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-5">
          <AreaMetricCard
            title="Vues totales"
            value={formatMetric(summary.total_views)}
            change={viewsChange ?? '—'}
            changeColor={viewsChange?.startsWith('-') ? SEMANTIC_COLORS.danger : NEUTRAL_CHART_COLORS.primary}
            color={NEUTRAL_CHART_COLORS.primary}
            data={viewsTrend}
          />
          <SeoRadialCard
            title="Score SEO moyen"
            score={avgSeoScore ?? 0}
            changePts={seoChangePts}
            data={seoTrend}
          />
          <SimpleMetricCard
            title="Pages uniques"
            value={formatMetric(summary.unique_pages)}
            change="—"
            description={`${Math.round(summary.unique_pages / Math.max(1, summary.total_views) * 100)} % des vues`}
          />
          <SimpleMetricCard
            title="Articles suivis"
            value={String(articleMetrics.length)}
            change="—"
          />
          <SimpleMetricCard
            title="Articles à optimiser"
            value={String(optimizeCount)}
            change="—"
            description={articleMetrics.length > 0 ? `${Math.round(optimizeCount / articleMetrics.length * 100)} % des articles` : undefined}
          />
        </div>

        {/* Section 2 — Évolution du trafic par canal */}
        <Card>
          <SectionTitle>Évolution du trafic par canal</SectionTitle>
          <div className="relative h-[250px]">
            <div className={`flex h-[250px] ${channelBarLayout.centered ? 'justify-center' : ''}`}>
              <div className="h-full" style={{ width: channelBarLayout.chartWidth }}>
                <ChartContainer config={trafficChartConfig} className="h-full w-full">
                  <BarChart data={channelTrend} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
                    <CartesianGrid vertical={false} />
                    <XAxis
                      dataKey="date"
                      tickLine={false}
                      axisLine={false}
                      tickMargin={8}
                      interval={0}
                    />
                    <YAxis tickLine={false} axisLine={false} width={36} allowDecimals={false} tickFormatter={formatAxisTick} />
                    <ChartTooltip
                      cursor={false}
                      content={
                        <ChartTooltipContent
                          indicator="dot"
                          formatter={(value: number | string, name: string) => {
                            const num = Number(value)
                            if (num <= 0) return <span />
                            return [
                              <span key="value" className="tabular-nums text-primary">{formatMetric(num)}</span>,
                              name as string,
                            ]
                          }}
                        />
                      }
                    />
                    <ChartLegend content={<ChartLegendContent />} />
                    {TRAFFIC_CHANNELS.map((channel, index) => (
                      <Bar
                        key={channel.key}
                        dataKey={channel.key}
                        name={channel.label}
                        stackId="a"
                        fill={channel.color}
                        barSize={channelBarLayout.barSize}
                        radius={
                          index === TRAFFIC_CHANNELS.length - 1 ? [4, 4, 0, 0]
                          : index === 0 ? [0, 0, 4, 4]
                          : [0, 0, 0, 0]
                        }
                        isAnimationActive
                      />
                    ))}
                  </BarChart>
                </ChartContainer>
              </div>
            </div>
            {!hasChannelTrend && <ChartEmpty message="Aucune donnée de trafic pour cette période." />}
          </div>
        </Card>

        {/* Section 3 — À auditer maintenant */}
        {auditItems.length > 0 && (
          <Card>
            <SectionTitle>À auditer maintenant</SectionTitle>
            <div className="flex flex-col">
              {auditItems.map((item) => (
                <div
                  key={item.id}
                  className="group flex items-center justify-between gap-3 border-b border-border/30 px-2 py-3 transition-colors hover:bg-surface-soft last:border-0"
                >
                  <div className="flex items-start gap-3 min-w-0 flex-1">
                    <span className={`mt-0.5 shrink-0 ${
                      item.priority === 'high' ? 'text-danger'
                      : item.priority === 'medium' ? 'text-warning'
                      : 'text-tertiary'
                    }`}>
                      <AlertTriangle size={14} />
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-[14px] font-medium text-primary">{item.title}</p>
                      <p className="mt-0.5 text-[12px] text-secondary">
                        {item.reason}
                        {item.seo_score !== null && (
                          <span className="ml-2 inline-flex items-center gap-1">
                            <span
                              className="inline-block h-2 w-2 rounded-full"
                              style={{ backgroundColor: scoreColor(item.seo_score) }}
                            />
                            SEO {item.seo_score}
                          </span>
                        )}
                        {item.views > 0 && (
                          <span className="ml-2">· {formatMetric(item.views)} vues</span>
                        )}
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => navigate(`/projects/${projectId}/articles/${item.article_id}/edit`)}
                    className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[8px] text-tertiary opacity-0 transition-all hover:text-primary group-hover:opacity-100"
                    title="Éditer l'article"
                  >
                    <Eye size={13} />
                  </button>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Section 4 — Top articles avec diagnostic */}
        <Card>
          <SectionTitle>Top articles</SectionTitle>
          {topArticles.length === 0 ? (
            <InlineEmpty>Aucun article suivi pour cette période.</InlineEmpty>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[700px]">
                <thead>
                  <tr className="border-b border-border text-[12px] font-medium uppercase tracking-wide text-tertiary">
                    <th className="px-3 pb-2 text-left font-medium">Article</th>
                    <th className="px-3 pb-2 text-right font-medium tabular-nums">Vues</th>
                    <th className="px-3 pb-2 text-right font-medium">Variation</th>
                    <th className="px-3 pb-2 text-right font-medium">Score SEO</th>
                    <th className="px-3 pb-2 text-left font-medium">Signal</th>
                    <th className="px-3 pb-2 text-center font-medium">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {topArticles.map((a) => {
                    const signal = articleSignal(a)
                    return (
                      <tr
                        key={a.article_id}
                        className="group border-b border-border/30 text-[14px] transition-colors hover:bg-surface-soft last:border-0"
                      >
                        <td className="py-2.5 px-3">
                          <button
                            type="button"
                            onClick={() => navigate(`/projects/${projectId}/articles/${a.article_id}/edit`)}
                            className="truncate text-left font-medium text-primary hover:text-secondary max-w-[220px] block"
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
                        <td className="py-2.5 px-3">
                          {a.seo_score !== null ? (
                            <span className="flex items-center justify-end gap-2">
                              <span className="w-6 shrink-0 text-right text-[12px] font-semibold tabular-nums text-primary">{a.seo_score}</span>
                              <span className="h-[6px] w-[60px] shrink-0 overflow-hidden rounded-full bg-surface-muted">
                                <span
                                  className="block h-full rounded-full transition-all"
                                  style={{
                                    width: `${Math.min(a.seo_score, 100)}%`,
                                    backgroundColor: scoreColor(a.seo_score),
                                  }}
                                />
                              </span>
                            </span>
                          ) : <span className="block text-right text-tertiary">—</span>}
                        </td>
                        <td className="py-2.5 px-3">
                          <span className={`text-[12px] font-medium ${signal.color}`}>{signal.label}</span>
                        </td>
                        <td className="py-2.5 px-3 text-center">
                          <button
                            type="button"
                            onClick={() => navigate(`/projects/${projectId}/articles/${a.article_id}/edit`)}
                            className="flex h-6 w-6 items-center justify-center rounded-[6px] border border-border text-tertiary transition-colors hover:border-border/50 hover:text-primary mx-auto"
                            title="Éditer l'article"
                          >
                            <Eye size={12} />
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        {/* Section 5 — Origine du trafic */}
        <Card>
          <SectionTitle>Origine du trafic</SectionTitle>
          {sourceChannels.length === 0 ? (
            <InlineEmpty>Aucune donnée de provenance pour cette période.</InlineEmpty>
          ) : (
            <div className="h-[140px]">
              <ChartContainer config={trafficOriginConfig} className="h-full w-full">
                <BarChart
                  accessibilityLayer
                  data={sourceChannels}
                  layout="vertical"
                    margin={{ left: 0 }}
                >
                  <XAxis type="number" dataKey="views" hide />
                  <YAxis
                    dataKey="label"
                    type="category"
                    tickLine={false}
                    tickMargin={8}
                    axisLine={false}
                    width={80}
                    tick={{ fontSize: 12, fill: '#5E5E5E', fontWeight: 500 }}
                  />
                  <ChartTooltip
                    cursor={false}
                    content={<ChartTooltipContent hideLabel />}
                  />
                  <Bar dataKey="views" fill="var(--color-views)" radius={5} barSize={24} />
                </BarChart>
              </ChartContainer>
            </div>
          )}
        </Card>

        {/* Section 6 — Pays + Appareils */}
        <div className="grid gap-4 sm:grid-cols-2">
          <Card>
            <SectionTitle>Pays</SectionTitle>
            {countryChartData.length ? (
              <div className="h-[220px]">
                <ChartContainer config={countryChartConfig} className="h-full w-full">
                  <BarChart
                    data={countryChartData}
                    layout="vertical"
                    margin={{ top: 2, right: 12, bottom: 2, left: 0 }}
                  >
                    <YAxis dataKey="flag" type="category" tickLine={false} axisLine={false} tickMargin={6} width={28} tick={{ fontSize: 16 }} />
                    <XAxis type="number" hide />
                    <ChartTooltip
                      cursor={false}
                      content={
                        <ChartTooltipContent
                          indicator="line"
                          hideLabel
                          formatter={(value: number | string, _name: string, entry: { payload?: { label?: string } }) => {
                            const label = entry.payload?.label ?? 'Pays'
                            return (
                              <div className="flex min-w-[120px] items-center justify-between gap-3">
                                <span className="text-secondary">{label}</span>
                                <span className="tabular-nums text-primary">{formatMetric(Number(value))}</span>
                              </div>
                            )
                          }}
                        />
                      }
                    />
                    <Bar dataKey="views" radius={5} barSize={14}>
                      {countryChartData.map((country) => (
                        <Cell key={country.key} fill={country.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ChartContainer>
              </div>
            ) : <InlineEmpty>Aucune donnée pays pour cette période.</InlineEmpty>}
          </Card>
          <Card>
            <SectionTitle>Appareils</SectionTitle>
            {devicePeriodData.length ? (
              <div className="h-[220px]">
                <div className={`flex h-full ${deviceBarLayout.centered ? 'justify-center' : ''}`}>
                  <div className="h-full" style={{ width: deviceBarLayout.chartWidth }}>
                    <ChartContainer config={deviceChartConfig} className="h-full w-full">
                      <BarChart data={devicePeriodData} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
                        <CartesianGrid vertical={false} />
                        <XAxis dataKey="date" tickLine={false} axisLine={false} tickMargin={8} interval={0} />
                        <YAxis tickLine={false} axisLine={false} width={36} allowDecimals={false} tickFormatter={formatAxisTick} />
                        <ChartTooltip cursor={false} content={<ChartTooltipContent indicator="dot" />} />
                        <ChartLegend content={<ChartLegendContent />} />
                        {deviceKeys.map((device, i) => (
                          <Bar
                            key={device}
                            dataKey={device}
                            name={getDeviceLabel(device)}
                            stackId="a"
                            fill={deviceColor(device)}
                            barSize={deviceBarLayout.barSize}
                            radius={
                              i === deviceKeys.length - 1 ? [4, 4, 0, 0]
                              : i === 0 ? [0, 0, 4, 4]
                              : [0, 0, 0, 0]
                            }
                            isAnimationActive
                          />
                        ))}
                      </BarChart>
                    </ChartContainer>
                  </div>
                </div>
              </div>
            ) : <InlineEmpty>Aucune donnée appareil pour cette période.</InlineEmpty>}
          </Card>
        </div>
      </div>
    </div>
  )
}
