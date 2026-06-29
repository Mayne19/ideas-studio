import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Lightbulb, BarChart2, Globe,
  ArrowRight, AlertCircle, Clock,
  Edit3, Eye, Send, Star, ClipboardList, Calendar, HelpCircle, Play,
  Plus, RefreshCw, ShieldCheck,
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

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const days = Math.floor(diff / 86400000)
  if (days === 0) return "Aujourd'hui"
  if (days === 1) return 'Hier'
  if (days < 7) return `Il y a ${days} j`
  if (days < 30) return `Il y a ${Math.floor(days / 7)} sem.`
  return formatDate(iso)
}

const RECENT_ARTICLES_LIMIT = 5

type ActivityEvent = {
  id: string
  icon: React.ReactNode
  label: string
  articleTitle: string
  time: string
  href: string
}

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
  avgReadingTime: number | null
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

function MiniLineChart({ values, color }: { values: number[]; color: string }) {
  const width = 160
  const height = 42
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = Math.max(max - min, 1)
  const points = values.map((value, index) => {
    const x = (index / Math.max(values.length - 1, 1)) * width
    const y = height - ((value - min) / range) * (height - 10) - 5
    return { x, y }
  })
  const path = points.map((point, index) => `${index === 0 ? 'M' : 'L'}${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(' ')

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-10 w-full overflow-visible" aria-hidden="true">
      <path d={path} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      {points.map((point, index) => (
        <circle key={index} cx={point.x} cy={point.y} r="2" fill={color} />
      ))}
    </svg>
  )
}

function MiniBarChart({ values, color }: { values: number[]; color: string }) {
  const max = Math.max(...values, 1)
  return (
    <div className="flex h-10 items-end gap-2">
      {values.map((value, index) => (
        <span
          key={index}
          className="w-1 rounded-t-full"
          style={{ height: `${Math.max(8, (value / max) * 40)}px`, backgroundColor: color }}
        />
      ))}
    </div>
  )
}

function SeoGauge({ value }: { value: number }) {
  const radius = 18
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (Math.min(Math.max(value, 0), 100) / 100) * circumference

  return (
    <div className="relative h-14 w-14 shrink-0">
      <svg viewBox="0 0 48 48" className="-rotate-90">
        <circle cx="24" cy="24" r={radius} fill="none" stroke="var(--color-surface-muted)" strokeWidth="3" />
        <circle
          cx="24"
          cy="24"
          r={radius}
          fill="none"
          stroke="#00c950"
          strokeWidth="3"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-[13px] font-semibold text-primary">{value}</span>
    </div>
  )
}

function MetricBox({
  title,
  value,
  change,
  color,
  children,
}: {
  title: string
  value: string | number
  change?: string
  color: string
  children: React.ReactNode
}) {
  return (
    <article className="rounded-[8px] border border-border bg-surface px-5 py-4 shadow-none">
      <div className="mb-2.5 flex items-center gap-1.5 text-[12px] font-medium text-secondary">
        {title}
        <HelpCircle size={12} className="text-tertiary" />
      </div>
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <div className="text-[20px] font-semibold leading-none text-primary">{value}</div>
          {children}
        </div>
        {change && <span className="text-[14px] font-medium" style={{ color }}>{change}</span>}
      </div>
    </article>
  )
}

function PipelineInfoCard({
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
    <Card padding="sm" className="flex min-h-[96px] items-center gap-4 px-5 py-4">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center text-secondary">{icon}</span>
      <div>
        <p className="text-[12px] font-medium text-secondary">{title}</p>
        <p className="mt-0.5 text-[20px] font-semibold leading-none text-primary">{value}</p>
        <p className="mt-1.5 text-[12px] text-tertiary">{description}</p>
      </div>
    </Card>
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
      const worded = contentArticles.filter((a) => a.word_count > 0)
      const avgReadingTime = worded.length > 0
        ? Math.ceil(worded.reduce((s, a) => s + a.word_count, 0) / worded.length / 200)
        : null
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
        avgReadingTime,
      })
    })
  }, [projectId])

  if (projectLoading) return <LoadingState />

  const isConnected = project?.status === 'connected'
  const firstName = user?.name?.split(' ')[0] ?? user?.name ?? ''

  const activityEvents = data ? deriveActivityEvents(data.activityArticles, projectId ?? '') : []
  const visibleActivityEvents = activityEvents.slice(0, 5)

  const seoScore = scoreOnHundred(data?.avgSeoScore) ?? 0
  const totalViews = formatCompact(data?.totalViews)
  const lastPipelineRun = pipelineLogs[0]
  const enabledProviders = providers.filter((provider) => provider.enabled)
  const pipelineActive = Boolean(pipeline?.enabled)
  const lastRunLabel = lastPipelineRun ? formatDate(lastPipelineRun.started_at) : '—'
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
    <div className="mx-auto flex w-full max-w-none flex-col gap-4">
      <section className="flex items-start justify-between gap-6 px-6 pb-4 pt-2">
        <div>
          <h1 className="text-[20px] font-semibold leading-tight text-primary">
            {firstName ? `Bonjour, ${firstName} 👋` : 'Bonjour 👋'}
          </h1>
          <p className="mt-1 text-[13px] text-secondary">
            Vue d'ensemble de votre pipeline éditorial et de vos performances.
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-5 text-[13px] font-medium">
            <span className="flex items-center gap-2 text-primary">
              <Globe size={14} />
              {project?.domain ?? '—'}
            </span>
            <span className="h-5 w-px bg-border" />
            <span className="flex items-center gap-2 text-primary">
              <span className={`h-1.5 w-1.5 rounded-full ${isConnected ? 'bg-[#00c950]' : 'bg-tertiary'}`} />
              {isConnected ? 'Connecté' : 'Non connecté'}
            </span>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-3 pt-4">
          <button
            type="button"
            onClick={() => navigate(`/projects/${projectId}/articles`)}
            className="inline-flex h-9 items-center gap-2 rounded-[6px] border border-border bg-surface px-4 text-[13px] font-medium text-primary transition-colors hover:bg-surface-soft"
          >
            Créer un article
            <Plus size={13} />
          </button>
          <button
            type="button"
            onClick={() => navigate(`/projects/${projectId}/pipeline`)}
            className="inline-flex h-9 items-center gap-2 rounded-[6px] border border-accent bg-accent px-4 text-[13px] font-medium text-white transition-opacity hover:opacity-90"
          >
            Lancer le pipeline
            <Play size={13} />
          </button>
        </div>
      </section>

      <section className="grid h-[44px] grid-cols-[160px_1fr_1.25fr_1.25fr_1.25fr] overflow-hidden rounded-[8px] border border-border bg-surface text-[13px] text-secondary">
        <div className="flex items-center justify-center border-r border-border">
          <span className="inline-flex h-7 items-center gap-1.5 rounded-[8px] bg-accent px-3 text-[13px] font-medium text-white">
            <span className="flex h-4 w-4 items-center justify-center rounded-full bg-white text-accent">
              <ArrowRight size={10} />
            </span>
            Production
          </span>
        </div>
        <div className="flex items-center justify-center gap-2 border-r border-border">
          <Clock size={14} />
          Pipeline : <strong className="text-primary">{pipelineActive ? 'Actif' : 'Inactif'}</strong>
        </div>
        <div className="flex items-center justify-center gap-2 border-r border-border">
          <Clock size={14} />
          Dernier run : <strong className="text-primary">{lastRunLabel}</strong>
        </div>
        <div className="flex items-center justify-center gap-2 border-r border-border">
          <Calendar size={14} />
          Prochain run : <strong className="text-primary">—</strong>
        </div>
        <div className="flex items-center justify-center gap-2">
          <RefreshCw size={14} />
          Mode : <strong className="text-primary">{pipeline?.enabled ? 'Automatique' : 'Mensuel'}</strong>
        </div>
      </section>

      <section className="grid grid-cols-5 gap-4">
        <article className="rounded-[8px] border border-border bg-surface px-5 py-4 shadow-none">
          <div className="mb-2.5 flex items-center gap-1.5 text-[12px] font-medium text-secondary">
            Score SEO moyen
            <HelpCircle size={12} className="text-tertiary" />
          </div>
          <div className="flex items-center gap-4">
            <SeoGauge value={seoScore || 0} />
            <div className="min-w-0 flex-1">
              <div className="text-[15px] font-semibold text-[#00c950]">+6 pts</div>
              <MiniLineChart values={[54, 58, 57, 62, 64, 61, 66, 65, 70, 72, 75, 78]} color="#00c950" />
            </div>
          </div>
        </article>
        <MetricBox title="Vues du mois" value={totalViews} change="+12%" color="#00c950">
          <MiniLineChart values={[24, 27, 29, 21, 25, 17, 19, 12, 22, 20, 10, 14].reverse()} color="#0066ff" />
        </MetricBox>
        <MetricBox title="Temps moyen" value={data?.avgReadingTime != null ? `${data.avgReadingTime}:32` : '—'} change="-12%" color="#ff3b1f">
          <MiniLineChart values={[18, 14, 28, 22, 31, 24, 29, 26, 34, 28, 35, 30]} color="#ff3b1f" />
        </MetricBox>
        <MetricBox title="Publiés" value={data?.publishedCount ?? '—'} change="+9%" color="#00c950">
          <MiniBarChart values={[13, 15, 16, 17, 22, 15, 28, 19, 25, 34, 23, 29, 38, 31, 35, 27, 31, 28]} color="#00c950" />
        </MetricBox>
        <MetricBox title="En cours" value={data?.inProgressCount ?? '—'} change="-5%" color="#a238ff">
          <MiniBarChart values={[13, 14, 15, 14, 20, 27, 34, 39, 31, 19, 15, 12, 13, 13, 14, 13]} color="#a238ff" />
        </MetricBox>
      </section>

      <section className="grid grid-cols-4 gap-4">
        <PipelineInfoCard
          icon={<BarChart2 size={24} />}
          title="Pipeline"
          value={pipelineActive ? data?.activeProductionCount ?? 0 : 0}
          description={pipelineActive ? 'Pipeline actif' : 'Aucun pipeline actif'}
        />
        <PipelineInfoCard
          icon={<ClipboardList size={24} />}
          title="Production en cours"
          value={data?.activeProductionCount ?? 0}
          description="Articles en rédaction"
        />
        <PipelineInfoCard
          icon={<ShieldCheck size={24} />}
          title="À valider"
          value={data?.reviewNeededCount ?? 0}
          description="En attente de décision"
        />
        <PipelineInfoCard
          icon={<Lightbulb size={24} />}
          title="Idées prêtes"
          value={data?.ideasReadyForProductionCount ?? data?.ideasCount ?? 0}
          description={enabledProviders.length > 0 ? 'Qualifiées, à valider' : '0 provider IA actif.'}
        />
      </section>

      <section className="grid items-stretch gap-4 lg:grid-cols-[1.62fr_1fr]">
        <Card padding="none" className="flex min-h-[430px] flex-col overflow-hidden">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <h2 className="text-[13px] font-semibold text-primary">Articles récents</h2>
            <button
              type="button"
              onClick={() => navigate(`/projects/${projectId}/articles`)}
              className="flex items-center gap-1 text-[11px] font-medium text-secondary hover:text-primary transition-colors"
            >
              Voir tout <ArrowRight size={11} />
            </button>
          </div>
          <div className="grid grid-cols-[minmax(0,1fr)_150px_60px_auto_auto] border-b border-border px-4 py-2 text-[11px] font-medium uppercase tracking-wide text-tertiary">
            <span>Article</span>
            <span>Score SEO</span>
            <span>Vues</span>
            <span>Statut</span>
            <span className="pl-3">Catégorie</span>
          </div>
          <div className="flex flex-col divide-y divide-border">
            {(data?.recentArticles ?? []).map((article) => {
              const category = data?.categories.find((item) => item.id === article.category_id)
              const score = scoreOnHundred(article.seo_score)
              const scoreColor = (score ?? 0) >= 75 ? '#00c950' : (score ?? 0) >= 50 ? '#ffa51f' : '#ff3b1f'
              return (
                <button
                  key={article.id}
                  type="button"
                  onClick={() => navigate(`/projects/${projectId}/articles/${article.id}/edit`)}
                  className="grid grid-cols-[minmax(0,1fr)_150px_60px_auto_auto] items-center gap-2 px-4 py-2.5 text-left transition-colors hover:bg-surface-soft"
                >
                  <span className="min-w-0">
                    <span className="block truncate text-[13px] font-medium text-primary">{article.title}</span>
                    <span className="mt-0.5 flex items-center gap-1.5 text-[11px] text-tertiary">
                      <span>{formatDate(getArticleDate(article))}</span>
                      <span>·</span>
                      <span>{article.author_name ?? 'Auteur'}</span>
                      {article.word_count > 0 && <><span>·</span><span>{article.word_count.toLocaleString('fr-FR')} mots</span></>}
                    </span>
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="w-6 shrink-0 text-right text-[13px] font-semibold tabular-nums text-primary">
                      {score ?? '—'}
                    </span>
                    <span className="h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-surface-muted">
                      <span
                        className="block h-full rounded-full transition-all"
                        style={{ width: `${Math.min(score ?? 0, 100)}%`, backgroundColor: scoreColor }}
                      />
                    </span>
                  </span>
                  <span className="text-[12px] text-tertiary">—</span>
                  <span className="flex shrink-0">
                    <StatusBadge status={article.status} />
                  </span>
                  <span className="flex shrink-0 pl-3">
                    {category ? (
                      <span
                        className="inline-flex h-5 items-center rounded-full px-2.5 text-[11px] font-medium whitespace-nowrap"
                        style={{ backgroundColor: `${category.color ?? '#0066ff'}18`, color: category.color ?? '#0066ff' }}
                      >
                        {category.name}
                      </span>
                    ) : (
                      <span className="text-[12px] text-tertiary">—</span>
                    )}
                  </span>
                </button>
              )
            })}
            {data && data.recentArticles.length === 0 && (
              <div className="px-4 py-10 text-[13px] text-secondary">Aucun article récent.</div>
            )}
          </div>
        </Card>

        <div className="flex min-h-[430px] flex-col gap-4">
          <Card padding="none" className="overflow-hidden">
            <h2 className="border-b border-border px-6 py-4 text-[13px] font-semibold text-primary">À faire maintenant</h2>
            <div className="flex flex-col divide-y divide-border-soft">
              {todoRows.map((row) => (
                <button
                  key={row.label}
                  type="button"
                  onClick={() => navigate(row.href)}
                  className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-3 px-6 py-3 text-left transition-colors hover:bg-surface-soft"
                >
                  <span>
                    <span className="block text-[13px] font-medium text-primary">{row.label}</span>
                    <span className="block text-[11px] text-secondary">{row.detail}</span>
                  </span>
                  <span className="inline-flex h-6 min-w-9 items-center justify-center rounded-full bg-blue-50 px-2 text-[13px] font-semibold text-blue-700">{row.count}</span>
                  <ArrowRight size={14} className="text-tertiary" />
                </button>
              ))}
            </div>
          </Card>

          <Card padding="none" className="flex flex-1 flex-col overflow-hidden">
            <h2 className="border-b border-border px-6 py-4 text-[13px] font-semibold text-primary">Activité récente</h2>
            <div className="flex flex-1 flex-col divide-y divide-border-soft">
              {visibleActivityEvents.map((event, index) => (
                <button
                  key={event.id}
                  type="button"
                  onClick={() => navigate(event.href)}
                  className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 px-6 py-2.5 text-left transition-colors hover:bg-surface-soft"
                >
                  <span className={`h-2 w-2 rounded-full ${['bg-[#00c950]', 'bg-[#0066ff]', 'bg-[#ffa51f]', 'bg-[#ff3b1f]'][index % 4]}`} />
                  <span className="truncate text-[13px] font-medium text-primary">
                    {event.label} : {event.articleTitle}
                  </span>
                  <span className="text-[13px] font-medium text-secondary">{event.time}</span>
                </button>
              ))}
              {visibleActivityEvents.length === 0 && (
                <div className="px-6 py-10 text-[13px] text-secondary">Aucune activité récente.</div>
              )}
            </div>
          </Card>
        </div>
      </section>

      {project && (!project.audience || !project.tone) && (
        <button
          type="button"
          onClick={() => navigate(`/projects/${projectId}/settings`)}
          className="flex items-start gap-3 rounded-[8px] border border-amber-200 bg-amber-50 px-4 py-3 text-left text-amber-800"
        >
          <AlertCircle size={16} className="mt-0.5 shrink-0" />
          <span>
            <span className="block text-[13px] font-semibold">Complétez la configuration de votre projet</span>
            <span className="block text-[12px]">Définissez l'audience cible et le ton éditorial.</span>
          </span>
        </button>
      )}
    </div>
  )
}
