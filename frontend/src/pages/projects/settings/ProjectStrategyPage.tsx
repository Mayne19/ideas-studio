import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Save, Sparkles } from 'lucide-react'
import { getProject, updateProject } from '@/api/projects'
import type { Project } from '@/types'
import Input from '@/components/ui/Input'
import Textarea from '@/components/ui/Textarea'
import Button from '@/components/ui/Button'
import LoadingState from '@/components/ui/LoadingState'
import EditorialSetupAssistant from '@/components/editorial/EditorialSetupAssistant'

const textFields = [
  ['audience', 'Audience cible', 'Décrivez les lecteurs prioritaires, leurs objectifs et leurs freins.'],
  ['editorial_goal', 'Objectif éditorial', 'Acquisition SEO, éducation marché, conversion, autorité, support produit...'],
  ['value_proposition', 'Proposition de valeur', 'Pourquoi ce contenu est différent et utile.'],
  ['allowed_topics', 'Sujets autorisés', 'Thèmes, angles et familles de contenus que l’IA peut traiter.'],
  ['forbidden_topics', 'Sujets interdits', 'Zones à éviter, promesses interdites, sujets hors périmètre.'],
  ['words_to_avoid', 'Mots à éviter', 'Expressions, jargon ou tournures à bannir.'],
  ['preferred_formats', 'Formats préférés', 'Guides, comparatifs, listes, tutoriels, analyses, FAQ...'],
  ['seo_rules', 'Règles SEO spécifiques', 'Structure Hn, intentions, metas, mots-clés, contraintes de longueur.'],
  ['geo_rules', 'Règles GEO spécifiques', 'Consignes pour les réponses IA, citations, passages synthétiques.'],
  ['source_guidelines', 'Consignes de sources', 'Types de sources acceptées, fraîcheur attendue, citation.'],
  ['internal_linking_guidelines', 'Maillage interne', 'Règles de liens vers contenus existants, ancres, priorités.'],
  ['external_linking_guidelines', 'Maillage externe', 'Sources externes autorisées, nofollow, domaines à éviter.'],
  ['style_examples', 'Exemples de style', 'Collez ici un extrait représentatif du ton attendu.'],
] as const

type StrategyForm = {
  audience: string
  tone: string
  reader_level: string
  writing_style: string
  editorial_goal: string
  value_proposition: string
  allowed_topics: string
  forbidden_topics: string
  words_to_avoid: string
  average_target_length: string
  preferred_formats: string
  technical_level: string
  seo_rules: string
  geo_rules: string
  source_guidelines: string
  internal_linking_guidelines: string
  external_linking_guidelines: string
  style_examples: string
}

export default function ProjectStrategyPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const [assistantOpen, setAssistantOpen] = useState(false)

  const [form, setForm] = useState<StrategyForm>({
    audience: '',
    tone: '',
    reader_level: '',
    writing_style: '',
    editorial_goal: '',
    value_proposition: '',
    allowed_topics: '',
    forbidden_topics: '',
    words_to_avoid: '',
    average_target_length: '',
    preferred_formats: '',
    technical_level: '',
    seo_rules: '',
    geo_rules: '',
    source_guidelines: '',
    internal_linking_guidelines: '',
    external_linking_guidelines: '',
    style_examples: '',
  })

  useEffect(() => {
    if (!projectId) return
    getProject(projectId)
      .then((p) => {
        setProject(p)
        setForm({
          audience: p.audience ?? '',
          tone: p.tone ?? '',
          reader_level: p.reader_level ?? '',
          writing_style: p.writing_style ?? '',
          editorial_goal: p.editorial_goal ?? '',
          value_proposition: p.value_proposition ?? '',
          allowed_topics: p.allowed_topics ?? '',
          forbidden_topics: p.forbidden_topics ?? '',
          words_to_avoid: p.words_to_avoid ?? '',
          average_target_length: p.average_target_length ?? '',
          preferred_formats: p.preferred_formats ?? '',
          technical_level: p.technical_level ?? '',
          seo_rules: p.seo_rules ?? '',
          geo_rules: p.geo_rules ?? '',
          source_guidelines: p.source_guidelines ?? '',
          internal_linking_guidelines: p.internal_linking_guidelines ?? '',
          external_linking_guidelines: p.external_linking_guidelines ?? '',
          style_examples: p.style_examples ?? '',
        })
      })
      .catch(() => setError('Impossible de charger le projet.'))
      .finally(() => setLoading(false))
  }, [projectId])

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    if (!projectId || !project) return
    setSaving(true)
    setSaved(false)
    setError('')
    try {
      await updateProject(projectId, Object.fromEntries(
        Object.entries(form).map(([key, value]) => [key, value.trim() || undefined]),
      ))
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors de la sauvegarde.')
    } finally {
      setSaving(false)
    }
  }

  function handleAssistantApplied() {
    if (!projectId) return
    getProject(projectId).then((p) => {
      setForm((current) => ({
        ...current,
        audience: p.audience ?? '',
        tone: p.tone ?? '',
      }))
    }).catch(() => {})
  }

  if (loading) return <LoadingState />

  return (
    <form onSubmit={handleSave} className="flex flex-col gap-6">
      {error && (
        <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[13px] text-danger">{error}</div>
      )}

      {/* Assistant button */}
      <div className="flex justify-end">
        <Button
          type="button"
          size="sm"
          variant="secondary"
          icon={<Sparkles size={13} />}
          onClick={() => setAssistantOpen(true)}
        >
          Assistant de configuration
        </Button>
      </div>

      {assistantOpen && projectId && (
        <EditorialSetupAssistant
          projectId={projectId}
          open={assistantOpen}
          onClose={() => setAssistantOpen(false)}
          onApplied={handleAssistantApplied}
        />
      )}

      {/* Editorial positioning */}
      <div className="rounded-[14px] border border-border bg-surface p-5 flex flex-col gap-4">
        <p className="text-[12px] font-semibold text-secondary uppercase tracking-wide">Positionnement éditorial</p>
        <Textarea
          label="Audience cible"
          value={form.audience}
          onChange={(e) => setForm((f) => ({ ...f, audience: e.target.value }))}
          placeholder="Ex : Développeurs web indépendants, 25-40 ans, intéressés par la performance et le SEO technique."
          rows={3}
          hint="Décrit le lecteur idéal de votre blog."
        />
        <Input
          label="Ton éditorial"
          value={form.tone}
          onChange={(e) => setForm((f) => ({ ...f, tone: e.target.value }))}
          placeholder="Ex : Expert mais accessible, pédagogique, sans jargon excessif."
          hint="Style et voix qui caractérisent vos articles."
        />
        <div className="grid gap-4 md:grid-cols-3">
          <Input
            label="Niveau du lecteur"
            value={form.reader_level}
            onChange={(e) => setForm((f) => ({ ...f, reader_level: e.target.value }))}
            placeholder="Débutant, intermédiaire, expert"
          />
          <Input
            label="Style d’écriture"
            value={form.writing_style}
            onChange={(e) => setForm((f) => ({ ...f, writing_style: e.target.value }))}
            placeholder="Pédagogique, direct, analytique..."
          />
          <Input
            label="Longueur moyenne cible"
            value={form.average_target_length}
            onChange={(e) => setForm((f) => ({ ...f, average_target_length: e.target.value }))}
            placeholder="1200-1800 mots"
          />
        </div>
        <Input
          label="Niveau de technicité"
          value={form.technical_level}
          onChange={(e) => setForm((f) => ({ ...f, technical_level: e.target.value }))}
          placeholder="Accessible avec exemples techniques modérés"
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        {textFields.filter(([key]) => key !== 'audience').map(([key, label, placeholder]) => (
          <Textarea
            key={key}
            label={label}
            value={form[key]}
            onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
            placeholder={placeholder}
            rows={key === 'style_examples' ? 5 : 3}
          />
        ))}
      </div>

      <div className="flex items-center gap-3">
        <Button type="submit" size="sm" loading={saving} icon={<Save size={13} />}>
          Enregistrer
        </Button>
        {saved && <span className="text-[12px] text-[#1a7a3a]">Sauvegardé ✓</span>}
      </div>
    </form>
  )
}
