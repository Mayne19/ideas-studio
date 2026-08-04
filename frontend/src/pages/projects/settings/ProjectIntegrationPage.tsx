import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { useParams } from 'react-router-dom'
import { Code2, Eye, EyeOff, Globe, Key, Power, RefreshCw, Wifi, WifiOff } from '@/components/ui/hugeIcons'
import { getConnectInfo, disconnectProject, revalidateProject, rotateRevalidateSecret, updateProject } from '@/api/projects'
import type { ConnectInfo } from '@/types'
import { ProjectStatus } from '@/lib/status'
import Button from '@/components/ui/Button'
import FormCard from '@/components/ui/FormCard'
import CopyButton from '@/components/ui/CopyButton'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'
import ConfirmModal from '@/components/ui/ConfirmModal'
import { formatDateTime } from '@/utils/format'

const API_KEY_MASK = '********'

function looksLikeEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim())
}

function deriveRevalidateUrl(publicSiteUrl: string) {
  const raw = publicSiteUrl.trim()
  if (!raw) return ''
  try {
    const url = new URL(raw.startsWith('http') ? raw : `https://${raw}`)
    return `${url.origin}/api/ideas-studio/revalidate`
  } catch {
    return ''
  }
}

function cleanRevalidateForm(data: ConnectInfo) {
  const publicSiteUrl = data.public_site_url ?? ''
  const endpoint = data.revalidate_url ?? ''
  if (!publicSiteUrl.trim()) {
    return {
      public_site_url: '',
      revalidate_url: '',
    }
  }
  const derived = deriveRevalidateUrl(publicSiteUrl)
  const safeEndpoint = looksLikeEmail(endpoint) ? '' : endpoint
  return {
    public_site_url: publicSiteUrl,
    revalidate_url: safeEndpoint || derived,
  }
}

function InfoRow({
  icon,
  label,
  value,
  copyValue,
  canCopy = false,
  action,
  mono = true,
}: {
  icon?: ReactNode
  label: string
  value: string
  copyValue?: string
  canCopy?: boolean
  action?: ReactNode
  mono?: boolean
}) {
  return (
    <div className="flex flex-col gap-1.5 px-4 py-2">
      <div className="min-w-0">
        <div className="flex items-center gap-1.5 text-[12px] font-medium uppercase tracking-wider text-tertiary">
          {icon}
          {label}
        </div>
      </div>
      <div className="flex min-h-9 min-w-0 items-center justify-between gap-3 rounded-[10px] border border-accent/10 bg-accent/6 px-3 py-1.5">
        <p className={`min-w-0 truncate text-[12px] text-tertiary ${mono ? 'font-mono' : ''}`}>{value}</p>
        {(action || canCopy) && (
          <div className="flex shrink-0 items-center gap-2">
            {action}
            {canCopy && <CopyButton value={copyValue ?? value} disabled={!(copyValue ?? value)} className="h-7 shrink-0 px-2" />}
          </div>
        )}
      </div>
    </div>
  )
}

export default function ProjectIntegrationPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [info, setInfo] = useState<ConnectInfo | null>(null)
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [refreshState, setRefreshState] = useState<'idle' | 'success' | 'error'>('idle')
  const [showInstructions, setShowInstructions] = useState(false)
  const [disconnectOpen, setDisconnectOpen] = useState(false)
  const [disconnecting, setDisconnecting] = useState(false)
  const [revalidateForm, setRevalidateForm] = useState({ public_site_url: '', revalidate_url: '' })
  const [savingRevalidate, setSavingRevalidate] = useState(false)
  const [manualRevalidating, setManualRevalidating] = useState(false)
  const [revalidateMessage, setRevalidateMessage] = useState('')
  const [revalidateEndpointEdited, setRevalidateEndpointEdited] = useState(false)
  const [showSecret, setShowSecret] = useState(false)
  const [rotatingSecret, setRotatingSecret] = useState(false)
  const [ga4Form, setGa4Form] = useState({ property_id: '', service_account_json: '' })
  const [savingGa4, setSavingGa4] = useState(false)
  const [ga4Message, setGa4Message] = useState('')

  async function handleDisconnect() {
    if (!projectId) return
    setDisconnecting(true)
    try {
      await disconnectProject(projectId)
      setDisconnectOpen(false)
      const data = await getConnectInfo(projectId)
      setInfo(data)
      setStatus('success')
    } catch {
      setStatus('error')
    }
    finally { setDisconnecting(false) }
  }

  function loadInfo({ quiet = false }: { quiet?: boolean } = {}) {
    if (!projectId) return
    if (quiet) setIsRefreshing(true)
    else setStatus('loading')
    getConnectInfo(projectId)
      .then((data) => {
        setInfo(data)
        setRevalidateForm(cleanRevalidateForm(data))
        setRevalidateEndpointEdited(false)
        setGa4Form({ property_id: data.ga4_property_id ?? '', service_account_json: '' })
        setStatus('success')
        if (quiet) {
          setRefreshState('success')
          window.setTimeout(() => setRefreshState('idle'), 2200)
        }
      })
      .catch(() => {
        if (quiet) {
          setRefreshState('error')
          window.setTimeout(() => setRefreshState('idle'), 2600)
        } else {
          setStatus('error')
        }
      })
      .finally(() => setIsRefreshing(false))
  }

  useEffect(() => {
    if (!projectId) return
    getConnectInfo(projectId)
      .then((data) => {
        setInfo(data)
        setRevalidateForm(cleanRevalidateForm(data))
        setRevalidateEndpointEdited(false)
        setGa4Form({ property_id: data.ga4_property_id ?? '', service_account_json: '' })
        setStatus('success')
      })
      .catch(() => setStatus('error'))
  }, [projectId])

  if (status === 'loading') return <LoadingState />
  if (status === 'error') return <ErrorState onRetry={loadInfo} />

  const isConnected = info?.status === ProjectStatus.CONNECTED
  const hasInstructionsVisible = !isConnected || showInstructions

  async function handleSaveRevalidation(event: React.FormEvent) {
    event.preventDefault()
    if (!projectId) return
    setSavingRevalidate(true)
    setRevalidateMessage('')
    const safeEndpoint = looksLikeEmail(revalidateForm.revalidate_url)
      ? deriveRevalidateUrl(revalidateForm.public_site_url)
      : revalidateForm.revalidate_url
    try {
      await updateProject(projectId, {
        site_url: revalidateForm.public_site_url || undefined,
        revalidate_url: safeEndpoint || undefined,
      })
      const data = await getConnectInfo(projectId)
      setInfo(data)
      setRevalidateForm(cleanRevalidateForm(data))
      setRevalidateEndpointEdited(false)
      setRevalidateMessage('Configuration sauvegardée.')
    } catch (err) {
      setRevalidateMessage(err instanceof Error ? err.message : 'Sauvegarde impossible.')
    } finally {
      setSavingRevalidate(false)
    }
  }

  async function handleSaveGa4(event: React.FormEvent) {
    event.preventDefault()
    if (!projectId) return
    setSavingGa4(true)
    setGa4Message('')
    try {
      await updateProject(projectId, {
        ga4_property_id: ga4Form.property_id.trim() || undefined,
        ga4_service_account_json: ga4Form.service_account_json.trim() || undefined,
      })
      const data = await getConnectInfo(projectId)
      setInfo(data)
      setGa4Form({ property_id: data.ga4_property_id ?? '', service_account_json: '' })
      setGa4Message('Configuration Google Analytics sauvegardée.')
    } catch (err) {
      setGa4Message(err instanceof Error ? err.message : 'Sauvegarde impossible.')
    } finally {
      setSavingGa4(false)
    }
  }

  async function handleRotateSecret() {
    if (!projectId) return
    if (!confirm("Régénérer le secret de revalidation ? L'ancienne valeur cessera de fonctionner immédiatement : pensez à la mettre à jour côté Vercel/Next.js après coup.")) return
    setRotatingSecret(true)
    setRevalidateMessage('')
    try {
      await rotateRevalidateSecret(projectId)
      const data = await getConnectInfo(projectId)
      setInfo(data)
      setShowSecret(true)
      setRevalidateMessage('Nouveau secret généré. Copiez-le et mettez à jour la variable côté Vercel/Next.js.')
    } catch (err) {
      setRevalidateMessage(err instanceof Error ? err.message : 'Régénération impossible.')
    } finally {
      setRotatingSecret(false)
    }
  }

  async function handleManualRevalidate() {
    if (!projectId) return
    setManualRevalidating(true)
    setRevalidateMessage('')
    try {
      const result = await revalidateProject(projectId)
      const data = await getConnectInfo(projectId)
      setInfo(data)
      setRevalidateMessage(result.revalidated ? 'Revalidation envoyée.' : result.message ?? 'Revalidation non configurée.')
    } catch (err) {
      setRevalidateMessage(err instanceof Error ? err.message : 'Revalidation impossible.')
    } finally {
      setManualRevalidating(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      {/* Connection status */}
      <FormCard title="Statut de connexion">
        <div className="flex flex-col gap-3">
          <div
            className={`flex flex-wrap items-center justify-between gap-3 rounded-[14px] px-4 py-3 ${
              isConnected ? 'bg-success/8' : 'bg-surface-soft'
            }`}
          >
            <div className="flex min-w-0 items-center gap-3">
              <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-[12px] ${isConnected ? 'bg-success/8 text-success' : 'bg-surface-soft text-tertiary'}`}>
                {isConnected ? <Wifi size={18} /> : <WifiOff size={18} />}
              </span>
              <div className="min-w-0">
                <p className={`text-[15px] font-semibold ${isConnected ? 'text-success' : 'text-primary'}`}>
                  {isConnected ? 'Site connecté' : 'En attente de connexion'}
                </p>
                <p className="text-[12px] text-secondary">
                  {isConnected
                    ? 'Le snippet est actif et les données sont collectées.'
                    : "Installez le snippet ci-dessous pour connecter votre site."}
                </p>
                {!isConnected && (
                  <p className="mt-2 text-[12px] text-accent">
                    Après avoir installé le snippet, ouvrez votre site dans un nouvel onglet puis cliquez sur Rafraîchir le statut.
                  </p>
                )}
              </div>
            </div>
            <div className="flex flex-wrap items-center justify-end gap-2">
              {refreshState !== 'idle' && (
                <span className={`text-[12px] ${refreshState === 'success' ? 'text-success' : 'text-danger'}`}>
                  {refreshState === 'success' ? 'Statut actualisé' : 'Actualisation impossible'}
                </span>
              )}
              <Button
                size="sm"
                variant="ghost"
                onClick={() => loadInfo({ quiet: true })}
                disabled={isRefreshing}
              >
                <RefreshCw size={12} className={isRefreshing ? 'animate-spin' : ''} />
                Rafraîchir le statut
              </Button>
              {isConnected && (
                <Button
                  size="sm"
                  variant="danger"
                  onClick={() => setDisconnectOpen(true)}
                >
                  <Power size={12} />
                  Déconnecter
                </Button>
              )}
            </div>
          </div>
          {isConnected && (
            <div className="grid gap-2 sm:grid-cols-3">
              <InfoRow icon={<Globe size={11} />} label="Domaine" value={info?.domain ?? 'Domaine non renseigné'} mono={false} />
              <InfoRow icon={<Wifi size={11} />} label="Connecté depuis" value={info?.connected_at ? formatDateTime(info.connected_at) : 'Date non disponible'} mono={false} />
              <InfoRow icon={<RefreshCw size={11} />} label="Dernière activité" value={info?.last_seen_at ? formatDateTime(info.last_seen_at) : 'Aucune activité récente'} mono={false} />
            </div>
          )}
        </div>
      </FormCard>

      {/* Keys & identifiers */}
      <FormCard
        title="Identifiants"
        description="Utilisez ces clés pour connecter votre blog à l'API publique."
      >
        <div className="flex flex-col gap-1.5">
          <InfoRow
            icon={<Key size={11} />}
            label="Project ID"
            value={info?.project_id ?? '—'}
            copyValue={info?.project_id}
            canCopy={Boolean(info?.project_id)}
          />
          <InfoRow
            icon={<Key size={11} />}
            label="Clé de tracking publique"
            value={info?.public_tracking_key ?? '—'}
            copyValue={info?.public_tracking_key ?? undefined}
            canCopy={Boolean(info?.public_tracking_key)}
          />
          <InfoRow
            icon={<Key size={11} />}
            label="Clé API (masquée)"
            value={info?.secret_api_key_masked ?? API_KEY_MASK}
          />
        </div>
      </FormCard>

      {isConnected && (
        <Button
          size="sm"
          onClick={() => setShowInstructions((visible) => !visible)}
        >
          <Code2 size={14} />
          {showInstructions ? 'Masquer les instructions d’installation' : 'Voir les instructions d’installation'}
        </Button>
      )}

      {hasInstructionsVisible && (
        <>
          {/* Step-by-step instructions */}
          <FormCard
            title="Comment connecter votre blog"
            description="Suivez ces 4 étapes pour activer le tracking et les analyses SEO."
          >
            <ol className="flex flex-col gap-3">
              {[
                { n: 1, text: 'Copiez le snippet ci-dessous (bouton "Copier" à droite du code).' },
                { n: 2, text: 'Collez-le dans la balise <head> de votre site, avant </head>.' },
                { n: 3, text: 'Déployez votre site avec ce changement.' },
                { n: 4, text: 'Revenez ici — le statut passera à "Connecté" dès la première visite enregistrée.' },
              ].map(({ n, text }) => (
                <li key={n} className="flex items-start gap-3">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent/10 text-[12px] font-semibold text-accent mt-0.5">
                    {n}
                  </span>
                  <span className="text-[14px] text-secondary leading-snug">{text}</span>
                </li>
              ))}
            </ol>
          </FormCard>

          {/* Tracking snippet */}
          <FormCard
            title="Snippet de tracking"
            description="Collez ce code dans le <head> de votre site pour activer le tracking et la connexion API."
          >
            <div className="flex flex-col gap-3">
              <div className="overflow-hidden rounded-[12px] border-2 border-border">
                <div className="flex items-center justify-between bg-surface-soft px-3.5 py-2">
                  <div className="flex items-center gap-2 text-[12px] text-secondary">
                    <Code2 size={13} />
                    HTML
                  </div>
                  <CopyButton value={info?.snippet ?? ''} disabled={!info?.snippet} />
                </div>
                <pre className="overflow-x-auto bg-primary p-4 text-[12px] leading-relaxed text-bg">
                  <code>{info?.snippet}</code>
                </pre>
              </div>
            </div>
          </FormCard>
        </>
      )}

      {/* Public API endpoints */}
      {info?.public_api_endpoints && Object.keys(info.public_api_endpoints).length > 0 && (
        <FormCard
          title="Endpoints API publics"
          description="Ces routes sont accessibles sans authentification pour alimenter votre blog."
        >
          <div className="flex flex-col gap-1.5">
            {Object.entries(info.public_api_endpoints).map(([key, url]) => (
              <InfoRow
                key={key}
                icon={<Globe size={11} />}
                label={key}
                value={url}
                copyValue={url}
                canCopy
              />
            ))}
          </div>
        </FormCard>
      )}

      <FormCard
        title="Publication rapide"
        description="Configurez l'appel de revalidation du site public pour rendre les articles publiés visibles en quelques minutes."
      >
        <form onSubmit={handleSaveRevalidation} className="flex flex-col gap-3">
          <div className="grid gap-3 lg:grid-cols-2">
            <label className="flex flex-col gap-1.5">
              <span className="text-[12px] font-medium text-secondary">URL du site public</span>
              <input
                value={revalidateForm.public_site_url}
                onChange={(event) => {
                  const nextSiteUrl = event.target.value
                  setRevalidateForm((form) => ({
                    ...form,
                    public_site_url: nextSiteUrl,
                    revalidate_url: revalidateEndpointEdited ? form.revalidate_url : deriveRevalidateUrl(nextSiteUrl),
                  }))
                }}
                placeholder="https://www.votresite.com"
                className="rounded-[10px] border border-border bg-surface px-3 py-2 text-[14px] text-primary outline-none focus:border-accent"
              />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-[12px] font-medium text-secondary">Endpoint revalidate</span>
              <input
                value={revalidateForm.revalidate_url}
                onChange={(event) => {
                  const value = event.target.value
                  setRevalidateEndpointEdited(true)
                  setRevalidateForm((form) => ({
                    ...form,
                    revalidate_url: looksLikeEmail(value) ? deriveRevalidateUrl(form.public_site_url) : value,
                  }))
                }}
                placeholder="https://www.votresite.com/api/ideas-studio/revalidate"
                className="rounded-[10px] border border-border bg-surface px-3 py-2 text-[14px] text-primary outline-none focus:border-accent"
              />
              {!revalidateForm.revalidate_url && (
                <span className="text-[12px] text-tertiary">
                  Renseignez l'URL du site public pour générer l'endpoint. Un email ne peut pas servir d'endpoint serveur.
                </span>
              )}
            </label>
          </div>
          <label className="flex flex-col gap-1.5">
            <span className="text-[12px] font-medium text-secondary">Secret de revalidation (propre à ce projet)</span>
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <input
                  readOnly
                  type={showSecret ? 'text' : 'password'}
                  value={info?.revalidate_secret ?? ''}
                  placeholder="Sera généré à l'enregistrement de l'URL du site"
                  className="w-full rounded-[10px] border border-border bg-surface px-3 py-2 pr-8 text-[13px] text-primary outline-none focus:border-accent"
                />
                {info?.revalidate_secret && (
                  <button
                    type="button"
                    onClick={() => setShowSecret((v) => !v)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-tertiary hover:text-primary"
                  >
                    {showSecret ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                )}
              </div>
              {info?.revalidate_secret && <CopyButton value={info.revalidate_secret} />}
              <Button size="sm" variant="ghost" type="button" disabled={rotatingSecret} onClick={handleRotateSecret}>
                <RefreshCw size={13} className={rotatingSecret ? 'animate-spin' : ''} />
                Régénérer
              </Button>
            </div>
            <span className="text-[12px] text-tertiary">
              À coller côté Vercel/Next.js (variable d'environnement lue par votre route /api/ideas-studio/revalidate).
              Chaque projet a son propre secret : pas besoin de le partager entre plusieurs sites.
            </span>
          </label>
          <div className="grid gap-2 lg:grid-cols-3">
            <InfoRow icon={<RefreshCw size={11} />} label="Dernière revalidation" value={info?.last_revalidated_at ? formatDateTime(info.last_revalidated_at) : 'Jamais'} mono={false} />
            <InfoRow icon={<Wifi size={11} />} label="Statut" value={info?.last_revalidate_status ?? 'Non configuré'} mono={false} />
            <InfoRow icon={<WifiOff size={11} />} label="Dernière erreur" value={info?.last_revalidate_error ?? 'Aucune'} mono={false} />
          </div>
          {revalidateMessage && (
            <p className={`text-[12px] ${revalidateMessage.includes('impossible') || revalidateMessage.includes('non configur') ? 'text-danger' : 'text-success'}`}>
              {revalidateMessage}
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              type="submit"
              loading={savingRevalidate}
            >
              Sauvegarder la revalidation
            </Button>
            <Button
              size="sm"
              variant="ghost"
              type="button"
              disabled={manualRevalidating}
              onClick={handleManualRevalidate}
            >
              <RefreshCw size={13} className={manualRevalidating ? 'animate-spin' : ''} />
              Relancer la revalidation
            </Button>
          </div>
        </form>
      </FormCard>

      <FormCard
        title="Google Analytics 4"
        description="Connectez GA4 pour afficher le trafic réel directement dans Analytics, sans repasser par la console Google."
      >
        <form onSubmit={handleSaveGa4} className="flex flex-col gap-3">
          <label className="flex flex-col gap-1.5">
            <span className="text-[12px] font-medium text-secondary">Property ID</span>
            <input
              value={ga4Form.property_id}
              onChange={(event) => setGa4Form((f) => ({ ...f, property_id: event.target.value }))}
              placeholder="ex : 123456789"
              className="rounded-[10px] border border-border bg-surface px-3 py-2 text-[14px] text-primary outline-none focus:border-accent"
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-[12px] font-medium text-secondary">
              Clé de service (JSON) {info?.ga4_configured ? '(laisser vide pour conserver)' : ''}
            </span>
            <textarea
              value={ga4Form.service_account_json}
              onChange={(event) => setGa4Form((f) => ({ ...f, service_account_json: event.target.value }))}
              placeholder='{"type": "service_account", "project_id": "...", ...}'
              rows={4}
              className="rounded-[10px] border border-border bg-surface px-3 py-2 font-mono text-[12px] text-primary outline-none focus:border-accent"
            />
            <span className="text-[11px] text-tertiary">
              Fichier de clé JSON d'un compte de service Google Cloud avec accès en lecture à cette propriété GA4.
              Jamais renvoyé en clair une fois enregistré.
            </span>
          </label>
          <div className="flex items-center gap-2">
            <InfoRow icon={<Wifi size={11} />} label="Statut" value={info?.ga4_configured ? 'Connecté' : 'Non configuré'} mono={false} />
          </div>
          {ga4Message && (
            <p className={`text-[12px] ${ga4Message.includes('impossible') ? 'text-danger' : 'text-success'}`}>
              {ga4Message}
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            <Button size="sm" type="submit" loading={savingGa4}>
              Sauvegarder Google Analytics
            </Button>
          </div>
        </form>
      </FormCard>

      {/* Key notice */}
      <div className="flex items-start gap-2.5 rounded-[16px] bg-surface-soft px-4 py-3">
        <Key size={14} className="mt-0.5 shrink-0 text-tertiary" />
        <p className="text-[12px] text-secondary leading-relaxed">
          La clé API secrète n'est jamais renvoyée en clair au frontend. Utilisez uniquement les valeurs publiques pour le tracking et contactez un administrateur si une rotation de clé est nécessaire.
        </p>
      </div>

      <ConfirmModal
        open={disconnectOpen}
        onClose={() => !disconnecting && setDisconnectOpen(false)}
        onConfirm={handleDisconnect}
        title="Déconnecter le site ?"
        description="Le statut repassera à Non connecté. Les clés de tracking existantes seront conservées. Vous pourrez reconnecter le site à tout moment."
        confirmLabel="Déconnecter"
        loading={disconnecting}
        variant="danger"
      />
    </div>
  )
}
