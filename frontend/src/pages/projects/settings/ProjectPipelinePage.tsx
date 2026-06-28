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

const DAYS = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']
const DAYS_EN = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

function dayLabel(fr: string): string {
  return fr.charAt(0).toUpperCase() + fr.slice(1)
}

const HOURS = Array.from({ length: 24 }, (_, i) => i)

function hourLabel(h: number): string {
  return `${h.toString().padStart(2, '0')}:00`
}

const ARTICLES_OPTIONS = [1, 2, 3, 5, 7, 10, 15, 20]

function AccessDenied() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-error/10">
        <span className="text-2xl text-error">🔒</span>
      </div>
      <h2 className="text-[18px] font-semibold text-primary">Accès réservé aux administrateurs</h2>
      <p className="mt-2 max-w-sm text-[14px] text-secondary">
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

  // Editable local state
  const [enabled, setEnabled] = useState(false)
  const [activeDays, setActiveDays] = useState<string[]>([])
  const [launchHour, setLaunchHour] = useState(8)
  const [articlesPerWeek, setArticlesPerWeek] = useState(5)
  const [costLimitPerArticle, setCostLimitPerArticle] = useState('')

  const [loadTrigger, setLoadTrigger] = useState(0)

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
        setActiveDays(s.active_days)
        setLaunchHour(s.launch_hour)
        setArticlesPerWeek(s.articles_per_week)
        setCostLimitPerArticle(s.cost_limit_per_article_eur == null ? '' : String(s.cost_limit_per_article_eur))
        setLogs(l)
        setLoadStatus('success')
        setLoadError('')
        setDirty(false)
      })
      .catch((err) => {
        if (!cancelled) {
          setLoadError(err instanceof Error && err.message === 'Not Found' ? "L’API Pipeline n’est pas disponible sur ce déploiement." : err instanceof Error ? err.message : '')
          setLoadStatus('error')
        }
      })
    return () => { cancelled = true }
  }, [projectId, loadTrigger])

  function toggleDay(dayEn: string) {
    setActiveDays((prev) =>
      prev.includes(dayEn) ? prev.filter((d) => d !== dayEn) : [...prev, dayEn]
    )
    setDirty(true)
  }

  async function handleSave() {
    if (!projectId) return
    setSaving(true)
    setSaveStatus('idle')
    try {
      const updated = await updatePipelineSettings(projectId, {
        enabled,
        active_days: activeDays,
        launch_hour: launchHour,
        articles_per_week: articlesPerWeek,
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
      setRunStatus('Erreur lors de l\'exécution')
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
        <div className="rounded-[8px] border border-border bg-surface p-4 text-[13px] text-secondary">
          Les owners/admins doivent pouvoir accéder à cette page. Si ce message apparaît en production, le backend déployé n’inclut pas encore les endpoints Pipeline.
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <Card padding="sm">
        <p className="text-[13px] font-medium text-primary">Flux éditorial automatique</p>
        <p className="mt-1 text-[12px] leading-relaxed text-secondary">
          Les catégories et leurs fréquences alimentent la génération d'idées, puis la validation humaine déclenche la production,
          la rédaction, la relecture et la planification. Ideas Studio ne publie pas automatiquement sans validation humaine.
        </p>
        <div className="mt-3 grid gap-2 text-[11px] text-secondary sm:grid-cols-5">
          {['Catégories', 'Idées', 'Validation', 'Production', 'Publication'].map((step) => (
            <span key={step} className="rounded-[6px] bg-surface-soft px-3 py-2 text-center font-medium">{step}</span>
          ))}
        </div>
      </Card>

      {/* Enable toggle */}
      <Card padding="sm">
        <p className="text-[13px] font-medium text-primary">Volume éditorial</p>
        <p className="mt-0.5 text-[12px] text-tertiary">
          {settings?.total_monthly_from_categories ?? 0} article(s)/mois calculé(s) depuis les catégories actives.
        </p>
        {settings?.categories_frequencies && settings.categories_frequencies.length > 0 && (
          <div className="mt-3 grid grid-cols-2 gap-1.5 border-t border-border pt-3 sm:grid-cols-3 md:grid-cols-4">
            {settings.categories_frequencies.map((category) => (
              <div key={category.id} className="flex items-center justify-between rounded-[6px] bg-surface px-2.5 py-1.5 text-[12px]">
                <span className="text-primary truncate">{category.name}</span>
                <span className={category.pipeline_enabled === false ? 'text-tertiary shrink-0 ml-2' : 'text-secondary shrink-0 ml-2'}>
                  {category.pipeline_enabled === false ? 'désactivée' : `${category.monthly_frequency ?? 0}/mois`}
                </span>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card padding="sm">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[13px] font-medium text-primary">Pipeline automatique</p>
            <p className="mt-0.5 text-[12px] text-tertiary">
              Planifiez les automatisations éditoriales du projet.
            </p>
          </div>
          <ToggleSwitch
            checked={enabled}
            onChange={(next) => {
              setEnabled(next)
              setDirty(true)
            }}
            ariaLabel="Activer le pipeline automatique"
          />
        </div>
        {enabled && (
          <p className="mt-3 text-[12px] text-secondary leading-snug border-t border-border pt-3">
            Le pipeline prépare le contenu dans Ideas Studio. La publication reste toujours une action humaine.
          </p>
        )}
      </Card>

      <Card padding="sm" className="!rounded-[8px]">
        <p className="text-[12px] text-secondary">
          {settings?.automation_notes || 'Automatisation non confirmée. Le lancement manuel reste disponible.'}
        </p>
      </Card>

      {enabled && (
        <>
          {/* Schedule */}
          <Card padding="sm">
            <p className="mb-3 text-[13px] font-medium text-primary">Planification</p>

            <div className="mb-3">
              <p className="mb-1.5 text-[12px] text-secondary">Jours actifs</p>
              <div className="flex flex-wrap gap-1.5">
                {DAYS.map((dayFr, i) => {
                  const dayEn = DAYS_EN[i]
                  const active = activeDays.includes(dayEn)
                  return (
                    <button
                      key={dayEn}
                      type="button"
                      onClick={() => toggleDay(dayEn)}
                      className={`rounded-[8px] px-2.5 py-1 text-[11px] font-medium transition-colors ${
                        active
                          ? 'bg-primary text-bg'
                          : 'border border-border bg-surface-soft text-secondary hover:bg-surface-muted'
                      }`}
                    >
                      {dayLabel(dayFr)}
                    </button>
                  )
                })}
              </div>
              {activeDays.length === 0 && (
                <p className="mt-1 text-[11px] text-tertiary">Aucun jour sélectionné = tous les jours actifs</p>
              )}
            </div>

            <div className="mb-3">
              <label className="mb-1 block text-[12px] text-secondary">Heure de lancement</label>
              <select
                value={launchHour}
                onChange={(e) => { setLaunchHour(Number(e.target.value)); setDirty(true) }}
                className="rounded-[8px] border border-border bg-surface-soft px-2.5 py-1.5 text-[12px] text-primary"
              >
                {HOURS.map((h) => (
                  <option key={h} value={h}>{hourLabel(h)}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1 block text-[12px] text-secondary">Cadence de sécurité hebdomadaire</label>
              <select
                value={articlesPerWeek}
                onChange={(e) => { setArticlesPerWeek(Number(e.target.value)); setDirty(true) }}
                className="rounded-[8px] border border-border bg-surface-soft px-2.5 py-1.5 text-[12px] text-primary"
              >
                {ARTICLES_OPTIONS.map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
              <p className="mt-1 text-[11px] text-tertiary">
                Le volume éditorial vient des catégories. Cette valeur limite l'exécution hebdomadaire du pipeline.
              </p>
            </div>

            <div className="mt-3">
              <label className="mb-1 block text-[12px] text-secondary">Limite coût IA par article (€)</label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={costLimitPerArticle}
                onChange={(e) => { setCostLimitPerArticle(e.target.value); setDirty(true) }}
                placeholder="Ex. 1.50"
                className="w-full rounded-[8px] border border-border bg-surface-soft px-2.5 py-1.5 text-[12px] text-primary"
              />
            </div>
          </Card>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              onClick={handleSave}
              disabled={saving || !dirty}
              loading={saving}
              icon={!saving ? <RotateCw size={13} /> : undefined}
            >
              {saveStatus === 'saved' ? 'Enregistré' : 'Enregistrer'}
            </Button>
            {saveStatus === 'error' && <p className="text-[12px] text-danger">Erreur</p>}

            <Button
              size="sm"
              variant="secondary"
              onClick={handleRun}
              disabled={running}
              loading={running}
              icon={!running ? <Play size={13} /> : undefined}
            >
              Exécuter maintenant
            </Button>
          </div>
          {runStatus && <p className="text-[12px] text-secondary">{runStatus}</p>}

          {/* Execution history */}
          <Card padding="sm">
            <div className="flex items-center gap-1.5 mb-3">
              <History size={14} className="text-tertiary" />
              <p className="text-[13px] font-medium text-primary">Historique d'exécution</p>
            </div>
            {logs.length === 0 ? (
              <p className="text-[12px] text-tertiary">Aucune exécution pour le moment.</p>
            ) : (
              <div className="flex flex-col gap-1.5">
                {logs.map((log) => (
                  <div key={log.id} className="flex items-center justify-between rounded-[6px] bg-surface-soft px-3 py-2">
                    <div>
                      <p className="text-[11px] text-primary">
                        {new Date(log.started_at).toLocaleDateString('fr-FR', {
                          day: 'numeric', month: 'short', year: 'numeric',
                          hour: '2-digit', minute: '2-digit',
                        })}
                      </p>
                      <p className="text-[11px] text-tertiary">
                        {log.ideas_generated} idée(s) · {log.articles_created} article(s)
                      </p>
                    </div>
                    <span className={`text-[11px] font-medium ${
                      log.status === 'completed' ? 'text-success' : 'text-danger'
                    }`}>
                      {log.status === 'completed' ? 'OK' : 'Échec'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </>
      )}

      {!enabled && (
        <Card padding="sm">
          <p className="text-[12px] text-tertiary">
            Activez le pipeline automatique puis enregistrez pour configurer la planification et voir l'historique.
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              onClick={handleSave}
              disabled={saving || !dirty}
              loading={saving}
              icon={!saving ? <RotateCw size={13} /> : undefined}
            >
              {saveStatus === 'saved' ? 'Enregistré' : 'Enregistrer'}
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={handleRun}
              disabled={running}
              loading={running}
              icon={!running ? <Play size={13} /> : undefined}
            >
              Exécuter maintenant
            </Button>
            {saveStatus === 'error' && <p className="text-[12px] text-danger">Erreur</p>}
          </div>
          {runStatus && <p className="mt-2 text-[12px] text-secondary">{runStatus}</p>}
        </Card>
      )}
    </div>
  )
}
