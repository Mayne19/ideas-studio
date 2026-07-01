import { useEffect, useState, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { CheckCircle, Loader2, RefreshCw } from '@/components/ui/hugeIcons'
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

  const getAssignment = (agentId: string): AgentAssignment | undefined =>
    assignments.find((a) => a.agent_id === agentId)

  const handleAssign = async (agentId: string, providerId: string) => {
    const current = getAssignment(agentId)
    setSavingId(agentId)
    setSuccessMsg(null)
    try {
      if (!providerId) {
        if (current) {
          await api.delete(`/settings/ai-agents/assignments/${current.id}`)
          setAssignments((prev) => prev.filter((a) => a.agent_id !== agentId))
        }
        setSuccessMsg('Agent remis sur le provider par défaut')
        setTimeout(() => setSuccessMsg(null), 2000)
        return
      }
      const result = await api.put<AgentAssignment>('/settings/ai-agents/assignments', {
        agent_id: agentId,
        provider_id: providerId,
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

  const enabledProviders = providers.filter((p) => p.enabled && p.api_key_configured)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-[18px] font-semibold text-primary">Agents IA</h2>
          <p className="mt-0.5 text-[14px] text-secondary">
            Assignez un provider IA à chaque agent pour ce projet. Les agents sans assignation utilisent le provider par défaut du projet.
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
                    <Select
                      value={ass?.provider_id || ''}
                      onChange={(e) => handleAssign(agent.agent_id, e.target.value)}
                      className="!h-8 !px-3 !pr-8 !text-[12px] !font-medium !text-secondary"
                      options={[
                        { value: '', label: 'Provider par défaut' },
                        ...enabledProviders.map((p) => ({
                          value: p.id,
                          label: `${p.label} (${p.provider})`,
                        })),
                      ]}
                    />
                  )}
                </div>
                <div className="flex min-w-0 items-center justify-between gap-3">
                  <div className="min-w-0">
                    {agent.has_implementation ? (
                      <span className="rounded-full bg-success/8 px-2 py-0.5 text-[12px] font-medium text-success">Implémenté</span>
                    ) : (
                      <span className="rounded-full bg-warning/12 px-2 py-0.5 text-[12px] font-medium text-warning">Heuristique</span>
                    )}
                    <p className="mt-1 truncate text-[12px] text-tertiary">
                      {ass ? (ass.enabled ? 'Assigné et actif' : 'Assigné, désactivé') : 'Provider par défaut'}
                    </p>
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
    </div>
  )
}
