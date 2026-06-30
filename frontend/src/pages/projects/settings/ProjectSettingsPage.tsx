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
  { value: 'Média / publication', label: 'Média / publication' },
  { value: 'Agence', label: 'Agence' },
  { value: 'Formation', label: 'Formation' },
  { value: 'Services professionnels', label: 'Services professionnels' },
  { value: '__custom__', label: 'Autre / personnalisé' },
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
  language: string
  vertical: string
  country_target: string
  timezone: string
  description: string
  industry: string
  industry_custom: string
}

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error'

export default function ProjectSettingsPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const { project, loading, refetch } = useProject()
  const [form, setForm] = useState<FormState>({
    name: '',
    domain: '',
    language: 'fr',
    vertical: '',
    country_target: '',
    timezone: 'Europe/Paris',
    description: '',
    industry: '',
    industry_custom: '',
  })
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle')
  const [errorMsg, setErrorMsg] = useState('')

  const isCustomIndustry = form.industry === '__custom__'

  useEffect(() => {
    if (!project) return
    const raw = project.industry ?? ''
    const isCustom = !INDUSTRY_OPTIONS.some((o) => o.value === raw)
    const values = {
      name: project.name ?? '',
      domain: project.domain ?? '',
      language: project.language ?? 'fr',
      vertical: project.vertical ?? '',
      country_target: project.country_target ?? '',
      timezone: project.timezone ?? 'Europe/Paris',
      description: project.description ?? '',
      industry: isCustom ? '__custom__' : raw,
      industry_custom: isCustom ? raw : '',
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
      const industry = isCustomIndustry ? form.industry_custom.trim() : form.industry
      const payload: UpdateProjectPayload = {
        name: form.name.trim(),
        domain: form.domain.trim() || undefined,
        language: form.language || undefined,
        vertical: form.vertical || undefined,
        country_target: form.country_target.trim() || undefined,
        timezone: form.timezone.trim() || undefined,
        description: form.description.trim() || undefined,
        industry: industry || undefined,
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
              <span className="text-[14px] text-[#1a7a3a]">Sauvegardé ✓</span>
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
              options={LANGUAGE_OPTIONS}
              value={form.language}
              onChange={set('language')}
            />
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
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-2">
              <Select
                label="Secteur / niche"
                options={INDUSTRY_OPTIONS}
                value={form.industry}
                onChange={set('industry')}
              />
              {isCustomIndustry && (
                <Input
                  label="Secteur personnalisé"
                  value={form.industry_custom}
                  onChange={set('industry_custom')}
                  placeholder="Ex. Crypto, Immobilier, Santé…"
                />
              )}
            </div>
            <Select
              label="Vertical éditorial"
              options={VERTICAL_OPTIONS}
              value={form.vertical}
              onChange={set('vertical')}
            />
          </div>
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
