import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { AlertTriangle, Bot, CheckCircle, ChevronDown, ChevronUp, History, Loader2, Play, RotateCw, Settings, TestTube2 } from '@/components/ui/hugeIcons'
import { listAIProviders } from '@/api/aiProviders'
import { getPipelineLogs, getPipelineSettings, pipelineRunMessage, pipelineStatusLabel, triggerPipelineRun } from '@/api/pipeline'
import { listArticles } from '@/api/articles'
import { api } from '@/api/client'
import type { AIProviderPublic } from '@/api/aiProviders'
import type { PipelineLog, PipelineSettings } from '@/api/pipeline'
import type { AgentAssignment, AgentInfo, Article } from '@/types'
import { ArticleStatus, articleStatusLabel, type ArticleStatusCode } from '@/lib/status'
import Button from '@/components/ui/Button'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'

type LoadState = 'loading' | 'success' | 'error'

function StatusPill({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[12px] font-medium ${ok ? 'bg-success/8 text-success' : 'bg-warning/12 text-warning'}`}>
      {ok ? <CheckCircle size={11} /> : <AlertTriangle size={11} />}
      {label}
    </span>
  )
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <p className="mb-3 text-[12px] font-semibold uppercase tracking-wide text-secondary">{children}</p>
}

function workflowStatus(article: Article): string {
  return articleStatusLabel(article.status)
}

function isLogSuccess(status: string) {
  return status.toLowerCase() === 'success'
}

function isLogFailure(log: PipelineLog) {
  const status = log.status.toLowerCase()
  return ['failed', 'failure', 'error'].includes(status)
}

function isLogPartial(status: string) {
  return status.toLowerCase() === 'partial_success'
}

const WORKFLOW_STATUSES: ArticleStatusCode[] = [
  ArticleStatus.WRITING_REQUESTED, ArticleStatus.WRITING_IN_PROGRESS, ArticleStatus.DRAFT_READY, ArticleStatus.FAILED,
]

export default function GeneratePage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [providers, setProviders] = useState<AIProviderPublic[]>([])
  const [agents, setAgents] = useState<AgentInfo[]>([])
  const [assignments, setAssignments] = useState<AgentAssignment[]>([])
  const [pipeline, setPipeline] = useState<PipelineSettings | null>(null)
  const [logs, setLogs] = useState<PipelineLog[]>([])
  const [articles, setArticles] = useState<Article[]>([])
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [runState, setRunState] = useState<'idle' | 'running' | 'done' | 'error'>('idle')
  const [runSummary, setRunSummary] = useState('')
  const [openLogId, setOpenLogId] = useState<string | null>(null)
  const [copiedLogId, setCopiedLogId] = useState<string | null>(null)
  const autoOpenedLogId = useRef<string | null>(null)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    Promise.resolve().then(() => { if (!cancelled) setLoadState('loading') })
    Promise.all([
      listAIProviders(projectId).catch(() => []),
      api.get<AgentInfo[]>(`/settings/ai-agents?project_id=${projectId}`).catch(() => []),
      api.get<AgentAssignment[]>(`/settings/ai-agents/assignments?project_id=${projectId}`).catch(() => []),
      getPipelineSettings(projectId).catch(() => null),
      getPipelineLogs(projectId, 12).catch(() => []),
      listArticles(projectId, { limit: 80 }).catch(() => []),
    ])
      .then(([providerData, agentData, assignmentData, pipelineData, logData, articleData]) => {
        if (cancelled) return
        setProviders(providerData)
        setAgents(agentData)
        setAssignments(assignmentData)
        setPipeline(pipelineData)
        setLogs(logData)
        setArticles(articleData)
        setLoadState('success')
      })
      .catch(() => {
        if (!cancelled) setLoadState('error')
      })
    return () => { cancelled = true }
  }, [projectId, tick])

  const activeProviders = providers.filter((provider) => provider.api_key_configured)
  const assignedAgentIds = new Set(assignments.filter((item) => item.enabled).map((item) => item.agent_id))
  const workflowArticles = useMemo(
    () => articles.filter((article) => WORKFLOW_STATUSES.includes(article.status)),
    [articles],
  )
  const runningWorkflows = workflowArticles.filter((article) => article.status === ArticleStatus.WRITING_REQUESTED || article.status === ArticleStatus.WRITING_IN_PROGRESS)
  const completedWorkflows = workflowArticles.filter((article) => article.status === ArticleStatus.DRAFT_READY)
  const recentGenerations = useMemo(
    () => [...workflowArticles].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()).slice(0, 8),
    [workflowArticles],
  )
  const sortedLogs = useMemo(
    () => [...logs].sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime()),
    [logs],
  )
  const failedPipelineLogs = sortedLogs.filter(isLogFailure)
  const failureCount = failedPipelineLogs.length
  const successPipelineLogs = sortedLogs.filter((log) => isLogSuccess(log.status))
  const successCount = successPipelineLogs.length
  const partialCount = sortedLogs.filter((log) => isLogPartial(log.status)).length
  const runningPipelineCount = sortedLogs.filter((log) => log.status === 'running').length
  // Le provider par défaut (is_default, choisi dans Paramètres → Providers)
  // prime toujours — activeProviders[0] n'a aucun ordre garanti (dépend de
  // l'ordre de retour de l'API), ce n'est ni le défaut ni ce que les agents
  // utilisent réellement. Repli sur le premier configuré uniquement si
  // aucun défaut n'est encore choisi, pour ne pas afficher "Aucun" alors
  // qu'un provider existe.
  const activeProvider = activeProviders.find((provider) => provider.is_default) ?? activeProviders[0]
  const activeProviderLabel = activeProvider?.label ?? 'Aucun'
  const activeProviderModelLabel = activeProvider?.model || (activeProvider ? 'Non défini' : 'Aucun')
  const pipelineLabel = pipeline?.enabled ? 'Actif' : 'Inactif'
  const hasSystemIssue = activeProviders.length === 0 || assignedAgentIds.size === 0 || !pipeline?.enabled || failureCount > 0

  useEffect(() => {
    const latestLogId = sortedLogs[0]?.id ?? null
    if (!latestLogId || autoOpenedLogId.current === latestLogId) return
    autoOpenedLogId.current = latestLogId
    setOpenLogId(latestLogId)
  }, [sortedLogs])

  async function handleRunPipeline() {
    if (!projectId || runState === 'running' || runningPipelineCount > 0) return
    setRunState('running')
    setRunSummary('')
    try {
      const result = await triggerPipelineRun(projectId)
      setRunState(result.status === 'failed' ? 'error' : 'done')
      setRunSummary(pipelineRunMessage(result))
      setTick((value) => value + 1)
    } catch {
      setRunState('error')
    }
  }

  function copyLog(logId: string, detailText: string) {
    navigator.clipboard.writeText(detailText)
    setCopiedLogId(logId)
    window.setTimeout(() => {
      setCopiedLogId((current) => current === logId ? null : current)
    }, 1200)
  }

  function renderLog(log: PipelineLog, index: number) {
    const extendedLog = log as PipelineLog & {
      created_at?: string
      message?: string | null
      error?: string | null
      details?: unknown
    }
    const isOpen = openLogId === log.id
    const isLatest = index === 0
    const isSuccess = isLogSuccess(log.status)
    const isPartial = isLogPartial(log.status)
    const logDate = extendedLog.created_at || log.started_at
    const firstLine = (extendedLog.message || extendedLog.error || log.run_errors?.[0] || '').split('\n')[0].slice(0, 120)
    const details = extendedLog.details ?? {
      id: log.id,
      status: log.status,
      workflow_run_id: log.workflow_run_id || log.id,
      expected_ideas: log.expected_ideas,
      generated_ideas: log.generated_ideas,
      failed_categories: log.failed_categories,
      run_errors: log.run_errors,
      ideas_generated: log.ideas_generated,
      articles_created: log.articles_created,
      started_at: log.started_at,
      finished_at: log.finished_at,
    }
    const detailText = typeof details === 'string' ? details : JSON.stringify(details, null, 2)
    const copied = copiedLogId === log.id

    return (
      <div key={log.id || index} className="mb-2 overflow-hidden rounded-[8px] border border-border">
        <div
          className="flex cursor-pointer items-center justify-between gap-3 px-3 py-2 hover:bg-surface-soft"
          onClick={() => setOpenLogId(isOpen ? null : log.id)}
        >
          <div className="flex min-w-0 items-center gap-2">
            <History size={13} className="shrink-0 text-tertiary" />
            <span className={`text-[12px] font-medium ${
              isSuccess ? 'text-success' : isPartial ? 'text-warning' : log.status === 'running' ? 'text-secondary' : 'text-danger'
            }`}>
              {isSuccess ? '✓ Succès' : isPartial ? '⚠ Partiel' : log.status === 'running' ? pipelineStatusLabel(log.status) : '✗ Échec'}
            </span>
            <span className="whitespace-nowrap text-[11px] text-tertiary">{new Date(logDate).toLocaleString('fr-FR')}</span>
            {isLatest && (
              <span className="rounded-full bg-bg-accent px-1.5 py-0.5 text-[10px] text-accent">
                Dernier
              </span>
            )}
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <span className="text-[11px] text-tertiary">
              {log.generated_ideas ?? log.ideas_generated ?? 0}/{log.expected_ideas ?? 0} idée(s)
            </span>
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation()
                copyLog(log.id, detailText)
              }}
              className={`inline-flex h-7 items-center justify-center rounded-[7px] border px-2 text-[11px] font-medium shadow-sm transition-all active:scale-[0.98] focus:outline-none focus:ring-2 ${
                copied
                  ? 'border-success/25 bg-success/10 text-success focus:ring-success/20'
                  : 'border-border bg-surface text-secondary hover:border-accent/30 hover:bg-surface-soft hover:text-primary focus:ring-accent/20'
              }`}
            >
              {copied ? 'Copié' : 'Copier'}
            </button>
            <span className="flex h-7 w-7 items-center justify-center rounded-[7px] text-tertiary">
              {isOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </span>
          </div>
        </div>

        {!isSuccess && firstLine && (
          <div className={`border-t border-border px-3 py-1.5 ${isPartial ? 'bg-warning/10' : 'bg-bg-danger/30'}`}>
            <p className={`truncate text-[11px] ${isPartial ? 'text-warning' : 'text-danger'}`}>{firstLine}</p>
          </div>
        )}

        {isOpen && (
          <div className="border-t border-border">
            <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-all p-3 text-[10px] leading-relaxed text-secondary">
              {detailText}
            </pre>
          </div>
        )}
      </div>
    )
  }

  if (loadState === 'loading') return <LoadingState />
  if (loadState === 'error') return <ErrorState message="Impossible de charger le centre IA." onRetry={() => setTick((value) => value + 1)} />

  return (
    <div className="project-page project-page--wide">
      <div className="project-page-header">
        <div>
          <h1 className="text-[20px] font-semibold tracking-tight text-primary">Génération IA</h1>
          <p className="mt-0.5 text-[14px] text-secondary">Surveillez les workflows IA, les agents, les coûts et les erreurs d’exécution.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" variant="secondary" icon={<Settings size={13} />} onClick={() => navigate(`/projects/${projectId}/settings/providers`)}>
            Providers
          </Button>
          <Button size="sm" variant="secondary" icon={<Bot size={13} />} onClick={() => navigate(`/projects/${projectId}/settings/agents`)}>
            Agents
          </Button>
          <Button
            size="sm"
            icon={runState === 'running' || runningPipelineCount > 0 ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
            loading={runState === 'running'}
            disabled={runState === 'running' || runningPipelineCount > 0}
            onClick={handleRunPipeline}
          >
            {runState === 'running' || runningPipelineCount > 0 ? 'Exécution en cours…' : 'Tester le pipeline'}
          </Button>
        </div>
      </div>

      {runState === 'error' && (
        <div className="mb-4 rounded-[12px] border border-danger/20 bg-danger/5 px-4 py-3 text-[14px] text-danger">Le lancement manuel a échoué. Consultez l’historique ou les providers.</div>
      )}
      {runState === 'done' && (
        <div className="mb-4 rounded-[12px] border border-success/20 bg-success/8 px-4 py-3 text-[14px] text-success">
          Pipeline lancé. {runSummary || "L’historique a été rafraîchi."}
        </div>
      )}

      <div className="mb-6 rounded-[14px] border border-border bg-surface p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <SectionTitle>Vue d’ensemble IA</SectionTitle>
            <p className="text-[14px] text-secondary">
              {hasSystemIssue ? 'Configuration incomplète ou pipeline à surveiller.' : 'Pipeline prêt, providers et agents configurés.'}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {activeProviders.length === 0 && (
              <Button size="sm" variant="secondary" icon={<Settings size={13} />} onClick={() => navigate(`/projects/${projectId}/settings/providers`)}>
                Configurer
              </Button>
            )}
            {assignedAgentIds.size === 0 && (
              <Button size="sm" variant="secondary" icon={<Bot size={13} />} onClick={() => navigate(`/projects/${projectId}/settings/agents`)}>
                Assigner
              </Button>
            )}
          </div>
        </div>

        <div className="mt-4 grid overflow-hidden rounded-[12px] border border-border sm:grid-cols-2 xl:grid-cols-7">
          <div className="border-b border-border p-4 sm:border-r xl:border-b-0">
            <p className="text-[12px] font-medium text-tertiary">Provider</p>
            <p className="mt-1 truncate text-[20px] font-semibold tracking-tight text-primary">{activeProviderLabel}</p>
          </div>
          <div className="border-b border-border p-4 xl:border-b-0 xl:border-r">
            <p className="text-[12px] font-medium text-tertiary">Modèle</p>
            <p className="mt-1 truncate text-[20px] font-semibold tracking-tight text-primary" title={activeProviderModelLabel}>{activeProviderModelLabel}</p>
          </div>
          <div className="border-b border-border p-4 sm:border-r xl:border-b-0">
            <p className="text-[12px] font-medium text-tertiary">Agents assignés</p>
            <p className="mt-1 text-[20px] font-semibold tracking-tight text-primary">{assignedAgentIds.size}/{agents.length || '—'}</p>
          </div>
          <div className="border-b border-border p-4 xl:border-b-0 xl:border-r">
            <p className="text-[12px] font-medium text-tertiary">Pipeline</p>
            <p className="mt-1 text-[20px] font-semibold tracking-tight text-primary">{pipelineLabel}</p>
          </div>
          <div className="border-b border-border p-4 sm:border-r sm:border-b-0">
            <p className="text-[12px] font-medium text-tertiary">Réussites</p>
            <p className="mt-1 text-[20px] font-semibold tracking-tight text-success">{successCount}</p>
          </div>
          <div className="border-b border-border p-4 sm:border-r sm:border-b-0">
            <p className="text-[12px] font-medium text-tertiary">Partiels</p>
            <p className="mt-1 text-[20px] font-semibold tracking-tight text-warning">{partialCount}</p>
          </div>
          <div className="p-4">
            <p className="text-[12px] font-medium text-tertiary">Échecs</p>
            <p className={`mt-1 text-[20px] font-semibold tracking-tight ${failureCount ? 'text-danger' : 'text-primary'}`}>{failureCount}</p>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <StatusPill ok={activeProviders.length > 0} label={activeProviders.length ? `${activeProviders.length} provider configuré` : 'Aucun provider actif'} />
          <StatusPill ok={assignedAgentIds.size > 0} label={assignedAgentIds.size ? `${assignedAgentIds.size} agent assigné` : 'Aucun agent assigné'} />
          <StatusPill ok={Boolean(pipeline?.enabled)} label={pipeline?.enabled ? 'Automatisation active' : 'Automatisation inactive'} />
          <StatusPill ok={partialCount === 0} label={partialCount ? `${partialCount} partiel${partialCount > 1 ? 's' : ''}` : 'Aucun partiel'} />
          <StatusPill ok={failureCount === 0} label={failureCount ? `${failureCount} échec${failureCount > 1 ? 's' : ''}` : 'Aucun échec'} />
        </div>
      </div>

      <div className="mb-6 grid gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <div className="rounded-[14px] border border-border bg-surface p-4">
          <SectionTitle>Workflows IA</SectionTitle>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-[12px] border border-border px-3 py-3">
              <p className="text-[18px] font-semibold text-primary">{runningWorkflows.length}</p>
              <p className="text-[12px] text-tertiary">En cours / bloqués</p>
            </div>
            <div className="rounded-[12px] border border-border px-3 py-3">
              <p className="text-[18px] font-semibold text-primary">{completedWorkflows.length}</p>
              <p className="text-[12px] text-tertiary">Terminés</p>
            </div>
            <div className="rounded-[12px] border border-border px-3 py-3">
              <p className="text-[18px] font-semibold text-primary">{failureCount}</p>
              <p className="text-[12px] text-tertiary">Échoués</p>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button size="sm" variant="secondary" icon={<TestTube2 size={13} />} disabled={runState === 'running' || runningPipelineCount > 0} onClick={handleRunPipeline}>
              {runState === 'running' || runningPipelineCount > 0 ? 'Exécution en cours…' : 'Tester pipeline'}
            </Button>
            <Button size="sm" variant="secondary" icon={<RotateCw size={13} />} onClick={() => setTick((value) => value + 1)}>Rafraîchir</Button>
          </div>
          <p className="mt-3 text-[12px] text-tertiary">Reprise depuis l’étape échouée : non disponible en V1 côté API.</p>
        </div>

        <div className="rounded-[14px] border border-border bg-surface p-4">
          <SectionTitle>Logs agents</SectionTitle>
          {sortedLogs.length === 0 ? (
            <p className="rounded-[12px] border border-border px-3 py-3 text-[14px] text-secondary">Aucun log pipeline disponible.</p>
          ) : (
            <div className="max-h-[168px] overflow-y-auto pr-1">
              {sortedLogs.map((log, index) => renderLog(log, index))}
            </div>
          )}
        </div>
      </div>

      <div className="rounded-[14px] border border-border bg-surface p-4">
        <SectionTitle>Dernières générations</SectionTitle>
        {recentGenerations.length === 0 ? (
          <p className="rounded-[12px] border border-border px-3 py-3 text-[14px] text-secondary">Aucune génération IA tracée pour le moment.</p>
        ) : (
          <div className="overflow-x-auto">
            <div className="min-w-[760px]">
              <div className="grid grid-cols-[1.6fr_0.9fr_0.7fr] gap-3 border-b border-border px-2 pb-2 text-[12px] font-semibold uppercase tracking-wide text-tertiary">
                <span>Contenu</span><span>Statut</span><span>MAJ</span>
              </div>
              {recentGenerations.map((article) => (
                <div key={article.id} className="grid grid-cols-[1.6fr_0.9fr_0.7fr] gap-3 border-b border-border px-2 py-3 text-[12px] last:border-0">
                  <button className="truncate text-left font-medium text-primary hover:text-accent" onClick={() => navigate(`/projects/${projectId}/articles/${article.id}/edit`)}>{article.title}</button>
                  <span className="text-secondary">{workflowStatus(article)}</span>
                  <span className="text-tertiary">{new Date(article.updated_at).toLocaleDateString('fr-FR')}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
