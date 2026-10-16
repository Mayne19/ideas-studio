import { useCallback, useEffect, useState } from 'react'
import { Loader2, Save, Sparkles, XCircle } from '@/components/ui/hugeIcons'
import { friendlyApiErrorMessage } from '@/api/client'
import {
  getIllustrationSettings,
  previewIllustration,
  saveIllustrationSettings,
  type IllustrationConfig,
  type IllustrationMode,
  type IllustrationPreview,
  type IllustrationSettings,
} from '@/api/illustrations'

const MODE_HINTS: Record<IllustrationMode, string> = {
  ai: "Illustrations dessinées pour chaque article à partir du texte des sections, dans le style de votre marque. Utilise la clé OpenRouter des Providers IA.",
  unsplash: 'Photos libres de droits Unsplash (clé ci-dessous) et visuels officiels des marques citées.',
  none: "Aucune image n'est ajoutée automatiquement aux articles.",
}

const SOURCE_LABELS: Record<string, string> = {
  project: 'réglage du projet',
  global: 'réglage global de la plateforme',
  default: 'valeurs par défaut',
}

const inputClass =
  'rounded-[10px] border border-border bg-surface px-3 py-2 text-[14px] text-primary outline-none focus:border-accent'

function formatUsd(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  return `${value.toLocaleString('fr-FR', { maximumFractionDigits: 4 })} $`
}

type Props = { projectId?: string }

export default function IllustrationSettingsCard({ projectId }: Props) {
  const [settings, setSettings] = useState<IllustrationSettings | null>(null)
  const [mode, setMode] = useState<IllustrationMode>('unsplash')
  const [config, setConfig] = useState<IllustrationConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [previewing, setPreviewing] = useState(false)
  const [preview, setPreview] = useState<IllustrationPreview | null>(null)
  const [subject, setSubject] = useState('')
  const [error, setError] = useState<string | null>(null)

  const apply = useCallback((data: IllustrationSettings) => {
    setSettings(data)
    setMode(data.mode)
    setConfig(data.config)
  }, [])

  useEffect(() => {
    let cancelled = false
    getIllustrationSettings(projectId)
      .then((data) => { if (!cancelled) apply(data) })
      .catch((err: unknown) => { if (!cancelled) setError(friendlyApiErrorMessage(err, 'Erreur de chargement')) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [projectId, apply])

  function update<K extends keyof IllustrationConfig>(key: K, value: IllustrationConfig[K]) {
    setConfig((c) => (c ? { ...c, [key]: value } : c))
    setSaved(false)
  }

  async function handleSave() {
    if (!config) return
    setSaving(true)
    setError(null)
    try {
      apply(await saveIllustrationSettings(mode, config, projectId))
      setSaved(true)
    } catch (err: unknown) {
      setError(friendlyApiErrorMessage(err, 'Erreur lors de la sauvegarde'))
    } finally {
      setSaving(false)
    }
  }

  async function handlePreview() {
    if (!config) return
    setPreviewing(true)
    setError(null)
    try {
      setPreview(await previewIllustration(config, projectId, subject.trim() || undefined))
    } catch (err: unknown) {
      setError(friendlyApiErrorMessage(err, "Erreur lors de la génération de l'aperçu"))
    } finally {
      setPreviewing(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center rounded-[8px] border border-border bg-surface p-6">
        <Loader2 size={18} className="animate-spin text-tertiary" />
      </div>
    )
  }

  if (!settings || !config) {
    return (
      <div className="rounded-[8px] border border-danger/20 bg-danger/5 p-4 text-[12px] text-danger">
        <XCircle size={12} className="mr-1 inline" />
        {error ?? "Réglages des images d'illustration indisponibles."}
      </div>
    )
  }

  const selectedModel = settings.models.find((m) => m.code === config.model)
  const imagesPerArticle = Math.max(0, config.max_images)

  return (
    <div className="rounded-[8px] border border-border bg-surface p-4">
      <div className="mb-3">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-[14px] font-medium text-primary">Images d'illustration</p>
          {!settings.configured && settings.effective_source !== 'default' && (
            <span className="rounded-full bg-accent/10 px-2 py-0.5 text-[10px] font-medium text-accent">Config globale</span>
          )}
        </div>
        <p className="mt-0.5 text-[12px] text-tertiary">
          Comment les articles générés sont illustrés. Actuellement : {SOURCE_LABELS[settings.effective_source]}.
        </p>
      </div>

      <div className="flex flex-col gap-4">
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3" role="radiogroup" aria-label="Mode des images">
          {settings.modes.map((m) => {
            const active = mode === m.code
            return (
              <button
                key={m.code}
                type="button"
                role="radio"
                aria-checked={active}
                onClick={() => { setMode(m.code as IllustrationMode); setSaved(false) }}
                className={`rounded-[10px] border px-3 py-2 text-left text-[13px] transition-colors ${
                  active ? 'border-accent bg-accent/5 text-primary' : 'border-border text-secondary hover:bg-surface-soft'
                }`}
              >
                <span className="font-medium">{m.label}</span>
              </button>
            )
          })}
        </div>
        <p className="text-[12px] text-tertiary">{MODE_HINTS[mode]}</p>

        {mode === 'ai' && (
          <>
            {!settings.openrouter_configured && (
              <div className="rounded-[8px] bg-warning/10 p-2 text-[12px] text-warning">
                Aucune clé OpenRouter trouvée : ajoutez-la dans Paramètres → Providers IA pour générer des illustrations.
              </div>
            )}

            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <div className="flex flex-col gap-1.5">
                <label className="text-[12px] font-medium text-secondary">Modèle d'image</label>
                <select value={config.model} onChange={(e) => update('model', e.target.value)} className={inputClass}>
                  {settings.models.map((m) => (
                    <option key={m.code} value={m.code}>
                      {m.label}{m.approx_cost_usd !== null ? ` · ~${formatUsd(m.approx_cost_usd)}/image` : ''}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[12px] font-medium text-secondary">Style visuel</label>
                <select value={config.style_preset} onChange={(e) => update('style_preset', e.target.value)} className={inputClass}>
                  {settings.style_presets.map((s) => (
                    <option key={s.code} value={s.code}>{s.label}</option>
                  ))}
                </select>
              </div>

              {config.style_preset === 'custom' && (
                <div className="flex flex-col gap-1.5 md:col-span-2">
                  <label className="text-[12px] font-medium text-secondary">Description du style (en anglais de préférence)</label>
                  <textarea
                    value={config.custom_style}
                    onChange={(e) => update('custom_style', e.target.value)}
                    rows={2}
                    maxLength={500}
                    placeholder="ex : risograph print, two-tone, bold geometric shapes, paper texture"
                    className={inputClass}
                  />
                </div>
              )}

              <div className="flex flex-col gap-1.5">
                <label className="text-[12px] font-medium text-secondary">Couleur principale</label>
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    value={config.primary_color}
                    onChange={(e) => update('primary_color', e.target.value.toUpperCase())}
                    className="h-9 w-12 cursor-pointer rounded-[8px] border border-border bg-surface"
                    aria-label="Couleur principale"
                  />
                  <input
                    type="text"
                    value={config.primary_color}
                    onChange={(e) => update('primary_color', e.target.value)}
                    className={`${inputClass} w-28 font-mono`}
                  />
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[12px] font-medium text-secondary">Couleur secondaire</label>
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    value={config.secondary_color}
                    onChange={(e) => update('secondary_color', e.target.value.toUpperCase())}
                    className="h-9 w-12 cursor-pointer rounded-[8px] border border-border bg-surface"
                    aria-label="Couleur secondaire"
                  />
                  <input
                    type="text"
                    value={config.secondary_color}
                    onChange={(e) => update('secondary_color', e.target.value)}
                    className={`${inputClass} w-28 font-mono`}
                  />
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[12px] font-medium text-secondary">Images max. par article (couverture incluse)</label>
                <input
                  type="number"
                  min={0}
                  max={settings.max_images_limit}
                  value={config.max_images}
                  onChange={(e) => update('max_images', Number(e.target.value))}
                  className={`${inputClass} w-28`}
                />
              </div>

              <div className="flex flex-col justify-end gap-1 text-[12px] text-tertiary">
                <span>
                  Coût estimé : jusqu'à {formatUsd((selectedModel?.approx_cost_usd ?? 0) * imagesPerArticle)} par article
                  {' '}(+ un court appel IA pour écrire les prompts).
                </span>
                <span>Seules les sections où un visuel aide vraiment sont illustrées.</span>
              </div>
            </div>

            <div className="flex flex-col gap-2 rounded-[10px] border border-border p-3">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
                <div className="flex flex-1 flex-col gap-1.5">
                  <label className="text-[12px] font-medium text-secondary">Sujet de l'aperçu (optionnel)</label>
                  <input
                    type="text"
                    value={subject}
                    maxLength={300}
                    onChange={(e) => setSubject(e.target.value)}
                    placeholder="ex : a small team planning a content calendar"
                    className={inputClass}
                  />
                </div>
                <button
                  type="button"
                  onClick={handlePreview}
                  disabled={previewing || !settings.openrouter_configured}
                  className="flex items-center justify-center gap-1.5 rounded-[10px] border border-accent px-4 py-2 text-[12px] font-medium text-accent transition-colors hover:bg-accent/5 disabled:opacity-50"
                >
                  {previewing ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                  {previewing ? 'Génération…' : 'Générer un aperçu'}
                </button>
              </div>
              {preview && (
                <figure className="flex flex-col gap-1.5">
                  <img
                    src={preview.image_data_url}
                    alt="Aperçu d'illustration générée"
                    className="w-full rounded-[8px] border border-border"
                  />
                  <figcaption className="text-[11px] text-tertiary">
                    {preview.model} · coût {formatUsd(preview.cost_usd)} · réglages non enregistrés tant que vous ne cliquez pas sur Enregistrer.
                  </figcaption>
                </figure>
              )}
            </div>
          </>
        )}

        {error && <p className="text-[12px] text-danger">{error}</p>}

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1.5 rounded-[10px] bg-accent px-4 py-2 text-[12px] font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
            Enregistrer
          </button>
          {saved && <span className="text-[12px] text-success">Réglages enregistrés</span>}
        </div>
      </div>
    </div>
  )
}
