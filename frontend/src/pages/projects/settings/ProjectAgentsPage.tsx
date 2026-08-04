import { useEffect, useState, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { Bot, CheckCircle, ChevronDown, ChevronRight, Loader2, RefreshCw } from '@/components/ui/hugeIcons'
import { api } from '@/api/client'
import Button from '@/components/ui/Button'
import Select from '@/components/ui/Select'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'
import ToggleSwitch from '@/components/ui/ToggleSwitch'
import type { AgentInfo, AgentAssignment, AIProviderConfig } from '@/types'
import { useProject } from '@/context/ProjectContext'

const CATEGORY_LABELS: Record<string, string> = {
  research: 'Recherche',
  strategy: 'Stratégie',
  creation: 'Création',
  review: 'Révision',
}

const STATUS_BADGES: Record<string, { label: string; className: string; title: string }> = {
  active: { label: 'Actif', className: 'bg-success/8 text-success', title: 'Implémenté et utilisé par le pipeline' },
  partial: { label: 'Partiel', className: 'bg-warning/12 text-warning', title: 'Implémenté partiellement : dépend d’un service externe à configurer' },
  heuristic: { label: 'Heuristique', className: 'bg-warning/12 text-warning', title: 'Règles internes, sans appel LLM' },
  planned: { label: 'Planifié', className: 'bg-tertiary/12 text-tertiary', title: 'Prévu, pas encore implémenté' },
  not_implemented: { label: 'Non implémenté', className: 'bg-tertiary/12 text-tertiary', title: 'Aucune implémentation : cet agent n’intervient pas dans le pipeline' },
  disabled: { label: 'Désactivé', className: 'bg-tertiary/12 text-tertiary', title: 'Désactivé' },
}

function statusBadge(agent: AgentInfo) {
  return (
    STATUS_BADGES[agent.status] ??
    (agent.has_implementation ? STATUS_BADGES.active : STATUS_BADGES.not_implemented)
  )
}

function AccessDenied() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-error/10">
        <span className="text-2xl text-error">🔒</span>
      </div>
      <h2 className="text-[18px] font-semibold text-primary">Accès réservé aux administrateurs</h2>
      <p className="mt-2 max-w-sm text-[15px] text-secondary">
        La configuration des providers, agents et pipeline est réservée aux owners et admins du projet.
      </p>
    </div>
  )
}

export default function ProjectAgentsPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const { myRole } = useProject()
  const [agents, setAgents] = useState<AgentInfo[]>([])
  const [assignments, setAssignments] = useState<AgentAssignment[]>([])
  const [providers, setProviders] = useState<AIProviderConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [savingId, setSavingId] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)
  const [assignAllOpen, setAssignAllOpen] = useState(false)
  const [assigningAll, setAssigningAll] = useState(false)
  const [assignAllModel, setAssignAllModel] = useState('')
  const [advancedMode, setAdvancedMode] = useState(false)

  const fetchAll = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [agentsData, assignmentsData, providersData] = await Promise.all([
        api.get<AgentInfo[]>(projectId ? `/settings/ai-agents?project_id=${projectId}` : '/settings/ai-agents').catch((err) => {
          setError(err instanceof Error && err.message === 'Not Found' ? "L’API Agents n’est pas disponible sur ce déploiement." : err instanceof Error ? err.message : 'Failed to load agents')
          return [] as AgentInfo[]
        }),
        api.get<AgentAssignment[]>(projectId ? `/settings/ai-agents/assignments?project_id=${projectId}` : '/settings/ai-agents/assignments').catch(() => [] as AgentAssignment[]),
        api.get<AIProviderConfig[]>(projectId ? `/settings/ai-providers?project_id=${projectId}` : '/settings/ai-providers').catch(() => [] as AIProviderConfig[]),
      ])
      setAgents(agentsData)
      setAssignments(assignmentsData)
      setProviders(providersData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    Promise.resolve().then(fetchAll)
  }, [fetchAll])

  const [modelDrafts, setModelDrafts] = useState<Record<string, string>>({})

  const getAssignment = (agentId: string): AgentAssignment | undefined =>
    assignments.find((a) => a.agent_id === agentId)

  const getModelDraft = (agentId: string): string =>
    modelDrafts[agentId] ?? getAssignment(agentId)?.model ?? ''

  const handleAssign = async (agentId: string, providerCode: string, model: string) => {
    const current = getAssignment(agentId)
    setSavingId(agentId)
    setSuccessMsg(null)
    try {
      if (!providerCode) {
        if (current) {
          await api.delete(`/settings/ai-agents/assignments/${current.id}`)
          setAssignments((prev) => prev.filter((a) => a.agent_id !== agentId))
        }
        setSuccessMsg('Agent remis sur le provider par défaut')
        setTimeout(() => setSuccessMsg(null), 2000)
        return
      }
      if (!model.trim()) {
        setError('Indiquez un modèle avant d\'assigner un provider.')
        return
      }
      const result = await api.put<AgentAssignment>('/settings/ai-agents/assignments', {
        agent_id: agentId,
        provider_code: providerCode,
        model: model.trim(),
        project_id: projectId,
        enabled: true,
        priority: 0,
      })
      setAssignments((prev) => {
        const filtered = prev.filter((a) => a.agent_id !== agentId)
        return [...filtered, result]
      })
      setSuccessMsg(`Agent mis à jour`)
      setTimeout(() => setSuccessMsg(null), 2000)
    } catch (err) {
      console.error('Failed to assign agent:', err)
    } finally {
      setSavingId(null)
    }
  }

  const handleAssignAll = async (providerCode: string, model: string) => {
    if (!model.trim()) {
      setError('Indiquez un modèle avant d\'assigner tous les agents.')
      return
    }
    setAssignAllOpen(false)
    setAssigningAll(true)
    setSuccessMsg(null)
    try {
      const results = await Promise.allSettled(
        agents.map((agent) =>
          api.put<AgentAssignment>('/settings/ai-agents/assignments', {
            agent_id: agent.agent_id,
            provider_code: providerCode,
            model: model.trim(),
            project_id: projectId,
            enabled: true,
            priority: 0,
          })
        )
      )
      const failed = results.filter((r) => r.status === 'rejected').length
      await fetchAll()
      setSuccessMsg(failed === 0 ? `${agents.length} agents assignés` : `${agents.length - failed} agents assignés, ${failed} en échec`)
      setTimeout(() => setSuccessMsg(null), 3000)
    } catch (err) {
      console.error('Failed to assign all agents:', err)
    } finally {
      setAssigningAll(false)
    }
  }

  const handleToggle = async (agentId: string, currentEnabled: boolean) => {
    const ass = getAssignment(agentId)
    if (!ass) return
    setSavingId(agentId)
    try {
      await api.patch<AgentAssignment>(`/settings/ai-agents/assignments/${ass.id}`, {
        enabled: !currentEnabled,
      })
      setAssignments((prev) =>
        prev.map((a) => (a.agent_id === agentId ? { ...a, enabled: !currentEnabled } : a))
      )
    } catch (err) {
      console.error('Failed to toggle agent:', err)
    } finally {
      setSavingId(null)
    }
  }

  if (myRole !== null && myRole !== 'owner' && myRole !== 'admin') {
    return <AccessDenied />
  }

  if (loading) return <LoadingState />
  if (error && agents.length === 0) {
    return (
      <div className="flex flex-col gap-4">
        <ErrorState message={error} onRetry={fetchAll} />
        <div className="rounded-[14px] border border-border bg-surface p-4 text-[14px] text-secondary">
          La page reste accessible aux owners/admins. Déployez le backend à jour si le registry agents n’est pas exposé.
        </div>
      </div>
    )
  }

  const enabledProviders = providers.filter((p) => p.api_key_configured)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-[18px] font-semibold text-primary">Agents IA</h2>
          <p className="mt-0.5 text-[14px] text-secondary">
            Tous les agents utilisent le provider connecté dans Paramètres → Providers. Le mode avancé permet
            d'assigner un provider et un modèle différents à un agent spécifique, si besoin.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {successMsg && (
            <span className="flex items-center gap-1 text-[14px] text-success">
              <CheckCircle size={14} /> {successMsg}
            </span>
          )}
          <Button variant="ghost" size="sm" onClick={fetchAll}>
            <RefreshCw size={14} className="mr-1" /> Rafraîchir
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-[12px] border border-warning/20 bg-warning/5 px-4 py-3 text-[14px] text-secondary">
          {error}
        </div>
      )}

      <button
        type="button"
        onClick={() => setAdvancedMode((v) => !v)}
        className="flex w-fit items-center gap-1.5 text-[13px] font-medium text-secondary transition-colors hover:text-primary"
      >
        {advancedMode ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        Mode avancé (provider/modèle par agent)
      </button>

      {!advancedMode && (
        <div className="overflow-x-auto rounded-[16px] bg-surface">
          <div className="min-w-[600px]">
            <div className="grid grid-cols-[1.1fr_1.8fr_1fr] gap-4 border-b border-border px-4 py-3 text-[12px] font-semibold uppercase tracking-wide text-tertiary">
              <span>Agent</span>
              <span>Mission</span>
              <span>État</span>
            </div>
            {agents.map((agent) => {
              const ass = getAssignment(agent.agent_id)
              return (
                <div key={agent.agent_id} className="grid grid-cols-[1.1fr_1.8fr_1fr] items-center gap-4 border-b border-border px-4 py-3 text-[12px] last:border-0">
                  <div className="min-w-0">
                    <p className="truncate font-semibold text-primary">{agent.name}</p>
                    <p className="mt-0.5 truncate text-[12px] text-tertiary">{CATEGORY_LABELS[agent.category] ?? agent.category}</p>
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-secondary" title={agent.description}>{agent.description}</p>
                  </div>
                  <div className="min-w-0">
                    <span
                      className={`rounded-full px-2 py-0.5 text-[12px] font-medium ${statusBadge(agent).className}`}
                      title={ass ? `Override : ${ass.provider_code} / ${ass.model}` : statusBadge(agent).title}
                    >
                      {statusBadge(agent).label}
                    </span>
                    {ass && <span className="ml-1.5 text-[11px] text-tertiary">override actif</span>}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {advancedMode && (
        <>
          <div className="flex items-center justify-end">
            <div className="relative">
              <Button
                variant="ghost"
                size="sm"
                disabled={assigningAll || enabledProviders.length === 0}
                onClick={() => setAssignAllOpen((open) => !open)}
                title={enabledProviders.length === 0 ? 'Aucun provider actif configuré' : 'Assigner tous les agents au même provider'}
              >
                {assigningAll ? <Loader2 size={14} className="mr-1 animate-spin" /> : <Bot size={14} className="mr-1" />}
                Tout assigner
              </Button>
              {assignAllOpen && (
                <>
                  <button
                    type="button"
                    aria-label="Fermer"
                    className="fixed inset-0 z-10 cursor-default"
                    onClick={() => setAssignAllOpen(false)}
                  />
                  <div className="absolute right-0 z-20 mt-1 w-72 rounded-[12px] border border-border bg-surface p-2 shadow-lg">
                    <p className="px-1 py-1 text-[11px] font-semibold uppercase tracking-wide text-tertiary">
                      Assigner tous les agents à
                    </p>
                    <input
                      value={assignAllModel}
                      onChange={(e) => setAssignAllModel(e.target.value)}
                      placeholder="Modèle (ex: gpt-5)"
                      className="mb-1 w-full rounded-[8px] border border-border bg-transparent px-2.5 py-1.5 text-[12px] text-primary outline-none focus:border-accent"
                    />
                    {enabledProviders.map((p) => (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => handleAssignAll(p.provider, assignAllModel)}
                        disabled={!assignAllModel.trim()}
                        className="block w-full rounded-[8px] px-3 py-2 text-left text-[13px] text-primary transition-colors hover:bg-surface-soft disabled:opacity-40"
                      >
                        {p.label} <span className="text-tertiary">({p.provider})</span>
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>

          <div className="overflow-x-auto rounded-[16px] bg-surface">
            <div className="min-w-[860px]">
              <div className="grid grid-cols-[1.1fr_1.8fr_1.15fr_1fr] gap-4 border-b border-border px-4 py-3 text-[12px] font-semibold uppercase tracking-wide text-tertiary">
                <span>Agent</span>
                <span>Mission</span>
                <span>Provider IA</span>
                <span>État</span>
              </div>
              {agents.map((agent) => {
                const ass = getAssignment(agent.agent_id)
                const isSaving = savingId === agent.agent_id
                return (
                  <div key={agent.agent_id} className="grid grid-cols-[1.1fr_1.8fr_1.15fr_1fr] items-center gap-4 border-b border-border px-4 py-3 text-[12px] last:border-0">
                    <div className="min-w-0">
                      <p className="truncate font-semibold text-primary">{agent.name}</p>
                      <p className="mt-0.5 truncate text-[12px] text-tertiary">{CATEGORY_LABELS[agent.category] ?? agent.category}</p>
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-secondary" title={agent.description}>{agent.description}</p>
                      <p className="mt-0.5 truncate text-[12px] text-tertiary">{agent.agent_id}</p>
                    </div>
                    <div>
                      {isSaving ? (
                        <Loader2 size={16} className="animate-spin text-secondary" />
                      ) : (
                        <div className="flex flex-col gap-1.5">
                          <Select
                            value={ass?.provider_code || ''}
                            onChange={(e) => handleAssign(agent.agent_id, e.target.value, getModelDraft(agent.agent_id))}
                            className="!h-8 !px-3 !pr-8 !text-[12px] !font-medium !text-secondary"
                            options={[
                              { value: '', label: 'Provider par défaut' },
                              ...enabledProviders.map((p) => ({
                                value: p.provider,
                                label: `${p.label} (${p.provider})`,
                              })),
                            ]}
                          />
                          <input
                            value={getModelDraft(agent.agent_id)}
                            onChange={(e) => setModelDrafts((prev) => ({ ...prev, [agent.agent_id]: e.target.value }))}
                            placeholder="Modèle (ex: gpt-5)"
                            className="h-7 rounded-[7px] border border-border bg-transparent px-2 text-[11px] text-primary outline-none focus:border-accent"
                          />
                        </div>
                      )}
                    </div>
                    <div className="flex min-w-0 items-center justify-between gap-3">
                      <div className="min-w-0">
                        <span
                          className={`rounded-full px-2 py-0.5 text-[12px] font-medium ${statusBadge(agent).className}`}
                          title={statusBadge(agent).title}
                        >
                          {statusBadge(agent).label}
                        </span>
                      </div>
                      {ass && (
                        <ToggleSwitch checked={ass.enabled} onChange={() => handleToggle(agent.agent_id, ass.enabled)} disabled={isSaving} />
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
