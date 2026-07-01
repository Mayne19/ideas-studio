import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { AlertTriangle, Bot, CheckCircle, Euro, History, Loader2, Play, RefreshCw, RotateCw, Settings, TestTube2, XCircle } from '@/components/ui/hugeIcons'
import { listAIProviders } from '@/api/aiProviders'
import { getPipelineLogs, getPipelineSettings, triggerPipelineRun } from '@/api/pipeline'
import { listArticles } from '@/api/articles'
import { api } from '@/api/client'
import type { AIProviderPublic } from '@/api/aiProviders'
import type { PipelineLog, PipelineSettings } from '@/api/pipeline'
import type { AgentAssignment, AgentInfo, Article } from '@/types'
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

function MetricCard({ icon, label, value, tone = 'accent' }: { icon: React.ReactNode; label: string; value: React.ReactNode; tone?: 'accent' | 'success' | 'warning' | 'danger' }) {
  const toneClass = {
    accent: 'bg-accent/10 text-accent',
    success: 'bg-success/8 text-success',
    warning: 'bg-warning/12 text-warning',
    danger: 'bg-danger/10 text-danger',
  }[tone]
  return (
    <div className="rounded-[14px] border border-border bg-surface p-4">
      <span className={`mb-3 flex h-8 w-8 items-center justify-center rounded-[10px] ${toneClass}`}>{icon}</span>
      <p className="text-[20px] font-semibold tracking-tight text-primary">{value}</p>
      <p className="mt-0.5 text-[12px] text-tertiary">{label}</p>
    </div>
  )
}

function articleCost(article: Article) {
  const actual = article.actual_cost_json?.actual_cost_eur
  const estimated = article.estimated_cost_json?.estimated_cost_eur
  const value = typeof actual === 'number' ? actual : typeof estimated === 'number' ? estimated : null
  return value
}

function workflowStatus(article: Article) {
  if (article.workflow_status) return article.workflow_status
  if (article.status === 'failed') return 'failed'
  if (article.next_agent_key) return 'running'
  if (article.completed_agent_keys) return 'completed'
  return 'not_started'
}

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

  const activeProviders = providers.filter((provider) => provider.enabled && provider.api_key_configured)
  const assignedAgentIds = new Set(assignments.filter((item) => item.enabled).map((item) => item.agent_id))
  const workflowArticles = articles.filter((article) => article.workflow_run_id || article.next_agent_key || article.completed_agent_keys || article.workflow_status)
  const failedWorkflows = workflowArticles.filter((article) => workflowStatus(article) === 'failed' || article.status === 'failed')
  const runningWorkflows = workflowArticles.filter((article) => ['running', 'in_progress', 'queued'].includes(workflowStatus(article)) || article.next_agent_key)
  const completedWorkflows = workflowArticles.filter((article) => workflowStatus(article) === 'completed')
  const recentGenerations = useMemo(
    () => [...workflowArticles].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()).slice(0, 8),
    [workflowArticles],
  )
  const recentCost = articles.reduce((sum, article) => sum + (articleCost(article) ?? 0), 0)

  async function handleRunPipeline() {
    if (!projectId) return
    setRunState('running')
    try {
      await triggerPipelineRun(projectId)
      setRunState('done')
      setTick((value) => value + 1)
    } catch {
      setRunState('error')
    }
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
          <Button size="sm" icon={runState === 'running' ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />} loading={runState === 'running'} onClick={handleRunPipeline}>
            Tester le pipeline
          </Button>
        </div>
      </div>

      {runState === 'error' && (
        <div className="mb-4 rounded-[12px] border border-danger/20 bg-danger/5 px-4 py-3 text-[14px] text-danger">Le lancement manuel a échoué. Consultez l’historique ou les providers.</div>
      )}
      {runState === 'done' && (
        <div className="mb-4 rounded-[12px] border border-success/20 bg-success/8 px-4 py-3 text-[14px] text-success">Pipeline lancé. L’historique a été rafraîchi.</div>
      )}

      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <MetricCard icon={<Settings size={18} />} label="Provider actif" value={activeProviders[0]?.label ?? '—'} tone={activeProviders.length ? 'success' : 'warning'} />
        <MetricCard icon={<Bot size={18} />} label="Agents assignés" value={`${assignedAgentIds.size}/${agents.length || '—'}`} tone={assignedAgentIds.size ? 'success' : 'warning'} />
        <MetricCard icon={<RefreshCw size={18} />} label="Pipeline" value={pipeline?.enabled ? 'Actif' : 'Inactif'} tone={pipeline?.enabled ? 'success' : 'warning'} />
        <MetricCard icon={<Euro size={18} />} label="Coût IA suivi" value={recentCost ? `${recentCost.toFixed(4)} €` : '—'} />
        <MetricCard icon={<XCircle size={18} />} label="Workflows échoués" value={failedWorkflows.length} tone={failedWorkflows.length ? 'danger' : 'success'} />
      </div>

      <div className="mb-6 grid gap-4 lg:grid-cols-3">
        <div className="rounded-[14px] border border-border bg-surface p-4">
          <SectionTitle>État du système IA</SectionTitle>
          <div className="flex flex-col gap-2">
            <StatusPill ok={activeProviders.length > 0} label={activeProviders.length ? `${activeProviders.length} provider(s) configuré(s)` : 'Aucun provider actif'} />
            <StatusPill ok={assignedAgentIds.size > 0} label={assignedAgentIds.size ? `${assignedAgentIds.size} agent(s) assigné(s)` : 'Aucun agent assigné'} />
            <StatusPill ok={Boolean(pipeline?.enabled)} label={pipeline?.enabled ? 'Pipeline automatique actif' : 'Pipeline automatique inactif'} />
          </div>
          {activeProviders.length === 0 && (
            <Link to={`/projects/${projectId}/settings/providers`} className="mt-4 inline-flex text-[12px] font-medium text-accent hover:underline">Configurer Gemini ou OpenAI</Link>
          )}
          {assignedAgentIds.size === 0 && (
            <Link to={`/projects/${projectId}/settings/agents`} className="ml-0 mt-2 block text-[12px] font-medium text-accent hover:underline">Assigner les agents IA</Link>
          )}
        </div>

        <div className="rounded-[14px] border border-border bg-surface p-4 lg:col-span-2">
          <SectionTitle>Workflows IA</SectionTitle>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-[12px] bg-surface-soft px-3 py-3">
              <p className="text-[18px] font-semibold text-primary">{runningWorkflows.length}</p>
              <p className="text-[12px] text-tertiary">En cours / bloqués</p>
            </div>
            <div className="rounded-[12px] bg-surface-soft px-3 py-3">
              <p className="text-[18px] font-semibold text-primary">{completedWorkflows.length}</p>
              <p className="text-[12px] text-tertiary">Terminés</p>
            </div>
            <div className="rounded-[12px] bg-surface-soft px-3 py-3">
              <p className="text-[18px] font-semibold text-primary">{failedWorkflows.length}</p>
              <p className="text-[12px] text-tertiary">Échoués</p>
            </div>
          </div>
          <p className="mt-3 text-[12px] text-tertiary">Reprise depuis l’étape échouée : non disponible en V1 côté API.</p>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.25fr)_minmax(360px,0.75fr)]">
        <div className="rounded-[14px] border border-border bg-surface p-4">
          <SectionTitle>Dernières générations</SectionTitle>
          {recentGenerations.length === 0 ? (
            <p className="rounded-[12px] bg-surface-soft px-3 py-3 text-[14px] text-secondary">Aucune génération IA tracée pour le moment.</p>
          ) : (
            <div className="overflow-x-auto">
              <div className="min-w-[860px]">
                <div className="grid grid-cols-[1.5fr_0.7fr_0.7fr_0.9fr_0.6fr_0.7fr_0.7fr] gap-3 border-b border-border px-2 pb-2 text-[12px] font-semibold uppercase tracking-wide text-tertiary">
                  <span>Contenu</span><span>Type</span><span>Statut</span><span>Dernier agent</span><span>Coût</span><span>Modèle</span><span>MAJ</span>
                </div>
                {recentGenerations.map((article) => (
                  <div key={article.id} className="grid grid-cols-[1.5fr_0.7fr_0.7fr_0.9fr_0.6fr_0.7fr_0.7fr] gap-3 border-b border-border px-2 py-3 text-[12px] last:border-0">
                    <button className="truncate text-left font-medium text-primary hover:text-accent" onClick={() => navigate(`/projects/${projectId}/articles/${article.id}/edit`)}>{article.title}</button>
                    <span className="text-secondary">{article.status.includes('idea') ? 'Idée' : 'Article'}</span>
                    <span className="text-secondary">{workflowStatus(article)}</span>
                    <span className="truncate text-secondary">{article.next_agent_key || article.completed_agent_keys?.split(',').at(-1) || '—'}</span>
                    <span className="text-secondary">{articleCost(article) ? `${articleCost(article)?.toFixed(4)} €` : '—'}</span>
                    <span className="text-tertiary">V1 —</span>
                    <span className="text-tertiary">{new Date(article.updated_at).toLocaleDateString('fr-FR')}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="rounded-[14px] border border-border bg-surface p-4">
          <SectionTitle>Logs agents</SectionTitle>
          {logs.length === 0 ? (
            <p className="rounded-[12px] bg-surface-soft px-3 py-3 text-[14px] text-secondary">Aucun log pipeline disponible.</p>
          ) : (
            <div className="flex flex-col gap-2">
              {logs.map((log) => (
                <div key={log.id} className="rounded-[12px] bg-surface-soft px-3 py-2">
                  <div className="flex items-center justify-between gap-3">
                    <span className="flex items-center gap-1.5 text-[12px] font-medium text-primary">
                      <History size={13} />
                      {log.status === 'completed' ? 'Terminé' : 'Échec'}
                    </span>
                    <span className="text-[12px] text-tertiary">{new Date(log.started_at).toLocaleString('fr-FR')}</span>
                  </div>
                  <p className="mt-1 text-[12px] text-tertiary">{log.ideas_generated} idée(s) · {log.articles_created} article(s)</p>
                  {log.errors && <p className="mt-1 text-[12px] text-danger">{log.errors}</p>}
                </div>
              ))}
            </div>
          )}
          <div className="mt-4 rounded-[12px] border border-border bg-surface px-3 py-3 text-[12px] text-secondary">
            <p className="font-medium text-primary">Actions techniques</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <Button size="sm" variant="secondary" icon={<TestTube2 size={13} />} onClick={handleRunPipeline}>Tester pipeline</Button>
              <Button size="sm" variant="secondary" icon={<RotateCw size={13} />} onClick={() => setTick((value) => value + 1)}>Rafraîchir</Button>
            </div>
            <p className="mt-2 text-[12px] text-tertiary">Relance agent bloqué et reprise d’étape : non disponible en V1.</p>
          </div>
        </div>
      </div>

      <div className="mt-6 rounded-[14px] border border-border bg-surface p-4">
        <SectionTitle>Registre agents</SectionTitle>
        {agents.length === 0 ? (
          <p className="rounded-[12px] bg-surface-soft px-3 py-3 text-[14px] text-secondary">Registry agents indisponible ou non exposé par l’API.</p>
        ) : (
          <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
            {agents.slice(0, 12).map((agent) => (
              <div key={agent.agent_id} className="rounded-[12px] bg-surface-soft px-3 py-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-[14px] font-semibold text-primary">{agent.name}</p>
                    <p className="mt-0.5 truncate text-[12px] text-tertiary">{agent.agent_id}</p>
                  </div>
                  <span className="shrink-0 rounded-full bg-surface px-2 py-0.5 text-[12px] text-secondary">{agent.phase || agent.category}</span>
                </div>
                <p className="mt-2 line-clamp-2 text-[12px] leading-snug text-secondary">{agent.description}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
