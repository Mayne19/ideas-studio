import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  FileText, Lightbulb, BarChart2, Sparkles, Globe,
  WifiOff, ArrowRight, AlertCircle, Clock, CheckCircle, PenLine,
  Edit3, Eye, Send, Star, BookOpen,
} from 'lucide-react'
import { useProject } from '@/context/ProjectContext'
import { useAuth } from '@/context/AuthContext'
import { listArticles } from '@/api/articles'
import { listCategories } from '@/api/categories'
import { getPerformanceSummary } from '@/api/performance'
import { listRecommendations } from '@/api/recommendations'
import type { Article, Category, OptimizationRecommendation } from '@/types'
import { Card } from '@/components/ui/Card'
import StatusBadge from '@/components/ui/StatusBadge'
import LoadingState from '@/components/ui/LoadingState'
import Modal from '@/components/ui/Modal'
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

function KpiCard({
  icon, value, suffix, label, trend, onClick, tone = 'accent',
}: {
  icon: React.ReactNode
  value: string | number
  suffix?: string
  label: string
  trend?: string | null
  onClick?: () => void
  tone?: 'accent' | 'sky' | 'indigo' | 'violet' | 'orange' | 'success'
}) {
  const trendClass = trend?.startsWith('+')
    ? 'bg-success/10 text-[#1a7a3a]'
    : trend?.startsWith('-')
      ? 'bg-danger/10 text-danger'
      : 'text-tertiary'
  const iconTone = {
    accent: 'bg-accent/10 text-accent',
    sky: 'bg-sky-500/10 text-sky-600',
    indigo: 'bg-indigo-500/10 text-indigo-600',
    violet: 'bg-violet-500/10 text-violet-600',
    orange: 'bg-orange-500/10 text-orange-600',
    success: 'bg-success/10 text-[#1a7a3a]',
  }[tone]

  return (
    <div
      className={`rounded-[22px] bg-surface p-4 flex flex-col justify-between gap-2 ${onClick ? 'cursor-pointer transition-colors hover:bg-white' : ''}`}
      onClick={onClick}
    >
      <span className={`flex h-8 w-8 items-center justify-center rounded-[10px] ${iconTone}`}>{icon}</span>
      <p className="text-[24px] font-semibold text-primary tracking-tight leading-none">
        {value}
        {suffix && <span className="text-[14px] font-normal text-tertiary ml-0.5">{suffix}</span>}
      </p>
      <div className="flex items-center justify-between">
        <p className="text-[12px] text-tertiary">{label}</p>
        {trend !== undefined && (
          <span className={`rounded-full px-1.5 py-0.5 text-[11px] font-medium ${trendClass}`}>{trend ?? '—'}</span>
        )}
      </div>
    </div>
  )
}

const RECENT_ARTICLES_LIMIT = 7

const TODO_ACCENT = {
  warning: 'bg-warning/8 text-[#c07000]',
  danger:  'bg-danger/8 text-danger',
  accent:  'bg-accent/8 text-accent',
  success: 'bg-success/8 text-[#1a7a3a]',
} as const

type TodoAccent = keyof typeof TODO_ACCENT

type TodoItem = {
  id: string
  icon: React.ReactNode
  label: string
  href: string
  accent: TodoAccent
}

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

function isFilledScore(score: number | null | undefined): score is number {
  return typeof score === 'number' && Number.isFinite(score)
}

function scoreOnTen(score: number | null | undefined): string {
  if (!isFilledScore(score)) return '—'
  const normalized = score > 10 ? score / 10 : score
  return normalized.toFixed(1)
}

function scoreTone(score: number | null | undefined): string {
  if (!isFilledScore(score)) return 'bg-[#f0f0f2] text-tertiary'
  if (score >= 70) return 'bg-success/10 text-[#1a7a3a]'
  if (score >= 40) return 'bg-warning/10 text-[#c07000]'
  return 'bg-danger/10 text-danger'
}

function ArticleScoreBadge({ label, value }: { label: string; value: number | null }) {
  return (
    <span className={`inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium whitespace-nowrap ${scoreTone(value)}`}>
      {label} {isFilledScore(value) ? Math.round(value) : '—'}
    </span>
  )
}

function getArticleDate(article: Article): string {
  return article.published_at ?? article.scheduled_at ?? article.updated_at ?? article.created_at
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
  const [activityModalOpen, setActivityModalOpen] = useState(false)

  useEffect(() => {
    if (!projectId) return
    Promise.allSettled([
      listArticles(projectId, { limit: 500 }),
      listRecommendations(projectId),
      getPerformanceSummary(projectId, '30d'),
      listCategories(projectId),
    ]).then(([articles, recs, perf, cats]) => {
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
      const scored = contentArticles.filter((a) => a.seo_score !== null)
      const avgSeoScore = scored.length > 0
        ? scored.reduce((s, a) => s + (a.seo_score ?? 0), 0) / scored.length
        : null
      const worded = contentArticles.filter((a) => a.word_count > 0)
      const avgReadingTime = worded.length > 0
        ? Math.round(worded.reduce((s, a) => s + a.word_count, 0) / worded.length / 200)
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

  const todoItems: TodoItem[] = []
  if (!isConnected) {
    todoItems.push({
      id: 'connect',
      icon: <WifiOff size={14} />,
      label: 'Connecter votre blog pour activer le tracking et les analyses.',
      href: `/projects/${projectId}/settings/integration`,
      accent: 'warning',
    })
  }
  if (data) {
    const highRecs = data.pendingRecs.filter((r) => r.priority >= 3)
    if (highRecs.length > 0) {
      todoItems.push({
        id: 'recs',
        icon: <Sparkles size={14} />,
        label: `${highRecs.length} recommandation${highRecs.length > 1 ? 's' : ''} haute priorité à traiter.`,
        href: `/projects/${projectId}/recommendations`,
        accent: 'danger',
      })
    }
    if (data.reviewNeededCount > 0) {
      todoItems.push({
        id: 'review',
        icon: <AlertCircle size={14} />,
        label: `${data.reviewNeededCount} article${data.reviewNeededCount > 1 ? 's' : ''} en attente de révision.`,
        href: `/projects/${projectId}/articles`,
        accent: 'warning',
      })
    }
    if (data.ideasCount > 0) {
      todoItems.push({
        id: 'ideas',
        icon: <Lightbulb size={14} />,
        label: `${data.ideasCount} idée${data.ideasCount > 1 ? 's' : ''} en attente — commencez à rédiger.`,
        href: `/projects/${projectId}/ideas`,
        accent: 'accent',
      })
    }
    if (data.readyCount > 0) {
      todoItems.push({
        id: 'ready',
        icon: <Send size={14} />,
        label: `${data.readyCount} article${data.readyCount > 1 ? 's' : ''} prêt${data.readyCount > 1 ? 's' : ''} à publier.`,
        href: `/projects/${projectId}/articles`,
        accent: 'success',
      })
    }
    if (todoItems.length === 0) {
      todoItems.push({
        id: 'empty',
        icon: <CheckCircle size={14} />,
        label: 'Tout est en ordre. Générez de nouvelles idées pour continuer.',
        href: `/projects/${projectId}/ideas`,
        accent: 'success',
      })
    }
  }

  const activityEvents = data ? deriveActivityEvents(data.activityArticles, projectId ?? '') : []
  const visibleActivityEvents = activityEvents.slice(0, 5)

  const seoValue = scoreOnTen(data?.avgSeoScore)
  const hasTrackingData = Boolean(data?.totalViews && data.totalViews > 0)

  const summaryText = (() => {
    if (!data) return 'Chargement de vos données…'
    if (data.publishedCount === 0 && data.inProgressCount === 0 && data.ideasCount === 0) {
      return 'Commencez par créer votre premier article ou générer des idées.'
    }
    if (!isConnected && data.publishedCount > 0) {
      return "Votre blog n'est pas encore connecté — installez le snippet pour activer les analytics."
    }
    return "Voici l'état de votre pipeline éditorial."
  })()

  return (
    <div className="mx-auto max-w-5xl">
      {/* Greeting */}
      <div className="mb-6 flex items-start gap-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-[14px] bg-accent/10 text-accent text-[18px] font-bold">
          {project?.name.charAt(0).toUpperCase() ?? '?'}
        </div>
        <div className="flex-1 min-w-0">
          <h1 className="text-[22px] font-semibold text-primary tracking-tight">
            {firstName ? `Bonjour, ${firstName} 👋` : 'Bonjour 👋'}
          </h1>
          <p className="mt-0.5 text-[13px] text-secondary">{summaryText}</p>
          <div className="mt-1.5 flex flex-wrap items-center gap-3">
            <span className="flex items-center gap-1 text-[12px] text-tertiary">
              <Globe size={11} />
              {project?.domain ?? '—'}
            </span>
            <span
              className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${
                isConnected ? 'bg-success/10 text-[#1a7a3a]' : 'bg-[#f0f0f2] text-tertiary'
              }`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${isConnected ? 'bg-[#1a7a3a]' : 'bg-[#c8c8cc]'}`} />
              {isConnected ? 'Connecté' : 'Non connecté'}
            </span>
          </div>
        </div>
      </div>

      {/* Onboarding */}
      {project && (!project.audience || !project.tone) && (
        <div className="mb-5 flex items-start gap-3 rounded-[14px] border border-warning/30 bg-warning/5 px-4 py-3">
          <AlertCircle size={16} className="mt-0.5 shrink-0 text-[#c07000]" />
          <div className="flex-1 min-w-0">
            <p className="text-[13px] font-medium text-primary">Complétez la configuration de votre projet</p>
            <p className="mt-0.5 text-[12px] text-secondary">
              Définissez l'audience cible et le ton éditorial pour améliorer la qualité de la génération IA.
            </p>
          </div>
          <button
            onClick={() => navigate(`/projects/${projectId}/settings`)}
            className="shrink-0 rounded-[8px] bg-[#c07000] px-3 py-1.5 text-[11px] font-medium text-white hover:bg-[#a05500] transition-colors"
          >
            Configurer
          </button>
        </div>
      )}

      {/* 5 KPI cards */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
        <KpiCard
          icon={<BarChart2 size={17} />}
          value={seoValue}
          suffix="/10"
          label="Score SEO moyen"
          tone="accent"
          onClick={() => navigate(`/projects/${projectId}/performance`)}
        />
        <KpiCard
          icon={<Globe size={17} />}
          value={hasTrackingData && data?.totalViews != null ? data.totalViews.toLocaleString('fr-FR') : '—'}
          label="Vues du mois"
          tone="sky"
          onClick={() => navigate(`/projects/${projectId}/traffic`)}
        />
        <KpiCard
          icon={<BookOpen size={17} />}
          value={data?.avgReadingTime != null ? data.avgReadingTime : '—'}
          suffix={data?.avgReadingTime != null ? ' min' : undefined}
          label="Temps moyen"
          tone="indigo"
        />
        <KpiCard
          icon={<FileText size={17} />}
          value={data?.publishedCount ?? '—'}
          label="Publiés"
          tone="violet"
          onClick={() => navigate(`/projects/${projectId}/articles`)}
        />
        <KpiCard
          icon={<PenLine size={17} />}
          value={data?.inProgressCount ?? '—'}
          label="En cours"
          tone="orange"
          onClick={() => navigate(`/projects/${projectId}/articles`)}
        />
      </div>

      {!hasTrackingData && (
        <Card className="mb-6">
          <div className="flex items-start gap-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[12px] bg-accent/10 text-accent">
              <Globe size={16} />
            </span>
            <div>
              <p className="text-[14px] font-medium text-primary">Aucune donnée disponible pour le moment</p>
              <p className="mt-0.5 text-[13px] text-secondary">
                Connectez votre site pour commencer à collecter les statistiques.
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Main 2-col layout: left=articles (65%), right=todo+activity (35%) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left — col-span-2 — Articles récents only */}
        <div className="lg:col-span-2">
          <Card className="flex h-full flex-col">
            <div className="flex items-center justify-between mb-4">
              <p className="text-[12px] font-semibold text-secondary uppercase tracking-wide">Articles récents</p>
              <button
                onClick={() => navigate(`/projects/${projectId}/articles`)}
                className="text-[11px] text-accent hover:underline"
              >
                Voir tout →
              </button>
            </div>
            {!data || data.recentArticles.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-8 text-center">
                <FileText size={20} className="text-tertiary" />
                <p className="text-[13px] text-secondary">Aucun article pour l'instant.</p>
                <button
                  onClick={() => navigate(`/projects/${projectId}/articles`)}
                  className="text-[12px] text-accent hover:underline"
                >
                  Créer un article →
                </button>
              </div>
            ) : (
              <div className="flex flex-1 flex-col justify-between gap-1">
                {data.recentArticles.map((a) => {
                  const cat = data.categories.find((c) => c.id === a.category_id)
                  return (
                    <button
                      key={a.id}
                      onClick={() => navigate(`/projects/${projectId}/articles/${a.id}/edit`)}
                      className="flex min-w-0 items-center gap-3 rounded-[12px] px-2 py-1 text-left transition-colors hover:bg-[#f5f5f7]"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-[13px] font-medium leading-snug text-primary break-words">{a.title}</p>
                        <div className="mt-1 flex flex-wrap items-center gap-y-1">
                          <span className="mr-5 min-w-[112px] text-[10px] font-medium text-accent/80">
                            {cat?.name ?? 'Sans catégorie'}
                          </span>
                          <span className="mr-5 flex flex-wrap items-center gap-1.5">
                            <ArticleScoreBadge label="SEO" value={a.seo_score} />
                            <ArticleScoreBadge label="Lisibilité" value={a.readability_score} />
                            <ArticleScoreBadge label="Qualité" value={a.quality_score} />
                            <ArticleScoreBadge label="EEAT" value={a.eeat_score} />
                          </span>
                          <span className="inline-flex min-w-[96px] items-center">
                            <StatusBadge status={a.status} />
                          </span>
                        </div>
                      </div>
                      <div className="flex shrink-0 items-center gap-1 pt-0.5 text-[10px] text-tertiary">
                        <Clock size={9} />
                        <span>{formatDate(getArticleDate(a))}</span>
                      </div>
                    </button>
                  )
                })}
              </div>
            )}
          </Card>
        </div>
        {/* Right — col-span-1 — À faire + Activité stacked */}
        <div className="flex flex-col gap-4">
          {/* À faire maintenant */}
          <Card>
            <p className="text-[12px] font-semibold text-secondary uppercase tracking-wide mb-3">À faire maintenant</p>
            <div className="flex flex-col gap-1.5">
              {(!data ? [] : todoItems).slice(0, 5).map((item) => (
                <button
                  key={item.id}
                  onClick={() => navigate(item.href)}
                  className="flex items-start gap-2.5 rounded-[10px] p-2 text-left hover:bg-[#f5f5f7] transition-colors"
                >
                  <span className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full ${TODO_ACCENT[item.accent]}`}>
                    {item.icon}
                  </span>
                  <span className="flex-1 text-[12px] text-primary leading-snug">{item.label}</span>
                  <ArrowRight size={11} className="mt-0.5 shrink-0 text-tertiary" />
                </button>
              ))}
              {!data && (
                <p className="text-[12px] text-tertiary text-center py-2">Chargement…</p>
              )}
            </div>
          </Card>

          {/* Activité récente */}
          <Card className="flex-1">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-[12px] font-semibold text-secondary uppercase tracking-wide">Activité récente</p>
              {activityEvents.length > 5 && (
                <button
                  type="button"
                  onClick={() => setActivityModalOpen(true)}
                  className="text-[11px] text-accent hover:underline"
                >
                  Voir tout →
                </button>
              )}
            </div>
            {activityEvents.length === 0 ? (
              <p className="text-[12px] text-tertiary text-center py-4">Aucune activité récente disponible pour le moment.</p>
            ) : (
              <div className="flex flex-col gap-0.5">
                {visibleActivityEvents.map((ev) => (
                  <button
                    key={ev.id}
                    onClick={() => navigate(ev.href)}
                    className="flex items-start gap-2 rounded-[8px] px-2 py-1.5 text-left hover:bg-[#f5f5f7] transition-colors"
                  >
                    <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-accent/8 text-accent">
                      {ev.icon}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-[11px] font-medium text-secondary">{ev.label}</p>
                      <p className="text-[11px] text-primary truncate">{ev.articleTitle}</p>
                    </div>
                    <span className="text-[10px] text-tertiary shrink-0 mt-0.5">{ev.time}</span>
                  </button>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>

      <Modal
        open={activityModalOpen}
        onClose={() => setActivityModalOpen(false)}
        title="Toutes les activités récentes"
        size="lg"
      >
        {activityEvents.length === 0 ? (
          <p className="text-[13px] text-tertiary">Aucune activité récente disponible pour le moment.</p>
        ) : (
          <div className="max-h-[520px] overflow-y-auto pr-1">
            <div className="flex flex-col gap-1">
              {activityEvents.map((ev) => (
                <button
                  key={ev.id}
                  type="button"
                  onClick={() => {
                    setActivityModalOpen(false)
                    navigate(ev.href)
                  }}
                  className="flex items-start gap-2 rounded-[10px] px-2.5 py-2 text-left transition-colors hover:bg-[#f5f5f7]"
                >
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent/8 text-accent">
                    {ev.icon}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-[12px] font-medium text-secondary">{ev.label}</p>
                    <p className="truncate text-[12px] text-primary">{ev.articleTitle}</p>
                  </div>
                  <span className="mt-0.5 shrink-0 text-[11px] text-tertiary">{ev.time}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
