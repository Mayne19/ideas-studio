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

const TONE_OPTIONS = [
  { value: '', label: 'Non défini' },
  { value: 'professionnel', label: 'Professionnel' },
  { value: 'décontracté', label: 'Décontracté' },
  { value: 'éducatif', label: 'Éducatif' },
  { value: 'expert', label: 'Expert' },
  { value: 'conversationnel', label: 'Conversationnel' },
]

type FormState = {
  name: string
  domain: string
  language: string
  country_target: string
  audience: string
  tone: string
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
    audience: '',
    tone: '',
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
      audience: project.audience ?? '',
      tone: project.tone ?? '',
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
        audience: form.audience.trim() || undefined,
        tone: form.tone || undefined,
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
          <Input
            label="Pays cible"
            value={form.country_target}
            onChange={set('country_target')}
            placeholder="France"
            hint="Pays principal visé pour le SEO"
          />
        </div>
      </FormCard>

      <FormCard
        title="Identité éditoriale"
        description="Décrivez votre audience et le ton de votre contenu pour guider l'IA."
      >
        <div className="flex flex-col gap-4">
          <Textarea
            label="Audience cible"
            value={form.audience}
            onChange={set('audience')}
            placeholder="Développeurs web, indépendants, petites agences..."
            rows={3}
          />
          <Select
            label="Ton éditorial"
            options={TONE_OPTIONS}
            value={form.tone}
            onChange={set('tone')}
          />
        </div>
      </FormCard>
    </form>
  )
}
