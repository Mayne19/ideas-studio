import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Play, RotateCw, History } from '@/components/ui/hugeIcons'
import { getPipelineSettings, updatePipelineSettings, triggerPipelineRun, getPipelineLogs } from '@/api/pipeline'
import type { PipelineLog, PipelineSettings } from '@/api/pipeline'
import { Card } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'
import ToggleSwitch from '@/components/ui/ToggleSwitch'
import { useProject } from '@/context/ProjectContext'

const HOURS = Array.from({ length: 24 }, (_, i) => i)
const DAYS = Array.from({ length: 31 }, (_, i) => i + 1)

function hourLabel(h: number): string {
  return `${String(h).padStart(2, '0')}h00`
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

export default function ProjectPipelinePage() {
  const { projectId } = useParams<{ projectId: string }>()
  const { myRole } = useProject()
  const [logs, setLogs] = useState<PipelineLog[]>([])
  const [settings, setSettings] = useState<PipelineSettings | null>(null)
  const [loadStatus, setLoadStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [saving, setSaving] = useState(false)
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saved' | 'error'>('idle')
  const [running, setRunning] = useState(false)
  const [runStatus, setRunStatus] = useState<string | null>(null)
  const [dirty, setDirty] = useState(false)
  const [loadError, setLoadError] = useState('')
  const [loadTrigger, setLoadTrigger] = useState(0)

  // Editable local state
  const [enabled, setEnabled] = useState(false)
  const [launchHour, setLaunchHour] = useState(8)
  const [ideasDayOfMonth, setIdeasDayOfMonth] = useState(25)
  const [publishHourStart, setPublishHourStart] = useState(8)
  const [publishHourEnd, setPublishHourEnd] = useState(10)
  const [costLimitPerArticle, setCostLimitPerArticle] = useState('')

  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    Promise.all([
      getPipelineSettings(projectId),
      getPipelineLogs(projectId, 10).catch(() => []),
    ])
      .then(([s, l]) => {
        if (cancelled) return
        setEnabled(s.enabled)
        setSettings(s)
        setLaunchHour(s.launch_hour)
        setIdeasDayOfMonth(s.ideas_day_of_month ?? 25)
        setPublishHourStart(s.publish_hour_start ?? 8)
        setPublishHourEnd(s.publish_hour_end ?? 10)
        setCostLimitPerArticle(s.cost_limit_per_article_eur == null ? '' : String(s.cost_limit_per_article_eur))
        setLogs(l)
        setLoadStatus('success')
        setLoadError('')
        setDirty(false)
      })
      .catch((err) => {
        if (!cancelled) {
          setLoadError(
            err instanceof Error && err.message === 'Not Found'
              ? "L'API Pipeline n'est pas disponible sur ce déploiement."
              : err instanceof Error ? err.message : ''
          )
          setLoadStatus('error')
        }
      })
    return () => { cancelled = true }
  }, [projectId, loadTrigger])

  async function handleSave() {
    if (!projectId) return
    setSaving(true)
    setSaveStatus('idle')
    try {
      const updated = await updatePipelineSettings(projectId, {
        enabled,
        launch_hour: launchHour,
        ideas_day_of_month: ideasDayOfMonth,
        publish_hour_start: publishHourStart,
        publish_hour_end: publishHourEnd,
        cost_limit_per_article_eur: costLimitPerArticle.trim() === '' ? null : Number(costLimitPerArticle),
      })
      setSettings(updated)
      setDirty(false)
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus('idle'), 3000)
    } catch {
      setSaveStatus('error')
    } finally {
      setSaving(false)
    }
  }

  async function handleRun() {
    if (!projectId) return
    setRunning(true)
    setRunStatus(null)
    try {
      const result = await triggerPipelineRun(projectId)
      setRunStatus(result.status === 'completed' ? 'Exécution terminée' : `Échec : ${result.status}`)
      getPipelineLogs(projectId, 10).then(setLogs).catch(() => {})
    } catch {
      setRunStatus("Erreur lors de l'exécution")
    } finally {
      setRunning(false)
    }
  }

  if (loadStatus === 'loading') return <LoadingState />

  function handleRetry() {
    setLoadStatus('loading')
    setLoadTrigger((n) => n + 1)
  }

  if (myRole !== null && myRole !== 'owner' && myRole !== 'admin') {
    return <AccessDenied />
  }

  if (loadStatus === 'error') {
    return (
      <div className="flex flex-col gap-4">
        <ErrorState message={loadError || 'Impossible de charger le pipeline.'} onRetry={handleRetry} />
        <div className="rounded-[14px] border border-border bg-surface p-4 text-[14px] text-secondary">
          Les owners/admins doivent pouvoir accéder à cette page. Si ce message apparaît en production, le backend déployé n'inclut pas encore les endpoints Pipeline.
        </div>
      </div>
    )
  }

  const totalMonthly = settings?.total_monthly_from_categories ?? 0

  return (
    <div className="flex flex-col gap-6">

      {/* Toggle pipeline */}
      <Card padding="sm">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[14px] font-medium text-primary">Pipeline automatique</p>
            <p className="mt-0.5 text-[12px] text-tertiary">
              Le système génère et prépare le contenu. La publication reste une action humaine.
            </p>
          </div>
          <ToggleSwitch
            checked={enabled}
            onChange={(next) => { setEnabled(next); setDirty(true) }}
            ariaLabel="Activer le pipeline automatique"
          />
        </div>
      </Card>

      {/* Volume éditorial */}
      <Card padding="sm">
        <p className="text-[14px] font-medium text-primary">Volume éditorial</p>
        <p className="mt-0.5 text-[13px] text-secondary">
          <span className="font-semibold text-primary">{totalMonthly}</span> articles/mois
          — calculés depuis vos catégories actives
        </p>
        {settings?.categories_frequencies && settings.categories_frequencies.length > 0 && (
          <div className="mt-3 grid grid-cols-2 gap-1.5 border-t border-border pt-3 sm:grid-cols-3">
            {settings.categories_frequencies.map((cat) => (
              <div key={cat.id} className="flex items-center justify-between rounded-[8px] bg-surface-soft px-2.5 py-1.5 text-[12px]">
                <span className="truncate text-primary">{cat.name}</span>
                <span className="ml-2 shrink-0 text-secondary">
                  {cat.pipeline_enabled === false ? 'désactivée' : `${cat.monthly_frequency ?? 0}/mois`}
                </span>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Planification (visible seulement si activé) */}
      {enabled && (
        <Card padding="sm">
          <p className="mb-4 text-[14px] font-medium text-primary">Planification</p>

          {/* Génération des idées */}
          <div className="mb-4">
            <p className="mb-1.5 text-[12px] font-medium text-secondary">Génération des idées</p>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[12px] text-tertiary">Le</span>
              <select
                value={ideasDayOfMonth}
                onChange={(e) => { setIdeasDayOfMonth(Number(e.target.value)); setDirty(true) }}
                className="h-9 rounded-[8px] border border-border bg-transparent px-2.5 text-[12px] text-primary"
              >
                {DAYS.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
              <span className="text-[12px] text-tertiary">de chaque mois à</span>
              <select
                value={launchHour}
                onChange={(e) => { setLaunchHour(Number(e.target.value)); setDirty(true) }}
                className="h-9 rounded-[8px] border border-border bg-transparent px-2.5 text-[12px] text-primary"
              >
                {HOURS.map((h) => (
                  <option key={h} value={h}>{hourLabel(h)}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Plage de publication */}
          <div className="mb-4">
            <p className="mb-1.5 text-[12px] font-medium text-secondary">Plage de publication</p>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[12px] text-tertiary">Entre</span>
              <select
                value={publishHourStart}
                onChange={(e) => { setPublishHourStart(Number(e.target.value)); setDirty(true) }}
                className="h-9 rounded-[8px] border border-border bg-transparent px-2.5 text-[12px] text-primary"
              >
                {HOURS.map((h) => (
                  <option key={h} value={h}>{hourLabel(h)}</option>
                ))}
              </select>
              <span className="text-[12px] text-tertiary">et</span>
              <select
                value={publishHourEnd}
                onChange={(e) => { setPublishHourEnd(Number(e.target.value)); setDirty(true) }}
                className="h-9 rounded-[8px] border border-border bg-transparent px-2.5 text-[12px] text-primary"
              >
                {HOURS.map((h) => (
                  <option key={h} value={h}>{hourLabel(h)}</option>
                ))}
              </select>
              <span className="text-[12px] text-tertiary">— le système choisit l'heure dans cette plage</span>
            </div>
          </div>

          {/* Limite coût */}
          <div>
            <p className="mb-1.5 text-[12px] font-medium text-secondary">Limite coût IA par article</p>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="0"
                step="0.01"
                value={costLimitPerArticle}
                onChange={(e) => { setCostLimitPerArticle(e.target.value); setDirty(true) }}
                placeholder="Aucune limite"
                className="h-9 w-32 rounded-[8px] border border-border bg-transparent px-2.5 text-[12px] text-primary placeholder:text-tertiary focus:outline-none focus:ring-1 focus:ring-accent/50"
              />
              <span className="text-[12px] text-tertiary">€ — laisser vide = pas de limite</span>
            </div>
          </div>
        </Card>
      )}

      {/* Boutons d'action */}
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          onClick={handleSave}
          disabled={saving || !dirty}
          loading={saving}
          icon={!saving ? <RotateCw size={13} /> : undefined}
          className="border-primary bg-primary text-bg hover:opacity-90 disabled:border-border disabled:bg-surface-muted disabled:text-tertiary"
        >
          {saveStatus === 'saved' ? 'Enregistré ✓' : 'Enregistrer'}
        </Button>
        <Button
          size="sm"
          variant="secondary"
          onClick={handleRun}
          disabled={running}
          loading={running}
          icon={!running ? <Play size={13} /> : undefined}
          className="border-border bg-transparent text-primary hover:bg-surface-soft"
        >
          Lancer maintenant
        </Button>
        {saveStatus === 'error' && <p className="text-[12px] text-danger">Erreur lors de l'enregistrement</p>}
        {runStatus && <p className="text-[12px] text-secondary">{runStatus}</p>}
      </div>

      {/* Historique d'exécution */}
      <Card padding="sm">
        <div className="mb-3 flex items-center gap-1.5">
          <History size={14} className="text-tertiary" />
          <p className="text-[14px] font-medium text-primary">Historique d'exécution</p>
        </div>
        {logs.length === 0 ? (
          <p className="text-[12px] text-tertiary">Aucune exécution pour le moment.</p>
        ) : (
          <div className="flex flex-col gap-1.5">
            {logs.map((log) => (
              <div key={log.id} className="flex items-center justify-between rounded-[8px] bg-surface-soft px-3 py-2">
                <div>
                  <p className="text-[12px] text-primary">
                    {new Date(log.started_at).toLocaleDateString('fr-FR', {
                      day: 'numeric', month: 'short', year: 'numeric',
                      hour: '2-digit', minute: '2-digit',
                    })}
                  </p>
                  <p className="text-[12px] text-tertiary">
                    {log.ideas_generated} idée(s) · {log.articles_created} article(s)
                  </p>
                </div>
                <span className={`text-[12px] font-medium ${log.status === 'completed' ? 'text-success' : 'text-danger'}`}>
                  {log.status === 'completed' ? 'OK' : 'Échec'}
                </span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
