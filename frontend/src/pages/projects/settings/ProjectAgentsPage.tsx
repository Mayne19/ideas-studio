import { useEffect, useState, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { CheckCircle, Loader2, RefreshCw } from 'lucide-react'
import { api } from '@/api/client'
import Button from '@/components/ui/Button'
import Select from '@/components/ui/Select'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'
import ToggleSwitch from '@/components/ui/ToggleSwitch'
import type { AgentInfo, AgentAssignment, AIProviderConfig } from '@/types'

const CATEGORY_LABELS: Record<string, string> = {
  research: 'Recherche',
  strategy: 'Stratégie',
  creation: 'Création',
  review: 'Révision',
}

const CATEGORY_ORDER = ['research', 'strategy', 'creation', 'review']

export default function ProjectAgentsPage() {
  const { projectId } = useParams<{ projectId: string }>()
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
        api.get<AgentInfo[]>(projectId ? `/settings/ai-agents?project_id=${projectId}` : '/settings/ai-agents'),
        api.get<AgentAssignment[]>(projectId ? `/settings/ai-agents/assignments?project_id=${projectId}` : '/settings/ai-agents/assignments').catch(() => [] as AgentAssignment[]),
        api.get<AIProviderConfig[]>(projectId ? `/settings/ai-providers?project_id=${projectId}` : '/settings/ai-providers'),
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

  if (loading) return <LoadingState />
  if (error) return <ErrorState message={error} onRetry={fetchAll} />

  const enabledProviders = providers.filter((p) => p.enabled && p.api_key_configured)

  const groupedAgents = CATEGORY_ORDER.reduce(
    (acc, cat) => {
      acc[cat] = agents.filter((a) => a.category === cat)
      return acc
    },
    {} as Record<string, AgentInfo[]>,
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-[18px] font-semibold text-primary">Agents IA</h2>
          <p className="mt-0.5 text-[13px] text-secondary">
            Assignez un provider IA à chaque agent pour ce projet. Les agents sans assignation utilisent le provider par défaut du projet.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {successMsg && (
            <span className="flex items-center gap-1 text-[13px] text-green-600">
              <CheckCircle size={14} /> {successMsg}
            </span>
          )}
          <Button variant="ghost" size="sm" onClick={fetchAll}>
            <RefreshCw size={14} className="mr-1" /> Rafraîchir
          </Button>
        </div>
      </div>

      <div className="rounded-[14px] border border-border bg-[#f8f9fc] px-4 py-3 text-[13px] text-secondary leading-relaxed">
        <strong className="text-primary">Ordre de résolution :</strong>{' '}
        Assignment du projet &gt; provider par défaut du projet &gt; variable d&apos;environnement.
        Les agents désactivés sont ignorés par le routage IA.
      </div>

      {CATEGORY_ORDER.map((cat) => {
        const catAgents = groupedAgents[cat]
        if (!catAgents || catAgents.length === 0) return null
        return (
          <div key={cat}>
            <h3 className="mb-3 text-[15px] font-semibold text-primary">
              {CATEGORY_LABELS[cat] || cat} ({catAgents.length})
            </h3>
            <div className="space-y-2">
              {catAgents.map((agent) => {
                const ass = getAssignment(agent.agent_id)
                const isSaving = savingId === agent.agent_id
                return (
                  <div
                    key={agent.agent_id}
                    className="rounded-[14px] border border-border bg-surface p-4"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-[14px] font-semibold text-primary">
                            {agent.name}
                          </span>
                          <span className="rounded-full bg-[#f0f0f2] px-2 py-0.5 text-[11px] text-tertiary">
                            {agent.agent_id}
                          </span>
                          {!agent.has_implementation && (
                            <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[11px] text-amber-700">
                              Heuristique uniquement
                            </span>
                          )}
                        </div>
                        <p className="mt-1 text-[13px] text-secondary">{agent.description}</p>
                      </div>

                      <div className="flex items-center gap-3 shrink-0">
                        {ass && (
                          <ToggleSwitch
                            checked={ass.enabled}
                            onChange={() => handleToggle(agent.agent_id, ass.enabled)}
                            disabled={isSaving}
                          />
                        )}

                        <div className="min-w-[180px]">
                          {isSaving ? (
                            <Loader2 size={16} className="animate-spin text-secondary" />
                          ) : (
                            <Select
                              value={ass?.provider_id || ''}
                              onChange={(e) => handleAssign(agent.agent_id, e.target.value)}
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
                      </div>
                    </div>

                    {ass && !ass.enabled && (
                      <p className="mt-2 text-[12px] text-amber-600">
                        Agent désactivé pour ce projet.
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )
}
