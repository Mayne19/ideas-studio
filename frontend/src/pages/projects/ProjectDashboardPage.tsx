import { useEffect, useState } from 'react'
import { Bar, BarChart, Line, LineChart, ResponsiveContainer } from 'recharts'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Lightbulb, Globe,
  ArrowRight, AlertCircle, Clock,
  Edit3, Eye, Send, Star, ClipboardList, HelpCircle,
  ShieldCheck,
} from '@/components/ui/hugeIcons'
import { useProject } from '@/context/ProjectContext'
import { useAuth } from '@/context/AuthContext'
import { listArticles } from '@/api/articles'
import { listCategories } from '@/api/categories'
import { getPerformanceSummary } from '@/api/performance'
import { listRecommendations } from '@/api/recommendations'
import { getPipelineLogs, getPipelineSettings } from '@/api/pipeline'
import { listAIProviders } from '@/api/aiProviders'
import type { Article, Category, OptimizationRecommendation } from '@/types'
import type { PipelineLog, PipelineSettings } from '@/api/pipeline'
import type { AIProviderPublic } from '@/api/aiProviders'
import { Card } from '@/components/ui/Card'
import StatusBadge from '@/components/ui/StatusBadge'
import LoadingState from '@/components/ui/LoadingState'
import { formatDate } from '@/utils/format'
import { getGeoScore } from '@/lib/scoreBadge'
import { SeoRadialCard, AreaMetricCard, type MonthPoint } from '@/components/charts/TrendCards'
import { NEUTRAL_CHART_COLORS } from '@/utils/chartPalette'

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const days = Math.floor(diff / 86400000)
  if (days === 0) return "Aujourd'hui"
  if (days === 1) return 'Hier'
  if (days < 7) return `Il y a ${days} j`
  if (days < 30) return `Il y a ${Math.floor(days / 7)} sem.`
  return formatDate(iso)
}

const RECENT_ARTICLES_LIMIT = 6

type ActivityEvent = {
  id: string
  icon: React.ReactNode
  label: string
  articleTitle: string
  time: string
  href: string
}

const MONTHLY_METRIC_POINTS = 12
const WEEKLY_METRIC_POINTS = 52

type DashboardData = {
  recentArticles: Article[]
  activityArticles: Article[]
  categories: Category[]
  publishedCount: number
  inProgressCount: number
  ideasCount: number
  reviewNeededCount: number
  readyCount: number
  scheduledCount: number
  failedCount: number
  aiValidatedCount: number
  ideasReadyForProductionCount: number
  activeProductionCount: number
  pendingRecs: OptimizationRecommendation[]
  totalViews: number | null
  avgSeoScore: number | null
  avgGeoScore: number | null
  avgReadingTime: number | null
  seoMonthly: MonthPoint[]
  geoMonthly: MonthPoint[]
  viewsMonthly: MonthPoint[]
  timeMonthly: MonthPoint[]
  publishedMonthly: MonthPoint[]
  seoChangePts: number
  geoChangePts: number
  timeChangeMins: number
  publishedChangePct: number
}

const IN_PROGRESS_STATUSES = new Set<Article['status']>([
  'draft',
  'outline_ready',
  'writing_requested',
  'writing_in_progress',
  'draft_ready',
  'review_needed',
  'correction_needed',
  'ready_to_publish',
  'scheduled',
  'update_recommended',
])

const PRODUCTION_STATUSES = new Set<Article['status']>([
  'outline_ready',
  'writing_requested',
  'writing_in_progress',
  'draft_ready',
  'review_needed',
  'correction_needed',
])

function isAiGeneratedArticle(article: Article) {
  const source = (article.proposal_source ?? '').toLowerCase()
  return Boolean(
    article.generation_report_json ||
    article.workflow_run_id ||
    article.agent_outputs_json ||
    article.production_brief_json ||
    source.includes('ia') ||
    source.includes('ai') ||
    source.includes('llm'),
  )
}

function isFilledScore(score: number | null | undefined): score is number {
  return typeof score === 'number' && Number.isFinite(score)
}

function scoreOnHundred(score: number | null | undefined): number | null {
  if (!isFilledScore(score)) return null
  return Math.round(score > 10 ? score : score * 10)
}

function formatCompact(value: number | null | undefined): string {
  if (!value) return '—'
  return Intl.NumberFormat('fr-FR', { notation: 'compact', maximumFractionDigits: 1 }).format(value)
}

function getArticleDate(article: Article): string {
  return article.published_at ?? article.scheduled_at ?? article.updated_at ?? article.created_at
}

function buildMonthlyMetric(articles: Article[], getValue: (arts: Article[]) => number): MonthPoint[] {
  const now = new Date()
  let lastValue = 0
  return Array.from({ length: MONTHLY_METRIC_POINTS }, (_, i) => {
    const start = new Date(now.getFullYear(), now.getMonth() - (MONTHLY_METRIC_POINTS - 1 - i), 1)
    const end = new Date(now.getFullYear(), now.getMonth() - (MONTHLY_METRIC_POINTS - 1 - i) + 1, 1)
    const month = articles.filter((a) => { const d = new Date(getArticleDate(a)); return d >= start && d < end })
    if (month.length > 0) lastValue = getValue(month)
    return { v: lastValue }
  })
}

function buildWeeklyMetric(
  articles: Article[],
  getValue: (arts: Article[]) => number,
  options: { carryForward?: boolean } = {},
): MonthPoint[] {
  const now = new Date()
  let lastValue = 0
  const carryForward = options.carryForward ?? true
  const currentWeekStart = new Date(now)
  currentWeekStart.setHours(0, 0, 0, 0)
  currentWeekStart.setDate(currentWeekStart.getDate() - ((currentWeekStart.getDay() + 6) % 7))

  return Array.from({ length: WEEKLY_METRIC_POINTS }, (_, i) => {
    const start = new Date(currentWeekStart)
    start.setDate(currentWeekStart.getDate() - (WEEKLY_METRIC_POINTS - 1 - i) * 7)
    const end = new Date(start)
    end.setDate(start.getDate() + 7)
    const week = articles.filter((a) => { const d = new Date(getArticleDate(a)); return d >= start && d < end })
    if (week.length > 0) {
      lastValue = getValue(week)
      return { v: lastValue }
    }
    return { v: carryForward ? lastValue : 0 }
  })
}

function SparkMetricCard({
  title,
  value,
  change,
  changeColor,
  color,
  data,
}: {
  title: string
  value: string | number
  change: string
  changeColor: string
  color: string
  data: MonthPoint[]
}) {
  return (
    <article className="flex h-[148px] flex-col rounded-[10px] border-2 border-border bg-transparent px-5 py-4 shadow-none">
      <div className="flex min-w-0 items-center gap-1.5 text-[11px] font-medium leading-none text-tertiary">
        <span className="truncate whitespace-nowrap">{title}</span>
        <HelpCircle size={12} className="shrink-0 text-tertiary" />
      </div>
      <div className="mt-3 flex h-8 items-center justify-between gap-3">
        <div className="text-[22px] font-semibold leading-none text-primary">{value}</div>
        <span className="text-[12px] font-semibold leading-none tabular-nums" style={{ color: changeColor }}>{change}</span>
      </div>
      <div className="mt-2 h-[60px] -mx-1">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 6, bottom: 6, left: 6 }}>
            <Line
              type="natural"
              dataKey="v"
              stroke={color}
              strokeWidth={1.5}
              dot={{ r: 1.5, fill: color, strokeWidth: 0 }}
              activeDot={{ r: 2.5, fill: color, strokeWidth: 0 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </article>
  )
}

function BarMetricCard({
  title,
  value,
  change,
  changeColor,
  color,
  data,
}: {
  title: string
  value: string | number
  change: string
  changeColor: string
  color: string
  data: MonthPoint[]
}) {
  return (
    <article className="flex h-[148px] flex-col rounded-[10px] border-2 border-border bg-transparent px-5 py-4 shadow-none">
      <div className="flex min-w-0 items-center gap-1.5 text-[11px] font-medium leading-none text-tertiary">
        <span className="truncate whitespace-nowrap">{title}</span>
        <HelpCircle size={12} className="shrink-0 text-tertiary" />
      </div>
      <div className="mt-3 flex h-8 items-center justify-between gap-3">
        <div className="text-[22px] font-semibold leading-none text-primary">{value}</div>
        <span className="text-[12px] font-semibold leading-none tabular-nums" style={{ color: changeColor }}>{change}</span>
      </div>
      <div className="mt-2 h-[60px] -mx-1">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 6, bottom: 6, left: 6 }} barSize={5}>
            <Bar dataKey="v" fill={color} radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </article>
  )
}



function PipelineSummaryItem({
  icon,
  title,
  value,
  description,
}: {
  icon: React.ReactNode
  title: string
  value: number | string
  description: string
}) {
  return (
    <div className="flex h-[56px] min-w-0 items-center gap-2.5 px-5">
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[8px] text-secondary">{icon}</span>
      <span className="min-w-0 truncate text-[14px] font-medium text-secondary">{title}</span>
      <strong className="shrink-0 text-[18px] font-semibold leading-none tabular-nums text-primary">{value}</strong>
      <span className="min-w-0 truncate text-[11px] font-medium text-tertiary">{description}</span>
    </div>
  )
}

function deriveActivityEvents(articles: Article[], projectId: string): ActivityEvent[] {
  const events: ActivityEvent[] = []
  for (const a of articles.slice(0, 20)) {
    if (a.status === 'published') {
      events.push({
        id: `pub-${a.id}`,
        icon: <Send size={11} />,
        label: 'Article publié',
        articleTitle: a.title,
        time: timeAgo(a.published_at ?? a.updated_at),
        href: `/projects/${projectId}/articles/${a.id}/edit`,
      })
    } else if (a.status === 'scheduled') {
      events.push({
        id: `sched-${a.id}`,
        icon: <Clock size={11} />,
        label: 'Publication programmée',
        articleTitle: a.title,
        time: timeAgo(a.scheduled_at ?? a.updated_at),
        href: `/projects/${projectId}/articles/${a.id}/edit`,
      })
    } else if (a.status === 'idea_proposed' || a.status === 'idea_priority') {
      events.push({
        id: `idea-${a.id}`,
        icon: <Lightbulb size={11} />,
        label: 'Idée créée',
        articleTitle: a.title,
        time: timeAgo(a.created_at),
        href: `/projects/${projectId}/ideas`,
      })
    } else if (a.status === 'draft_ready' || a.status === 'review_needed') {
      events.push({
        id: `review-${a.id}`,
        icon: <Eye size={11} />,
        label: 'Brouillon prêt',
        articleTitle: a.title,
        time: timeAgo(a.updated_at),
        href: `/projects/${projectId}/articles/${a.id}/edit`,
      })
    } else if (a.seo_score !== null) {
      events.push({
        id: `seo-${a.id}`,
        icon: <Star size={11} />,
        label: 'Analyse SEO terminée',
        articleTitle: a.title,
        time: timeAgo(a.updated_at),
        href: `/projects/${projectId}/articles/${a.id}/edit`,
      })
    } else {
      events.push({
        id: `edit-${a.id}`,
        icon: <Edit3 size={11} />,
        label: 'Article modifié',
        articleTitle: a.title,
        time: timeAgo(a.updated_at),
        href: `/projects/${projectId}/articles/${a.id}/edit`,
      })
    }
  }
  return events
}

export default function ProjectDashboardPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const { project, loading: projectLoading } = useProject()
  const { user } = useAuth()
  const [data, setData] = useState<DashboardData | null>(null)
  const [pipeline, setPipeline] = useState<PipelineSettings | null>(null)
  const [pipelineLogs, setPipelineLogs] = useState<PipelineLog[]>([])
  const [providers, setProviders] = useState<AIProviderPublic[]>([])

  useEffect(() => {
    if (!projectId) return
    Promise.allSettled([
      listArticles(projectId, { limit: 500 }),
      listRecommendations(projectId),
      getPerformanceSummary(projectId, '30d'),
      listCategories(projectId),
      getPipelineSettings(projectId).catch(() => null),
      getPipelineLogs(projectId, 1).catch(() => []),
      listAIProviders(projectId).catch(() => []),
    ]).then(([articles, recs, perf, cats, pipelineResult, logsResult, providersResult]) => {
      if (pipelineResult.status === 'fulfilled') setPipeline(pipelineResult.value)
      if (logsResult.status === 'fulfilled') setPipelineLogs(logsResult.value)
      if (providersResult.status === 'fulfilled') setProviders(providersResult.value)
      const allArticles =
        articles.status === 'fulfilled'
          ? [...articles.value].sort((a, b) => getArticleDate(b).localeCompare(getArticleDate(a)))
          : []
      const contentRecentArticles = allArticles
        .filter((article) => !article.status.startsWith('idea_'))
        .slice(0, RECENT_ARTICLES_LIMIT)
      const recentArticles =
        contentRecentArticles.length >= RECENT_ARTICLES_LIMIT
          ? contentRecentArticles
          : [
              ...contentRecentArticles,
              ...allArticles
                .filter((article) => !contentRecentArticles.some((recent) => recent.id === article.id))
                .slice(0, RECENT_ARTICLES_LIMIT - contentRecentArticles.length),
            ]
      const activityArticles = allArticles.slice(0, 20)
      const categories = cats.status === 'fulfilled' ? cats.value : []
      const contentArticles = allArticles.filter((article) => !article.status.startsWith('idea_'))
      const publishedArticles = allArticles.filter((article) => article.status === 'published')
      const inProgressArticles = allArticles.filter((article) => IN_PROGRESS_STATUSES.has(article.status))
      const aiValidatedArticles = allArticles.filter((article) =>
        isAiGeneratedArticle(article) &&
        ['published', 'scheduled'].includes(article.status) &&
        Boolean(article.human_validated_at || article.published_at || article.scheduled_at),
      )
      const ideasReadyForProduction = allArticles.filter((article) => article.status === 'idea_priority')
      const activeProductionArticles = allArticles.filter((article) => PRODUCTION_STATUSES.has(article.status))
      const scored = contentArticles.filter((a) => a.seo_score !== null)
      const avgSeoScore = scored.length > 0
        ? scored.reduce((s, a) => s + (a.seo_score ?? 0), 0) / scored.length
        : null
      const geoScored = contentArticles.filter((a) => getGeoScore(a) !== null)
      const avgGeoScore = geoScored.length > 0
        ? geoScored.reduce((s, a) => s + (scoreOnHundred(getGeoScore(a)) ?? 0), 0) / geoScored.length
        : null
      const worded = contentArticles.filter((a) => a.word_count > 0)
      const avgReadingTime = worded.length > 0
        ? Math.ceil(worded.reduce((s, a) => s + a.word_count, 0) / worded.length / 200)
        : null

      // Monthly data (12 derniers mois)
      const seoMonthly = buildMonthlyMetric(
        scored,
        (arts) => Math.round(arts.reduce((s, a) => s + scoreOnHundred(a.seo_score)!, 0) / arts.length),
      )
      const geoMonthly = buildMonthlyMetric(
        geoScored,
        (arts) => Math.round(arts.reduce((s, a) => s + scoreOnHundred(getGeoScore(a))!, 0) / arts.length),
      )
      const timeMonthly = buildMonthlyMetric(
        worded,
        (arts) => Math.ceil(arts.reduce((s, a) => s + a.word_count, 0) / arts.length / 200),
      )
      const viewsMonthly = buildMonthlyMetric(
        contentArticles,
        (arts) => arts.length,
      )
      // Weekly data only for the published bar chart (52 dernières semaines)
      const publishedMonthly = buildWeeklyMetric(
        allArticles.filter((a) => a.status === 'published'),
        (arts) => arts.length,
        { carryForward: false },
      )
      const lastMonthIndex = MONTHLY_METRIC_POINTS - 1
      const previousMonthIndex = MONTHLY_METRIC_POINTS - 2
      const lastWeekIndex = WEEKLY_METRIC_POINTS - 1
      const previousWeekIndex = WEEKLY_METRIC_POINTS - 2
      const seoChangePts = seoMonthly[lastMonthIndex].v - seoMonthly[previousMonthIndex].v
      const geoChangePts = geoMonthly[lastMonthIndex].v - geoMonthly[previousMonthIndex].v
      const timeChangeMins = timeMonthly[lastMonthIndex].v - timeMonthly[previousMonthIndex].v
      const publishedChangePct = publishedMonthly[previousWeekIndex].v > 0
        ? Math.round(((publishedMonthly[lastWeekIndex].v - publishedMonthly[previousWeekIndex].v) / publishedMonthly[previousWeekIndex].v) * 100)
        : publishedMonthly[lastWeekIndex].v > 0 ? 100 : 0

      setData({
        recentArticles,
        activityArticles,
        categories,
        publishedCount: publishedArticles.length,
        inProgressCount: inProgressArticles.length,
        ideasCount:
          allArticles.filter((article) => article.status === 'idea_proposed' || article.status === 'idea_priority').length,
        reviewNeededCount: allArticles.filter((article) => article.status === 'review_needed').length,
        readyCount: allArticles.filter((article) => article.status === 'ready_to_publish').length,
        scheduledCount: allArticles.filter((article) => article.status === 'scheduled').length,
        failedCount: allArticles.filter((article) => article.status === 'failed').length,
        aiValidatedCount: aiValidatedArticles.length,
        ideasReadyForProductionCount: ideasReadyForProduction.length,
        activeProductionCount: activeProductionArticles.length,
        pendingRecs:
          recs.status === 'fulfilled'
            ? recs.value.filter((r) => r.status === 'pending')
            : [],
        totalViews: perf.status === 'fulfilled' ? perf.value.total_views : null,
        avgSeoScore,
        avgGeoScore,
        avgReadingTime,
        seoMonthly,
        geoMonthly,
        viewsMonthly,
        timeMonthly,
        publishedMonthly,
        seoChangePts,
        geoChangePts,
        timeChangeMins,
        publishedChangePct,
      })
    })
  }, [projectId])

  if (projectLoading) return <LoadingState />

  const isConnected = project?.status === 'connected'
  const firstName = user?.name?.split(' ')[0] ?? user?.name ?? ''

  const activityEvents = data ? deriveActivityEvents(data.activityArticles, projectId ?? '') : []
  const visibleActivityEvents = activityEvents.slice(0, 5)

  const seoScore = scoreOnHundred(data?.avgSeoScore) ?? 0
  const geoScore = scoreOnHundred(data?.avgGeoScore) ?? 0
  const totalViews = formatCompact(data?.totalViews)

  const enabledProviders = providers.filter((provider) => provider.enabled)
  const pipelineActive = Boolean(pipeline?.enabled)
  const lastRunLabel = pipelineLogs[0] ? formatDate(pipelineLogs[0].started_at) : '—'

  const todoRows = data
    ? [
        {
          label: `Valider ${data.ideasCount} idée${data.ideasCount > 1 ? 's' : ''}`,
          detail: data.ideasCount > 0 ? 'Générées récemment' : 'Aucune idée en attente',
          count: data.ideasCount,
          href: `/projects/${projectId}/ideas`,
        },
        {
          label: `Valider ${data.reviewNeededCount} article${data.reviewNeededCount > 1 ? 's' : ''}`,
          detail: data.reviewNeededCount > 0 ? 'Prêts à publier' : 'Aucun article à valider',
          count: data.reviewNeededCount,
          href: `/projects/${projectId}/articles`,
        },
        {
          label: `Programmer ${data.scheduledCount || data.readyCount} publication${(data.scheduledCount || data.readyCount) > 1 ? 's' : ''}`,
          detail: 'Dans le calendrier',
          count: data.scheduledCount || data.readyCount,
          href: `/projects/${projectId}/calendar`,
        },
      ]
    : []

  return (
    <div className="mx-auto flex w-full max-w-none flex-col gap-5">
      <section className="flex items-start justify-between gap-6 pb-2 pt-3">
        <div>
          <h1 className="text-[22px] font-semibold leading-tight text-primary">
            {firstName ? `Bonjour, ${firstName} 👋` : 'Bonjour 👋'}
          </h1>
          <p className="mt-1.5 text-[14px] text-secondary">
            Vue d'ensemble de votre pipeline éditorial et de vos performances.
          </p>
        </div>
      </section>

      <section className="grid h-[48px] grid-cols-[auto_auto_auto_auto_auto] items-center overflow-hidden rounded-[10px] border-2 border-border bg-transparent text-[14px] text-secondary">
        {/* Domain */}
        <div className="flex h-full min-w-0 items-center gap-2 border-r border-border px-6 font-medium text-primary">
          <Globe size={15} className="shrink-0 text-secondary" />
          <span className="truncate">{project?.domain ?? '—'}</span>
        </div>
        {/* Statut connecté */}
        <div className="flex h-full min-w-0 items-center justify-center border-r border-border px-6">
          <span className="inline-flex h-7 items-center gap-1.5 rounded-[8px] bg-success px-3 text-[14px] font-semibold text-white">
            <span className="flex h-4 w-4 items-center justify-center rounded-full bg-white text-success">
              <svg
                aria-hidden="true"
                viewBox="0 0 16 16"
                className="h-3 w-3"
                fill="none"
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2.4"
              >
                <path d="M8 12V4" />
                <path d="M4.75 7.25 8 4l3.25 3.25" />
              </svg>
            </span>
            <span>
              {isConnected ? 'Connecté' : 'Non connecté'}
            </span>
          </span>
        </div>
        {/* Pipeline + runs */}
        <div className="flex h-full min-w-0 items-center gap-2 border-r border-border px-6">
          <Clock size={15} className="shrink-0" />
          <span className="truncate">Pipeline : <strong className="text-primary">{pipelineActive ? 'Actif' : 'Inactif'}</strong></span>
        </div>
        <div className="flex h-full min-w-0 items-center border-r border-border px-6">
          <span className="truncate">Dernier run : <strong className="text-primary">{lastRunLabel}</strong></span>
        </div>
        <div className="flex h-full min-w-0 items-center px-6">
          <span className="truncate">Prochain run : <strong className="text-primary">—</strong></span>
        </div>
      </section>

      <section className="grid grid-cols-5 gap-4">
        <SeoRadialCard
          title="SEO moyen"
          score={seoScore || 0}
          changePts={data?.seoChangePts ?? 0}
          data={data?.seoMonthly ?? Array.from({ length: MONTHLY_METRIC_POINTS }, () => ({ v: 0 }))}
        />
        <SeoRadialCard
          title="GEO moyen"
          score={geoScore || 0}
          changePts={data?.geoChangePts ?? 0}
          color={NEUTRAL_CHART_COLORS.tertiary}
          data={data?.geoMonthly ?? Array.from({ length: MONTHLY_METRIC_POINTS }, () => ({ v: 0 }))}
        />
        <AreaMetricCard
          title="Vues mensuelles"
          value={totalViews}
          change={data ? (() => { const d = data.viewsMonthly; const diff = d[MONTHLY_METRIC_POINTS - 1].v - d[MONTHLY_METRIC_POINTS - 2].v; return diff >= 0 ? `+${diff}` : `${diff}` })() : '—'}
          changeColor={NEUTRAL_CHART_COLORS.primary}
          color={NEUTRAL_CHART_COLORS.primary}
          data={data?.viewsMonthly ?? Array.from({ length: MONTHLY_METRIC_POINTS }, () => ({ v: 0 }))}
        />
        <SparkMetricCard
          title="Temps moyen"
          value={data?.avgReadingTime != null ? `${data.avgReadingTime} min` : '—'}
          change={data ? (data.timeChangeMins >= 0 ? `+${data.timeChangeMins} min` : `${data.timeChangeMins} min`) : '—'}
          changeColor={NEUTRAL_CHART_COLORS.secondary}
          color={NEUTRAL_CHART_COLORS.secondary}
          data={data?.timeMonthly ?? Array.from({ length: MONTHLY_METRIC_POINTS }, () => ({ v: 0 }))}
        />
        <BarMetricCard
          title="Publié"
          value={data?.publishedCount ?? '—'}
          change={data ? (data.publishedChangePct >= 0 ? `+${data.publishedChangePct}%` : `${data.publishedChangePct}%`) : '—'}
          changeColor={NEUTRAL_CHART_COLORS.primary}
          color={NEUTRAL_CHART_COLORS.primary}
          data={data?.publishedMonthly ?? Array.from({ length: WEEKLY_METRIC_POINTS }, () => ({ v: 0 }))}
        />
      </section>

      <section className="grid grid-cols-4 divide-x divide-border overflow-hidden rounded-[10px] border-2 border-border bg-transparent shadow-none">
        <PipelineSummaryItem
          icon={<ClipboardList size={20} />}
          title="Production"
          value={data?.activeProductionCount ?? 0}
          description="Articles en rédaction"
        />
        <PipelineSummaryItem
          icon={<ShieldCheck size={20} />}
          title="À valider"
          value={data?.reviewNeededCount ?? 0}
          description="En attente"
        />
        <PipelineSummaryItem
          icon={<Lightbulb size={20} />}
          title="Idées prêtes"
          value={data?.ideasReadyForProductionCount ?? data?.ideasCount ?? 0}
          description={enabledProviders.length > 0 ? 'Qualifiées' : '0 provider IA actif'}
        />
        <PipelineSummaryItem
          icon={<Edit3 size={20} />}
          title="En cours"
          value={data?.inProgressCount ?? 0}
          description="Actifs"
        />
      </section>

      <section className="grid items-stretch gap-4 lg:grid-cols-[1.62fr_1fr]">
        <Card padding="none" className="flex h-full flex-col overflow-hidden rounded-[10px]">
          <div className="flex items-center justify-between border-b border-border px-5 py-4">
            <h2 className="text-[15px] font-semibold text-primary">Articles récents</h2>
            <button
              type="button"
              onClick={() => navigate(`/projects/${projectId}/articles`)}
              className="flex items-center gap-1.5 rounded-[6px] px-2.5 py-1 text-[11px] font-medium text-tertiary transition-colors hover:bg-surface-soft hover:text-primary"
            >
              Voir tout <ArrowRight size={13} />
            </button>
          </div>
          <div className="grid h-10 grid-cols-[minmax(0,1fr)_120px_56px_110px_96px] items-center gap-6 border-b border-border px-5 text-[11px] font-medium text-tertiary">
            <span>Article</span>
            <span>Score Global</span>
            <span>Vues</span>
            <span>Statut</span>
            <span>Catégorie</span>
          </div>
          <div className="flex flex-col divide-y divide-border">
            {(data?.recentArticles ?? []).map((article) => {
              const category = data?.categories.find((item) => item.id === article.category_id)
              const score = scoreOnHundred(article.global_score)
              const scoreColor = (score ?? 0) >= 75 ? 'var(--color-success)' : (score ?? 0) >= 50 ? 'var(--color-warning)' : 'var(--color-danger)'
              return (
                <button
                  key={article.id}
                  type="button"
                  onClick={() => navigate(`/projects/${projectId}/articles/${article.id}/edit`)}
                  className="grid grid-cols-[minmax(0,1fr)_120px_56px_110px_96px] items-center gap-6 px-5 py-1.5 text-left transition-colors hover:bg-surface-soft"
                >
                  <span className="min-w-0">
                    <span className="block truncate text-[14px] font-medium text-primary">{article.title}</span>
                    <span className="mt-0.5 flex items-center gap-1.5 text-[11px] font-medium text-tertiary">
                      <span>{formatDate(getArticleDate(article))}</span>
                      <span>·</span>
                      <span>{article.author_name ?? 'Auteur'}</span>
                      {article.word_count > 0 && <><span>·</span><span>{article.word_count.toLocaleString('fr-FR')} mots</span></>}
                    </span>
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="w-6 shrink-0 text-right text-[14px] font-semibold tabular-nums text-primary">
                      {score ?? '—'}
                    </span>
                    <span className="h-[6px] w-[60px] shrink-0 overflow-hidden rounded-full bg-surface-muted">
                      <span
                        className="block h-full rounded-full transition-all"
                        style={{ width: `${Math.min(score ?? 0, 100)}%`, backgroundColor: scoreColor }}
                      />
                    </span>
                  </span>
                  <span className="text-[11px] font-medium text-tertiary">—</span>
                  <span className="flex shrink-0">
                    <StatusBadge status={article.status} />
                  </span>
                  <span className="flex shrink-0">
                    {category ? (
                      <span
                        className="inline-flex h-[22px] items-center rounded-full px-2.5 text-[11px] font-medium whitespace-nowrap"
                        style={{ backgroundColor: `${category.color ?? NEUTRAL_CHART_COLORS.secondary}22`, color: category.color ?? NEUTRAL_CHART_COLORS.secondary }}
                      >
                        {category.name}
                      </span>
                    ) : (
                      <span className="text-[11px] font-medium text-tertiary">—</span>
                    )}
                  </span>
                </button>
              )
            })}
            {data && data.recentArticles.length === 0 && (
              <div className="px-4 py-10 text-[14px] text-secondary">Aucun article récent.</div>
            )}
          </div>
        </Card>

        <div className="flex flex-col gap-4">
          <Card padding="none" className="overflow-hidden rounded-[10px]">
            <h2 className="border-b border-border px-6 py-4 text-[15px] font-semibold text-primary">À faire maintenant</h2>
            <div className="flex flex-col divide-y divide-border-soft">
              {todoRows.map((row) => (
                <button
                  key={row.label}
                  type="button"
                  onClick={() => navigate(row.href)}
                  className="grid h-10 grid-cols-[minmax(0,1fr)_auto] items-center gap-4 px-6 text-left transition-colors hover:bg-surface-soft"
                >
                  <span className="text-[11px] font-medium text-tertiary">{row.label}</span>
                  <span className="shrink-0 pl-6 text-[11px] font-medium text-tertiary">{row.detail}</span>
                </button>
              ))}
            </div>
          </Card>

          <Card padding="none" className="overflow-hidden rounded-[10px]">
            <h2 className="border-b border-border px-6 py-4 text-[15px] font-semibold text-primary">Activité récente</h2>
            <div className="flex flex-col divide-y divide-border-soft">
              {visibleActivityEvents.length === 0
                ? Array.from({ length: 5 }).map((_, i) => (
                    <div key={`empty-${i}`} className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-x-4 px-6 py-2.5">
                      <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-transparent" />
                  <span className="text-[11px] font-medium text-tertiary">—</span>
                  <span />
                    </div>
                  ))
                : (
                  <>
                    {visibleActivityEvents.map((event, index) => (
                      <button
                        key={event.id}
                        type="button"
                        onClick={() => navigate(event.href)}
                        className="grid h-10 grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-x-4 px-6 text-left transition-colors hover:bg-surface-soft"
                      >
                        <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: [NEUTRAL_CHART_COLORS.primary, NEUTRAL_CHART_COLORS.secondary, NEUTRAL_CHART_COLORS.tertiary, NEUTRAL_CHART_COLORS.muted][index % 4] }} />
                        <span className="truncate text-[11px] font-medium text-tertiary">
                          {event.label} : {event.articleTitle}
                        </span>
                        <span className="shrink-0 pl-6 text-[11px] font-medium text-tertiary">{event.time}</span>
                      </button>
                    ))}
                    {Array.from({ length: Math.max(0, 5 - visibleActivityEvents.length) }).map((_, i) => (
                      <div key={`pad-${i}`} className="grid h-10 grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-x-4 px-6">
                        <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-transparent" />
                        <span />
                        <span />
                      </div>
                    ))}
                  </>
                )}
            </div>
          </Card>
        </div>
      </section>

      {project && (!project.audience || !project.tone) && (
        <button
          type="button"
          onClick={() => navigate(`/projects/${projectId}/settings`)}
          className="flex items-start gap-3 rounded-[8px] border border-warning/20 bg-warning/8 px-4 py-3 text-left text-warning"
        >
          <AlertCircle size={16} className="mt-0.5 shrink-0" />
          <span>
            <span className="block text-[14px] font-semibold">Complétez la configuration de votre projet</span>
            <span className="block text-[11px] font-medium text-tertiary">Définissez l'audience cible et le ton éditorial.</span>
          </span>
        </button>
      )}
    </div>
  )
}
