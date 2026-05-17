import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Play, RotateCw, History, Loader2 } from 'lucide-react'
import { getPipelineSettings, updatePipelineSettings, triggerPipelineRun, getPipelineLogs } from '@/api/pipeline'
import type { PipelineLog } from '@/api/pipeline'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'

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

export default function ProjectPipelinePage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [logs, setLogs] = useState<PipelineLog[]>([])
  const [loadStatus, setLoadStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [saving, setSaving] = useState(false)
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saved' | 'error'>('idle')
  const [running, setRunning] = useState(false)
  const [runStatus, setRunStatus] = useState<string | null>(null)
  const [dirty, setDirty] = useState(false)

  // Editable local state
  const [enabled, setEnabled] = useState(false)
  const [activeDays, setActiveDays] = useState<string[]>([])
  const [launchHour, setLaunchHour] = useState(8)
  const [articlesPerWeek, setArticlesPerWeek] = useState(5)

  const [loadTrigger, setLoadTrigger] = useState(0)

  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    Promise.all([
      getPipelineSettings(projectId),
      getPipelineLogs(projectId, 10),
    ])
      .then(([s, l]) => {
        if (cancelled) return
        setEnabled(s.enabled)
        setActiveDays(s.active_days)
        setLaunchHour(s.launch_hour)
        setArticlesPerWeek(s.articles_per_week)
        setLogs(l)
        setLoadStatus('success')
        setDirty(false)
      })
      .catch(() => {
        if (!cancelled) setLoadStatus('error')
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
      await updatePipelineSettings(projectId, {
        enabled,
        active_days: activeDays,
        launch_hour: launchHour,
        articles_per_week: articlesPerWeek,
      })
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

  if (loadStatus === 'error') return <ErrorState onRetry={handleRetry} />

  return (
    <div className="flex flex-col gap-6">
      {/* Enable toggle */}
      <div className="rounded-[16px] bg-surface p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[13px] font-medium text-primary">Pipeline automatique</p>
            <p className="mt-0.5 text-[12px] text-tertiary">
              Génération automatique d'idées uniquement pour l'instant, selon votre planification.
            </p>
          </div>
          <label className="relative inline-flex h-5 w-9 cursor-pointer items-center">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => { setEnabled(e.target.checked); setDirty(true) }}
              className="peer sr-only"
            />
            <span className="absolute inset-0 rounded-full bg-[#d1d1d6] transition-colors peer-checked:bg-accent" />
            <span className="absolute left-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition-transform peer-checked:translate-x-4" />
          </label>
        </div>
        {enabled && (
          <p className="mt-3 text-[12px] text-secondary leading-snug border-t border-border pt-3">
            Le pipeline génère des idées uniquement pour l'instant. Il ne publie jamais automatiquement,
            et les priorités par catégorie ne sont pas encore appliquées à la sélection.
          </p>
        )}
      </div>

      {enabled && (
        <>
          {/* Schedule */}
          <div className="rounded-[16px] bg-surface p-4">
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
                          ? 'bg-accent text-white'
                          : 'border border-border bg-[#f5f5f7] text-secondary hover:bg-[#ebebed]'
                      }`}
                    >
                      {dayLabel(dayFr)}
                    </button>
                  )
                })}
              </div>
              {activeDays.length === 0 && (
                <p className="mt-1 text-[11px] text-tertiary">Aucun jour sélectionné = tous les jours</p>
              )}
            </div>

            <div className="mb-3">
              <label className="mb-1 block text-[12px] text-secondary">Heure de lancement</label>
              <select
                value={launchHour}
                onChange={(e) => { setLaunchHour(Number(e.target.value)); setDirty(true) }}
                className="rounded-[8px] border border-border bg-[#f5f5f7] px-2.5 py-1.5 text-[12px] text-primary"
              >
                {HOURS.map((h) => (
                  <option key={h} value={h}>{hourLabel(h)}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1 block text-[12px] text-secondary">Articles par semaine</label>
              <select
                value={articlesPerWeek}
                onChange={(e) => { setArticlesPerWeek(Number(e.target.value)); setDirty(true) }}
                className="rounded-[8px] border border-border bg-[#f5f5f7] px-2.5 py-1.5 text-[12px] text-primary"
              >
                {ARTICLES_OPTIONS.map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleSave}
              disabled={saving || !dirty}
              className="flex items-center gap-1.5 rounded-[10px] bg-accent px-4 py-2 text-[12px] font-medium text-white transition-colors hover:bg-accent/90 disabled:opacity-50"
            >
              {saving ? <Loader2 size={13} className="animate-spin" /> : <RotateCw size={13} />}
              {saveStatus === 'saved' ? 'Enregistré' : 'Enregistrer'}
            </button>
            {saveStatus === 'error' && <p className="text-[12px] text-danger">Erreur</p>}

            <button
              type="button"
              onClick={handleRun}
              disabled={running}
              className="flex items-center gap-1.5 rounded-[10px] border border-border bg-surface px-4 py-2 text-[12px] font-medium text-secondary transition-colors hover:bg-[#f0f0f2] disabled:opacity-50"
            >
              {running ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
              Exécuter maintenant
            </button>
          </div>
          {runStatus && <p className="text-[12px] text-secondary">{runStatus}</p>}

          {/* Execution history */}
          <div className="rounded-[16px] bg-surface p-4">
            <div className="flex items-center gap-1.5 mb-3">
              <History size={14} className="text-tertiary" />
              <p className="text-[13px] font-medium text-primary">Historique d'exécution</p>
            </div>
            {logs.length === 0 ? (
              <p className="text-[12px] text-tertiary">Aucune exécution pour le moment.</p>
            ) : (
              <div className="flex flex-col gap-1.5">
                {logs.map((log) => (
                  <div key={log.id} className="flex items-center justify-between rounded-[8px] bg-[#f5f5f7] px-3 py-2">
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
                      log.status === 'completed' ? 'text-[#1a7a3a]' : 'text-danger'
                    }`}>
                      {log.status === 'completed' ? 'OK' : 'Échec'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {!enabled && (
        <div className="rounded-[14px] border border-border bg-surface px-4 py-3">
          <p className="text-[12px] text-tertiary">
            Activez le pipeline automatique pour configurer la planification et voir l'historique.
          </p>
        </div>
      )}
    </div>
  )
}
