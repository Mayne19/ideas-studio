import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { updateProject } from '@/api/projects'
import type { UpdateProjectPayload } from '@/api/projects'
import { useProject } from '@/context/ProjectContext'
import FormCard from '@/components/ui/FormCard'
import Input from '@/components/ui/Input'
import Textarea from '@/components/ui/Textarea'
import Select from '@/components/ui/Select'
import Button from '@/components/ui/Button'
import LoadingState from '@/components/ui/LoadingState'

const LANGUAGE_OPTIONS = [
  { value: 'fr', label: 'Français' },
  { value: 'en', label: 'Anglais' },
  { value: 'es', label: 'Espagnol' },
  { value: 'de', label: 'Allemand' },
  { value: 'pt', label: 'Portugais' },
  { value: 'it', label: 'Italien' },
]

const COUNTRY_OPTIONS = [
  { value: '', label: 'Non défini' },
  { value: 'France', label: 'France' },
  { value: 'Belgique', label: 'Belgique' },
  { value: 'Suisse', label: 'Suisse' },
  { value: 'Canada', label: 'Canada francophone' },
  { value: 'International', label: 'International' },
]

const TIMEZONE_OPTIONS = [
  { value: 'Europe/Paris', label: 'Europe/Paris' },
  { value: 'Europe/Brussels', label: 'Europe/Brussels' },
  { value: 'Europe/Zurich', label: 'Europe/Zurich' },
  { value: 'America/Montreal', label: 'America/Montreal' },
  { value: 'UTC', label: 'UTC' },
]

const INDUSTRY_OPTIONS = [
  { value: '', label: 'Non défini' },
  { value: 'SaaS B2B', label: 'SaaS B2B' },
  { value: 'E-commerce', label: 'E-commerce' },
  { value: 'Media / publication', label: 'Média / publication' },
  { value: 'Agence', label: 'Agence' },
  { value: 'Formation', label: 'Formation' },
  { value: 'Services professionnels', label: 'Services professionnels' },
]

type FormState = {
  name: string
  domain: string
  language: string
  country_target: string
  timezone: string
  public_site_url: string
  description: string
  industry: string
}

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error'

export default function ProjectSettingsPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const { project, loading, refetch } = useProject()
  const [form, setForm] = useState<FormState>({
    name: '',
    domain: '',
    language: 'fr',
    country_target: '',
    timezone: 'Europe/Paris',
    public_site_url: '',
    description: '',
    industry: '',
  })
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle')
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    if (!project) return
    const values = {
      name: project.name ?? '',
      domain: project.domain ?? '',
      language: project.language ?? 'fr',
      country_target: project.country_target ?? '',
      timezone: project.timezone ?? 'Europe/Paris',
      public_site_url: project.public_site_url ?? '',
      description: project.description ?? '',
      industry: project.industry ?? '',
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
        language: form.language || undefined,
        country_target: form.country_target.trim() || undefined,
        timezone: form.timezone.trim() || undefined,
        public_site_url: form.public_site_url.trim() || null,
        description: form.description.trim() || undefined,
        industry: form.industry.trim() || undefined,
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
              <span className="text-[13px] text-[#1a7a3a]">Sauvegardé ✓</span>
            )}
            {saveStatus === 'error' && (
              <span className="text-[13px] text-danger">{errorMsg}</span>
            )}
            <Button type="submit" loading={saveStatus === 'saving'} size="sm">
              Sauvegarder
            </Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
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
          <Select
            label="Langue principale"
            options={LANGUAGE_OPTIONS}
            value={form.language}
            onChange={set('language')}
          />
          <div className="grid gap-4 md:grid-cols-2">
            <Select
              label="Pays cible"
              options={COUNTRY_OPTIONS}
              value={form.country_target}
              onChange={set('country_target')}
            />
            <Select
              label="Fuseau horaire"
              options={TIMEZONE_OPTIONS}
              value={form.timezone}
              onChange={set('timezone')}
            />
          </div>
          <Input
            label="URL publique du site"
            value={form.public_site_url}
            onChange={set('public_site_url')}
            placeholder="https://www.exemple.fr"
            hint={`Connexion site : ${project?.status === 'connected' ? 'connecté' : 'non connecté'}`}
          />
          <Select
            label="Secteur / niche"
            options={INDUSTRY_OPTIONS}
            value={form.industry}
            onChange={set('industry')}
          />
          <Textarea
            label="Description courte du projet"
            value={form.description}
            onChange={set('description')}
            placeholder="Décrivez ce que publie le site, pour qui, et pourquoi."
            rows={3}
          />
        </div>
      </FormCard>
    </form>
  )
}
