import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Lightbulb, Zap, PenLine, Loader2, AlertCircle, CheckCircle, ArrowRight } from 'lucide-react'
import { generateIdea, launchIdeas } from '@/api/ideas'
import { listCategories } from '@/api/categories'
import { useEffect } from 'react'
import type { Category, IdeaGenerateResponse } from '@/types'
import { ApiError } from '@/api/client'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import Select from '@/components/ui/Select'

type Mode = 'idea' | 'full_article' | 'manual'

const MODES: { key: Mode; icon: React.ReactNode; label: string; desc: string }[] = [
  {
    key: 'idea',
    icon: <Lightbulb size={20} />,
    label: 'Générer une idée',
    desc: "L'IA propose un sujet structuré avec keyword, angle et plan.",
  },
  {
    key: 'full_article',
    icon: <Zap size={20} />,
    label: 'Article complet',
    desc: "L'IA génère un brouillon complet prêt à réviser.",
  },
  {
    key: 'manual',
    icon: <PenLine size={20} />,
    label: 'Brouillon manuel',
    desc: 'Créez un brouillon vide et commencez à écrire.',
  },
]

function translateError(err: unknown): string {
  if (err instanceof ApiError) {
    switch (err.status) {
      case 409: return 'Une génération est déjà en cours. Attendez quelques instants.'
      case 403: return 'Vous n\'avez pas la permission de lancer cette action.'
      case 422: return 'Données invalides. Vérifiez les informations saisies.'
      default: return err.message || `Erreur ${err.status}`
    }
  }
  return 'Une erreur inattendue est survenue.'
}

export default function GeneratePage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()

  const [mode, setMode] = useState<Mode>('idea')
  const [keyword, setKeyword] = useState('')
  const [secondaryKeywords, setSecondaryKeywords] = useState('')
  const [category, setCategory] = useState('')
  const [audience, setAudience] = useState('')
  const [angle, setAngle] = useState('')
  const [articleType, setArticleType] = useState('')
  const [targetLength, setTargetLength] = useState('')
  const [withFaq, setWithFaq] = useState(false)
  const [withCallouts, setWithCallouts] = useState(false)
  const [categories, setCategories] = useState<Category[]>([])

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<IdeaGenerateResponse | null>(null)

  useEffect(() => {
    if (!projectId) return
    listCategories(projectId).then(setCategories).catch(() => {})
  }, [projectId])

  function buildContextHint(): string {
    const parts: string[] = []
    if (keyword) parts.push(`Keyword : ${keyword}`)
    if (secondaryKeywords) parts.push(`Keywords secondaires : ${secondaryKeywords}`)
    if (audience) parts.push(`Audience : ${audience}`)
    if (angle) parts.push(`Angle : ${angle}`)
    if (articleType) parts.push(`Type d'article : ${articleType}`)
    if (targetLength) parts.push(`Longueur cible : ${targetLength}`)
    if (withFaq) parts.push('Inclure une FAQ')
    if (withCallouts) parts.push('Inclure des encadrés callout')
    return parts.join(' — ')
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!projectId) return
    setLoading(true)
    setError('')
    setResult(null)

    try {
      if (mode === 'idea') {
        const res = await generateIdea(projectId, {
          context_hint: buildContextHint() || undefined,
        })
        setResult(res)
      } else if (mode === 'full_article') {
        const res = await launchIdeas(projectId, { mode: 'full_article' })
        if (res.article_ids.length > 0) {
          navigate(`/projects/${projectId}/articles/${res.article_ids[0]}/edit`)
        } else {
          setError('Aucun article créé. Réessayez dans quelques instants.')
        }
      } else {
        // manual — we need an articleId, create from the ideas pipeline
        // createManualDraft needs an article_id (from an existing idea)
        // Instead, navigate to articles list to create manually
        navigate(`/projects/${projectId}/articles`)
      }
    } catch (err) {
      setError(translateError(err))
    } finally {
      setLoading(false)
    }
  }

  const categoryOptions = [
    { value: '', label: 'Aucune catégorie' },
    ...categories.map((c) => ({ value: c.id, label: c.name })),
  ]

  return (
    <div className="mx-auto max-w-2xl">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-[20px] font-semibold text-primary tracking-tight">Générer</h1>
        <p className="mt-0.5 text-[13px] text-secondary">
          Lancez une production manuelle : idée, article complet ou brouillon vide.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-6">
        {/* Mode selector */}
        <div className="grid grid-cols-3 gap-3">
          {MODES.map((m) => (
            <button
              key={m.key}
              type="button"
              onClick={() => setMode(m.key)}
              className={`flex flex-col gap-3 rounded-[16px] border p-4 text-left transition-all ${
                mode === m.key
                  ? 'border-accent bg-accent/5 shadow-sm'
                  : 'border-border bg-surface hover:border-accent/40 hover:bg-[#f9f9fb]'
              }`}
            >
              <span className={mode === m.key ? 'text-accent' : 'text-tertiary'}>
                {m.icon}
              </span>
              <div>
                <p className={`text-[13px] font-semibold ${mode === m.key ? 'text-accent' : 'text-primary'}`}>
                  {m.label}
                </p>
                <p className="mt-0.5 text-[11px] text-secondary leading-snug">{m.desc}</p>
              </div>
            </button>
          ))}
        </div>

        {/* Context fields — shown for idea + full_article */}
        {mode !== 'manual' && (
          <div className="rounded-[16px] border border-border bg-surface p-5 flex flex-col gap-4">
            <p className="text-[12px] font-semibold text-secondary uppercase tracking-wide">
              Contexte {mode === 'full_article' ? '(optionnel)' : ''}
            </p>
            <Input
              label="Keyword principal"
              placeholder="optimisation seo pour blogs"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              hint="Mot-clé cible de l'idée ou de l'article"
            />
            <Input
              label="Keywords secondaires"
              placeholder="seo technique, core web vitals, indexation"
              value={secondaryKeywords}
              onChange={(e) => setSecondaryKeywords(e.target.value)}
              hint="Séparés par des virgules"
            />
            {categories.length > 0 && (
              <Select
                label="Catégorie"
                options={categoryOptions}
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              />
            )}
            <Input
              label="Audience cible"
              placeholder="Développeurs web indépendants"
              value={audience}
              onChange={(e) => setAudience(e.target.value)}
            />
            <Input
              label="Angle éditorial"
              placeholder="Guide pratique avec exemples concrets"
              value={angle}
              onChange={(e) => setAngle(e.target.value)}
              hint="Perspective unique à adopter"
            />
            <div className="grid grid-cols-2 gap-3">
              <Select
                label="Type d'article"
                options={[
                  { value: '', label: 'Automatique' },
                  { value: 'guide complet', label: 'Guide complet' },
                  { value: 'listicle', label: 'Listicle' },
                  { value: 'how-to', label: 'Tutoriel How-To' },
                  { value: 'comparatif', label: 'Comparatif' },
                  { value: 'analyse', label: 'Analyse approfondie' },
                  { value: 'actualité', label: 'Actualité / News' },
                ]}
                value={articleType}
                onChange={(e) => setArticleType(e.target.value)}
              />
              <Select
                label="Longueur cible"
                options={[
                  { value: '', label: 'Automatique' },
                  { value: 'court (500-800 mots)', label: 'Court (500-800 mots)' },
                  { value: 'moyen (1000-1500 mots)', label: 'Moyen (1000-1500 mots)' },
                  { value: 'long (2000-3000 mots)', label: 'Long (2000-3000 mots)' },
                  { value: 'très long (4000+ mots)', label: 'Très long (4000+ mots)' },
                ]}
                value={targetLength}
                onChange={(e) => setTargetLength(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={withFaq}
                  onChange={(e) => setWithFaq(e.target.checked)}
                  className="rounded"
                />
                <span className="text-[12px] text-secondary">Inclure une FAQ</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={withCallouts}
                  onChange={(e) => setWithCallouts(e.target.checked)}
                  className="rounded"
                />
                <span className="text-[12px] text-secondary">Inclure des callouts</span>
              </label>
            </div>

            {mode === 'full_article' && (
              <div className="flex items-start gap-2 rounded-[10px] border border-warning/20 bg-warning/5 px-3 py-2.5">
                <AlertCircle size={13} className="mt-0.5 shrink-0 text-[#c07000]" />
                <p className="text-[12px] text-secondary leading-snug">
                  L'article complet utilise les paramètres du projet (audience, ton). Les champs ci-dessus servent de contexte additionnel.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Manual mode info */}
        {mode === 'manual' && (
          <div className="rounded-[16px] border border-border bg-[#f9f9fb] p-5 flex items-start gap-3">
            <PenLine size={16} className="mt-0.5 shrink-0 text-tertiary" />
            <div>
              <p className="text-[13px] font-medium text-primary">Brouillon manuel</p>
              <p className="mt-0.5 text-[12px] text-secondary leading-snug">
                Vous serez redirigé vers la liste d'articles pour créer un brouillon vide et commencer à écrire directement dans l'éditeur.
              </p>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="flex items-start gap-2 rounded-[10px] border border-danger/20 bg-danger/5 px-3 py-2.5 text-[13px] text-danger">
            <AlertCircle size={13} className="mt-0.5 shrink-0" />
            <span className="leading-snug">{error}</span>
          </div>
        )}

        {/* Success result */}
        {result && (
          <div className="rounded-[16px] border border-success/20 bg-success/5 p-4 flex flex-col gap-3">
            <div className="flex items-center gap-2 text-[#1a7a3a]">
              <CheckCircle size={15} />
              <p className="text-[13px] font-semibold">Idée générée avec succès</p>
            </div>
            <div>
              <p className="text-[14px] font-medium text-primary">{result.title}</p>
              {result.keyword && (
                <p className="mt-0.5 text-[12px] text-tertiary">🔑 {result.keyword}</p>
              )}
              {result.angle && (
                <p className="mt-1 text-[12px] text-secondary leading-snug">{result.angle}</p>
              )}
            </div>
            <div className="flex gap-2 pt-1">
              <Button
                size="sm"
                variant="secondary"
                onClick={() => navigate(`/projects/${projectId}/ideas`)}
              >
                Voir les idées
              </Button>
              <Button
                size="sm"
                icon={<ArrowRight size={13} />}
                onClick={() => {
                  if (result.id) navigate(`/projects/${projectId}/articles/${result.id}/edit`)
                  else navigate(`/projects/${projectId}/ideas`)
                }}
              >
                Ouvrir dans l'éditeur
              </Button>
            </div>
          </div>
        )}

        {/* Submit */}
        {!result && (
          <Button
            type="submit"
            loading={loading}
            icon={loading ? <Loader2 size={14} className="animate-spin" /> : mode === 'manual' ? <PenLine size={14} /> : <Zap size={14} />}
            className="w-full justify-center"
          >
            {mode === 'idea' ? 'Générer une idée' : mode === 'full_article' ? 'Générer l\'article' : 'Créer un brouillon'}
          </Button>
        )}

        {result && (
          <button
            type="button"
            onClick={() => { setResult(null); setKeyword(''); setSecondaryKeywords(''); setAngle(''); setAudience(''); setArticleType(''); setTargetLength(''); setWithFaq(false); setWithCallouts(false) }}
            className="text-center text-[12px] text-accent hover:underline"
          >
            Générer une autre idée
          </button>
        )}
      </form>
    </div>
  )
}
