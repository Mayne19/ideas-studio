import { useEffect, useState, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { Plus, Trash2, TestTube, CheckCircle, XCircle, Loader2, Eye, EyeOff, Save, Settings, Star } from '@/components/ui/hugeIcons'
import { api, friendlyApiErrorMessage } from '@/api/client'
import { Card } from '@/components/ui/Card'
import { useProject } from '@/context/ProjectContext'
import { useAuth } from '@/context/AuthContext'

type AIProviderConfig = {
  id: string
  project_id: string | null
  provider: string
  label: string
  api_key_configured: boolean
  base_url: string | null
  model: string | null
  is_default: boolean
  last_test_status: string | null
  last_test_error: string | null
  last_tested_at: string | null
  created_at: string
}

type ProviderCatalogEntry = {
  id: string
  code: string
  label: string
  base_url: string | null
  is_enabled: boolean
}

function getCatalogEntry(catalog: ProviderCatalogEntry[], code: string): ProviderCatalogEntry | undefined {
  return catalog.find((p) => p.code === code)
}

type ProviderFormData = {
  provider: string
  label: string
  api_key: string
  model: string
}

const emptyForm: ProviderFormData = {
  provider: '',
  label: '',
  api_key: '',
  model: '',
}

type CatalogFormData = {
  code: string
  label: string
  base_url: string
}

const emptyCatalogForm: CatalogFormData = { code: '', label: '', base_url: '' }

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

export default function ProjectProvidersPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const { myRole } = useProject()
  const { user } = useAuth()
  const [configs, setConfigs] = useState<AIProviderConfig[]>([])
  const [catalog, setCatalog] = useState<ProviderCatalogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState<ProviderFormData>(emptyForm)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<{ id: string; status: string; message: string } | null>(null)
  const [showKeys, setShowKeys] = useState<Set<string>>(new Set())
  const [deleting, setDeleting] = useState<string | null>(null)
  const [settingDefault, setSettingDefault] = useState<string | null>(null)

  // Gestion du catalogue global (admin plateforme uniquement)
  const [catalogManagerOpen, setCatalogManagerOpen] = useState(false)
  const [catalogForm, setCatalogForm] = useState<CatalogFormData>(emptyCatalogForm)
  const [savingCatalog, setSavingCatalog] = useState(false)
  const [catalogError, setCatalogError] = useState('')

  const loadConfigs = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [data, catalogData] = await Promise.all([
        api.get<AIProviderConfig[]>(projectId ? `/settings/ai-providers?project_id=${projectId}` : '/settings/ai-providers'),
        api.get<ProviderCatalogEntry[]>('/settings/ai-providers/catalog'),
      ])
      setConfigs(data)
      setCatalog(catalogData)
    } catch (err: unknown) {
      const msg = friendlyApiErrorMessage(err, 'Erreur de chargement')
      setError(msg)
      setConfigs([])
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    const timer = setTimeout(() => loadConfigs(), 0)
    return () => clearTimeout(timer)
  }, [loadConfigs])

  const availableCatalog = catalog.filter((p) => p.is_enabled)

  function openCreate(code: string) {
    const def = getCatalogEntry(catalog, code)
    setForm({
      provider: code,
      label: def?.label ?? code,
      api_key: '',
      model: '',
    })
    setEditingId(null)
    setShowForm(true)
    setTestResult(null)
  }

  function openEdit(config: AIProviderConfig) {
    setForm({
      provider: config.provider,
      label: config.label,
      api_key: '',
      model: config.model ?? '',
    })
    setEditingId(config.id)
    setShowForm(true)
    setTestResult(null)
  }

  async function handleSave() {
    setSaving(true)
    try {
      const apiKey = form.api_key.trim()
      const model = form.model.trim()
      if (editingId) {
        // AIProviderUpdate accepte api_key et model côté backend v3 — le label et
        // le provider sont fixés à la création (contrainte unique project_id+provider).
        const payload: Record<string, string> = {}
        if (apiKey) payload.api_key = apiKey
        payload.model = model
        await api.patch(`/settings/ai-providers/${editingId}`, payload)
      } else {
        await api.post('/settings/ai-providers', {
          provider: form.provider,
          label: form.label || form.provider,
          project_id: projectId,
          api_key: apiKey || undefined,
          model: model || undefined,
        })
      }
      setShowForm(false)
      setEditingId(null)
      setTestResult(null)
      await loadConfigs()
    } catch (err: unknown) {
      const msg = friendlyApiErrorMessage(err, 'Erreur lors de la sauvegarde')
      alert(msg)
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: string) {
    setDeleting(id)
    try {
      await api.delete(`/settings/ai-providers/${id}`)
      await loadConfigs()
    } catch (err: unknown) {
      const msg = friendlyApiErrorMessage(err, 'Erreur lors de la suppression')
      alert(msg)
    } finally {
      setDeleting(null)
    }
  }

  async function handleSetDefault(id: string) {
    setSettingDefault(id)
    try {
      await api.patch(`/settings/ai-providers/${id}`, { is_default: true })
      await loadConfigs()
    } catch (err: unknown) {
      alert(friendlyApiErrorMessage(err, 'Erreur lors de la définition du provider par défaut'))
    } finally {
      setSettingDefault(null)
    }
  }

  async function handleTest(id: string) {
    setTesting(id)
    setTestResult(null)
    try {
      const result = await api.post<{ provider: string; status: string; message: string | null; model: string | null }>(`/settings/ai-providers/${id}/test`)
      setTestResult({ id, status: result.status, message: result.message || (result.status === 'connected' ? 'Connexion réussie' : 'Erreur inconnue') })
      await loadConfigs()
    } catch (err: unknown) {
      const msg = friendlyApiErrorMessage(err, 'Erreur de test')
      setTestResult({ id, status: 'error', message: msg })
    } finally {
      setTesting(null)
    }
  }

  function toggleKey(id: string) {
    setShowKeys((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  async function handleAddCatalogEntry(event: React.FormEvent) {
    event.preventDefault()
    const code = catalogForm.code.trim().toLowerCase()
    if (!code || !catalogForm.label.trim()) return
    setSavingCatalog(true)
    setCatalogError('')
    try {
      await api.post('/settings/ai-providers/catalog', {
        code,
        label: catalogForm.label.trim(),
        base_url: catalogForm.base_url.trim() || undefined,
      })
      setCatalogForm(emptyCatalogForm)
      await loadConfigs()
    } catch (err: unknown) {
      setCatalogError(friendlyApiErrorMessage(err, "Erreur lors de l'ajout au catalogue"))
    } finally {
      setSavingCatalog(false)
    }
  }

  async function handleToggleCatalogEntry(entry: ProviderCatalogEntry) {
    try {
      await api.patch(`/settings/ai-providers/catalog/${entry.id}`, { is_enabled: !entry.is_enabled })
      await loadConfigs()
    } catch (err: unknown) {
      alert(friendlyApiErrorMessage(err, 'Erreur lors de la mise à jour'))
    }
  }

  async function handleDeleteCatalogEntry(entry: ProviderCatalogEntry) {
    if (!confirm(`Retirer "${entry.label}" du catalogue ? Impossible si des clés y sont encore connectées.`)) return
    try {
      await api.delete(`/settings/ai-providers/catalog/${entry.id}`)
      await loadConfigs()
    } catch (err: unknown) {
      alert(friendlyApiErrorMessage(err, 'Erreur lors de la suppression'))
    }
  }

  if (myRole !== null && myRole !== 'owner' && myRole !== 'admin') {
    return <AccessDenied />
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 size={20} className="animate-spin text-tertiary" />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h2 className="text-[15px] font-semibold text-primary">Configuration des providers IA</h2>
        {user?.is_staff && (
          <button
            onClick={() => setCatalogManagerOpen((open) => !open)}
            className="flex items-center gap-1.5 rounded-[10px] border border-border px-3 py-1.5 text-[12px] font-medium text-secondary transition-colors hover:bg-surface-soft hover:text-primary"
          >
            <Settings size={13} />
            Catalogue des plateformes
          </button>
        )}
      </div>

      <div className="rounded-[14px] border border-accent/20 bg-accent/5 px-4 py-3">
        <p className="text-[12px] text-secondary leading-snug">
          Un provider ici correspond à une clé API pour une plateforme donnée. Le modèle utilisé par chaque agent
          se choisit dans Paramètres → Agents, pas ici. Le provider marqué « Par défaut » (étoile) est utilisé pour
          « Tester le pipeline » et pour tout agent sans assignation spécifique — les agents assignés explicitement
          dans Paramètres → Agents utilisent toujours leur propre provider, indépendamment de ce choix.
        </p>
      </div>

      {user?.is_staff && catalogManagerOpen && (
        <Card>
          <p className="text-[14px] font-medium text-primary mb-1">Catalogue des plateformes IA</p>
          <p className="text-[12px] text-tertiary mb-3">
            Liste globale, partagée par tous les projets. Réservé aux administrateurs plateforme.
          </p>
          <div className="flex flex-col gap-2 mb-4">
            {catalog.map((entry) => (
              <div key={entry.id} className="flex items-center justify-between gap-3 rounded-[8px] border border-border px-3 py-2">
                <div className="min-w-0">
                  <p className="text-[13px] font-medium text-primary">{entry.label} <span className="text-tertiary font-normal">({entry.code})</span></p>
                  {entry.base_url && <p className="text-[11px] text-tertiary truncate">{entry.base_url}</p>}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => handleToggleCatalogEntry(entry)}
                    className={`rounded-full px-2 py-0.5 text-[10px] font-medium transition-colors ${entry.is_enabled ? 'bg-success/8 text-success' : 'bg-surface-soft text-tertiary'}`}
                  >
                    {entry.is_enabled ? 'Activé' : 'Désactivé'}
                  </button>
                  <button
                    onClick={() => handleDeleteCatalogEntry(entry)}
                    className="flex h-6 w-6 items-center justify-center rounded-[6px] text-tertiary hover:bg-danger/10 hover:text-danger transition-colors"
                    title="Retirer du catalogue"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>
            ))}
          </div>
          <form onSubmit={handleAddCatalogEntry} className="flex flex-col gap-2 border-t border-border pt-3">
            <p className="text-[12px] font-medium text-secondary">Ajouter une plateforme</p>
            {catalogError && <p className="text-[12px] text-danger">{catalogError}</p>}
            <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
              <input
                value={catalogForm.code}
                onChange={(e) => setCatalogForm((f) => ({ ...f, code: e.target.value }))}
                placeholder="code (ex: anthropic)"
                className="rounded-[8px] border border-border bg-surface px-2.5 py-1.5 text-[12px] text-primary outline-none focus:border-accent"
              />
              <input
                value={catalogForm.label}
                onChange={(e) => setCatalogForm((f) => ({ ...f, label: e.target.value }))}
                placeholder="Label (ex: Claude / Anthropic)"
                className="rounded-[8px] border border-border bg-surface px-2.5 py-1.5 text-[12px] text-primary outline-none focus:border-accent"
              />
              <input
                value={catalogForm.base_url}
                onChange={(e) => setCatalogForm((f) => ({ ...f, base_url: e.target.value }))}
                placeholder="Base URL (optionnel)"
                className="rounded-[8px] border border-border bg-surface px-2.5 py-1.5 text-[12px] text-primary outline-none focus:border-accent"
              />
            </div>
            <button
              type="submit"
              disabled={savingCatalog || !catalogForm.code.trim() || !catalogForm.label.trim()}
              className="w-fit flex items-center gap-1.5 rounded-[8px] bg-accent px-3 py-1.5 text-[12px] font-medium text-white hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {savingCatalog ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
              Ajouter au catalogue
            </button>
          </form>
        </Card>
      )}

      {error && (
        <div className="rounded-[12px] border border-danger/20 bg-danger/5 px-4 py-3">
          <div className="flex items-start gap-2 text-[14px] text-danger">
            <XCircle size={15} className="mt-0.5 shrink-0" />
            <div>
              <p className="font-medium">Configuration IA indisponible</p>
              <p className="mt-0.5 text-[12px] text-secondary">
                {error === 'Not Found' ? "L’API Providers n’est pas disponible sur ce déploiement. Déployez le backend à jour pour connecter Gemini." : error}
              </p>
            </div>
          </div>
          <button onClick={loadConfigs} className="mt-3 rounded-[10px] bg-accent px-4 py-2 text-[12px] font-medium text-white transition-opacity hover:opacity-90">
            Réessayer
          </button>
        </div>
      )}

      {configs.length === 0 && !showForm && (
        <Card className="text-center">
          <p className="text-[14px] text-secondary mb-4">Aucun provider configuré. Ajoutez-en un depuis la liste ci-dessous.</p>
          <div className="flex flex-wrap justify-center gap-2">
            {availableCatalog.map((p) => (
              <button
                key={p.code}
                onClick={() => openCreate(p.code)}
                disabled={!!error}
                className="flex items-center gap-1.5 rounded-[10px] border border-border px-3 py-2 text-[12px] font-medium text-secondary transition-colors hover:bg-surface-soft hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Plus size={13} />
                {p.label}
              </button>
            ))}
          </div>
        </Card>
      )}

      {configs.map((config) => {
        return (
          <div key={config.id} className="rounded-[8px] border border-border bg-surface p-4">
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="flex items-center gap-2">
                  <p className="text-[14px] font-medium text-primary">{config.label}</p>
                  {config.is_default && (
                    <span className="flex items-center gap-1 rounded-full bg-accent/10 px-2 py-0.5 text-[10px] font-medium text-accent">
                      <Star size={10} />
                      Par défaut
                    </span>
                  )}
                  {config.last_test_status === 'connected' && (
                    <span className="rounded-full bg-success/8 px-2 py-0.5 text-[10px] font-medium text-success">Connecté</span>
                  )}
                  {config.last_test_status === 'error' && (
                    <span className="rounded-full bg-danger/8 px-2 py-0.5 text-[10px] font-medium text-danger">Erreur</span>
                  )}
                </div>
                <p className="mt-0.5 text-[12px] text-tertiary">
                  {config.provider}{config.base_url ? ` · ${config.base_url}` : ''}
                </p>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => !config.is_default && handleSetDefault(config.id)}
                  disabled={config.is_default || settingDefault === config.id}
                  className={`flex h-7 w-7 items-center justify-center rounded-[8px] transition-colors ${
                    config.is_default
                      ? 'text-warning cursor-default'
                      : 'text-tertiary hover:bg-surface-soft hover:text-primary'
                  }`}
                  title={config.is_default ? 'Provider par défaut du projet' : 'Définir comme provider par défaut du projet'}
                >
                  {settingDefault === config.id
                    ? <Loader2 size={13} className="animate-spin" />
                    : <Star size={13} className={config.is_default ? 'fill-current' : 'fill-none'} />}
                </button>
                <button
                  onClick={() => handleTest(config.id)}
                  disabled={testing === config.id}
                  className="flex h-7 w-7 items-center justify-center rounded-[8px] text-tertiary hover:bg-surface-soft hover:text-primary transition-colors"
                  title="Tester la connexion"
                >
                  {testing === config.id ? <Loader2 size={13} className="animate-spin" /> : <TestTube size={13} />}
                </button>
                <button
                  onClick={() => openEdit(config)}
                  className="flex h-7 w-7 items-center justify-center rounded-[8px] text-tertiary hover:bg-surface-soft hover:text-primary transition-colors"
                  title="Modifier la clé API"
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>
                  </svg>
                </button>
                <button
                  onClick={() => handleDelete(config.id)}
                  disabled={deleting === config.id}
                  className="flex h-7 w-7 items-center justify-center rounded-[8px] text-tertiary hover:bg-danger/10 hover:text-danger transition-colors"
                  title="Supprimer"
                >
                  {deleting === config.id ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
                </button>
              </div>
            </div>

            {config.last_test_error && (
              <p className="text-[12px] text-danger mb-2">{config.last_test_error}</p>
            )}

            {testResult && testResult.id === config.id && (
              <div className={`rounded-[8px] p-2 text-[12px] mb-2 ${testResult.status === 'connected' ? 'bg-success/8 text-success' : 'bg-danger/8 text-danger'}`}>
                {testResult.status === 'connected' ? <CheckCircle size={11} className="inline mr-1" /> : <XCircle size={11} className="inline mr-1" />}
                {testResult.message}
              </div>
            )}

            <div className="flex flex-wrap gap-4 text-[12px] text-tertiary">
              <span>Clé API : {config.api_key_configured ? 'Configurée' : 'Non configurée'}</span>
              <span>Modèle : {config.model || 'Non défini'}</span>
              {config.last_tested_at && <span>Dernier test : {new Date(config.last_tested_at).toLocaleString('fr-FR')}</span>}
            </div>
          </div>
        )
      })}

      {configs.length > 0 && !showForm && (
        <div className="flex flex-wrap gap-2">
          {availableCatalog.map((p) => {
            const alreadyConfigured = configs.some((c) => c.provider === p.code)
            if (alreadyConfigured) return null
            return (
              <button
                key={p.code}
                onClick={() => openCreate(p.code)}
                disabled={!!error}
                className="flex items-center gap-1.5 rounded-[10px] border border-border px-3 py-2 text-[12px] font-medium text-secondary transition-colors hover:bg-surface-soft hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Plus size={13} />
                {p.label}
              </button>
            )
          })}
        </div>
      )}

      {showForm && (
        <Card>
          <p className="text-[14px] font-medium text-primary mb-4">
            {editingId ? `Modifier la clé : ${form.label}` : `Ajouter : ${getCatalogEntry(catalog, form.provider)?.label || form.provider}`}
          </p>
          <div className="flex flex-col gap-3">
            {!editingId && (
              <>
                <div className="flex flex-col gap-1.5">
                  <label className="text-[12px] font-medium text-secondary">Type de provider</label>
                  <select
                    value={form.provider}
                    onChange={(e) => {
                      const def = getCatalogEntry(catalog, e.target.value)
                      setForm({
                        ...form,
                        provider: e.target.value,
                        label: def?.label ?? e.target.value,
                      })
                    }}
                    className="rounded-[10px] border border-border bg-surface px-3 py-2 text-[14px] text-primary outline-none focus:border-accent"
                  >
                    {availableCatalog.map((p) => (
                      <option key={p.code} value={p.code}>{p.label}</option>
                    ))}
                  </select>
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-[12px] font-medium text-secondary">Label</label>
                  <input
                    type="text"
                    value={form.label}
                    onChange={(e) => setForm({ ...form, label: e.target.value })}
                    placeholder="Mon provider Gemini"
                    className="rounded-[10px] border border-border bg-surface px-3 py-2 text-[14px] text-primary outline-none focus:border-accent"
                  />
                </div>
              </>
            )}
            <div className="flex flex-col gap-1.5">
              <label className="text-[12px] font-medium text-secondary">
                Clé API {editingId ? '(laisser vide pour conserver)' : ''}
              </label>
              <div className="relative">
                <input
                  type={showKeys.has('form') ? 'text' : 'password'}
                  value={form.api_key}
                  onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                  placeholder={editingId ? 'Nouvelle clé (optionnelle)' : 'Votre clé API'}
                  className="w-full rounded-[10px] border border-border bg-surface px-3 py-2 pr-8 text-[14px] text-primary outline-none focus:border-accent"
                />
                <button
                  type="button"
                  onClick={() => toggleKey('form')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-tertiary hover:text-primary"
                >
                  {showKeys.has('form') ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>
            {form.provider === 'ollama' && (
              <div className="rounded-[12px] bg-accent/8 px-3 py-2 text-[12px] text-secondary">
                Sans clé API : connexion à une instance Ollama locale (http://127.0.0.1:11434). Avec une clé API :
                connexion automatique à Ollama Cloud (ollama.com).
              </div>
            )}
            <div className="flex flex-col gap-1.5">
              <label className="text-[12px] font-medium text-secondary">Modèle</label>
              <input
                type="text"
                value={form.model}
                onChange={(e) => setForm({ ...form, model: e.target.value })}
                placeholder="ex : gpt-5, gemini-2.5-flash, claude-sonnet-5..."
                className="rounded-[10px] border border-border bg-surface px-3 py-2 text-[14px] text-primary outline-none focus:border-accent"
              />
              <span className="text-[11px] text-tertiary">
                Modèle utilisé à chaque appel de ce provider par les agents qui n'en définissent pas d'autre.
              </span>
            </div>
            <div className="flex items-center gap-2 pt-2">
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-1.5 rounded-[10px] bg-accent px-4 py-2 text-[12px] font-medium text-white hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                {editingId ? 'Mettre à jour' : 'Ajouter'}
              </button>
              <button
                onClick={() => { setShowForm(false); setEditingId(null); setTestResult(null) }}
                className="rounded-[10px] px-4 py-2 text-[12px] font-medium text-secondary hover:bg-surface-soft transition-colors"
              >
                Annuler
              </button>
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}
