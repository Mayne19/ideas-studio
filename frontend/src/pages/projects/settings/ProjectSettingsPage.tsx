import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { updateProject } from '@/api/projects'
import type { UpdateProjectPayload } from '@/api/projects'
import { useProject } from '@/context/ProjectContext'
import FormCard from '@/components/ui/FormCard'
import Input from '@/components/ui/Input'
import Select from '@/components/ui/Select'
import Button from '@/components/ui/Button'
import LoadingState from '@/components/ui/LoadingState'

const LOCALE_OPTIONS = [
  { value: 'fr-FR', label: 'Français' },
  { value: 'en-US', label: 'Anglais' },
  { value: 'es-ES', label: 'Espagnol' },
  { value: 'de-DE', label: 'Allemand' },
  { value: 'pt-PT', label: 'Portugais' },
  { value: 'it-IT', label: 'Italien' },
]

const TIMEZONE_OPTIONS = [
  { value: 'Europe/Paris', label: 'Europe/Paris' },
  { value: 'Europe/Brussels', label: 'Europe/Brussels' },
  { value: 'Europe/Zurich', label: 'Europe/Zurich' },
  { value: 'America/Montreal', label: 'America/Montreal' },
  { value: 'UTC', label: 'UTC' },
]

const VERTICAL_OPTIONS = [
  { value: '', label: 'Non défini' },
  { value: 'IA & Tech', label: 'IA & Tech' },
  { value: 'Finance & Crypto', label: 'Finance & Crypto' },
  { value: 'Marketing Digital', label: 'Marketing Digital' },
  { value: 'Santé & Bien-être', label: 'Santé & Bien-être' },
  { value: 'Immobilier', label: 'Immobilier' },
  { value: 'Voyage & Tourisme', label: 'Voyage & Tourisme' },
  { value: 'Mode & Lifestyle', label: 'Mode & Lifestyle' },
  { value: 'Éducation & Formation', label: 'Éducation & Formation' },
  { value: 'Juridique & Compliance', label: 'Juridique & Compliance' },
  { value: 'RH & Management', label: 'RH & Management' },
  { value: 'Développement logiciel', label: 'Développement logiciel' },
  { value: 'Autre', label: 'Autre' },
]

type FormState = {
  name: string
  domain: string
  locale: string
  vertical: string
  timezone: string
  word_count_min: string
  word_count_max: string
}

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error'

export default function ProjectSettingsPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const { project, loading, refetch } = useProject()
  const [form, setForm] = useState<FormState>({
    name: '',
    domain: '',
    locale: 'fr-FR',
    vertical: '',
    timezone: 'Europe/Paris',
    word_count_min: '',
    word_count_max: '',
  })
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle')
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    if (!project) return
    const values = {
      name: project.name ?? '',
      domain: project.domain ?? '',
      locale: project.locale ?? 'fr-FR',
      vertical: project.vertical ?? '',
      timezone: project.timezone ?? 'Europe/Paris',
      word_count_min: project.word_count_min != null ? String(project.word_count_min) : '',
      word_count_max: project.word_count_max != null ? String(project.word_count_max) : '',
    }
    Promise.resolve().then(() => setForm(values))
  }, [project])

  function set(field: keyof FormState) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
      setForm((f) => ({ ...f, [field]: e.target.value }))
      if (saveStatus !== 'idle') setSaveStatus('idle')
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    if (!projectId || !form.name.trim()) return
    setErrorMsg('')
    setSaveStatus('saving')
    try {
      const payload: UpdateProjectPayload = {
        name: form.name.trim(),
        domain: form.domain.trim() || undefined,
        locale: form.locale || undefined,
        vertical: form.vertical || undefined,
        timezone: form.timezone.trim() || undefined,
        word_count_min: form.word_count_min.trim() ? parseInt(form.word_count_min) : null,
        word_count_max: form.word_count_max.trim() ? parseInt(form.word_count_max) : null,
      }
      await updateProject(projectId, payload)
      setSaveStatus('saved')
      refetch()
      setTimeout(() => setSaveStatus('idle'), 3000)
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Erreur lors de la sauvegarde')
      setSaveStatus('error')
    }
  }

  if (loading) return <LoadingState />

  return (
    <form onSubmit={handleSave} className="flex flex-col gap-5">
      <FormCard
        title="Informations générales"
        description="Modifiez le nom, le domaine et la langue de votre projet."
        footer={
          <div className="flex items-center gap-3">
            {saveStatus === 'saved' && (
              <span className="text-[14px] text-success">Sauvegardé ✓</span>
            )}
            {saveStatus === 'error' && (
              <span className="text-[14px] text-danger">{errorMsg}</span>
            )}
            <Button type="submit" loading={saveStatus === 'saving'} size="sm">
              Sauvegarder
            </Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Nom du projet"
              value={form.name}
              onChange={set('name')}
              required
              placeholder="Mon blog tech"
            />
            <Input
              label="Domaine"
              value={form.domain}
              onChange={set('domain')}
              placeholder="monblog.com"
            />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <Select
              label="Langue principale"
              options={LOCALE_OPTIONS}
              value={form.locale}
              onChange={set('locale')}
            />
            <Select
              label="Fuseau horaire"
              options={TIMEZONE_OPTIONS}
              value={form.timezone}
              onChange={set('timezone')}
            />
            <Select
              label="Vertical éditorial"
              options={VERTICAL_OPTIONS}
              value={form.vertical}
              onChange={set('vertical')}
            />
          </div>
          {/* Volume éditorial — plage de mots par défaut pour tout le projet */}
          <div>
            <p className="text-[13px] font-medium text-primary mb-1">
              Volume éditorial par défaut
            </p>
            <p className="text-[11px] text-tertiary mb-2">
              Plage de mots appliquée à tous les articles du projet.
              Peut être surchargée catégorie par catégorie.
            </p>
            <div className="flex items-center gap-2 flex-wrap">
              <input
                type="number"
                min="300"
                step="100"
                value={form.word_count_min}
                onChange={set('word_count_min')}
                placeholder="Min (ex. 900)"
                className="h-9 w-28 rounded-[8px] border border-border bg-transparent px-2.5 text-[12px] text-primary"
              />
              <span className="text-[12px] text-tertiary">à</span>
              <input
                type="number"
                min="300"
                step="100"
                value={form.word_count_max}
                onChange={set('word_count_max')}
                placeholder="Max (ex. 1400)"
                className="h-9 w-28 rounded-[8px] border border-border bg-transparent px-2.5 text-[12px] text-primary"
              />
              <span className="text-[12px] text-tertiary">mots</span>
            </div>
            <p className="mt-1.5 text-[11px] text-tertiary">
              Le système génère des articles dans cette plage.
              En dessous du minimum et au-dessus du maximum : jamais.
            </p>
          </div>
        </div>
      </FormCard>
    </form>
  )
}
