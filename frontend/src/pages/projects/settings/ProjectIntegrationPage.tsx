import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { useParams } from 'react-router-dom'
import { Code2, Globe, Key, Power, RefreshCw, Wifi, WifiOff } from '@/components/ui/hugeIcons'
import { getConnectInfo, disconnectProject, revalidateProject, updateProject } from '@/api/projects'
import type { ConnectInfo } from '@/types'
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
  const derived = deriveRevalidateUrl(publicSiteUrl)
  const safeEndpoint = looksLikeEmail(endpoint) ? '' : endpoint
  return {
    public_site_url: publicSiteUrl,
    revalidate_url: safeEndpoint || derived,
    revalidate_secret: '',
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
    <div className="flex items-start justify-between gap-3 rounded-[12px] bg-surface-soft px-4 py-3">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5 text-[12px] font-medium uppercase tracking-wider text-tertiary">
          {icon}
          {label}
        </div>
        <p className={`mt-0.5 truncate text-[12px] text-secondary ${mono ? 'font-mono' : ''}`}>{value}</p>
      </div>
      {(action || canCopy) && (
        <div className="flex shrink-0 items-center gap-2">
          {action}
          {canCopy && <CopyButton value={copyValue ?? value} disabled={!(copyValue ?? value)} className="shrink-0" />}
        </div>
      )}
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
  const [revalidateForm, setRevalidateForm] = useState({ public_site_url: '', revalidate_url: '', revalidate_secret: '' })
  const [savingRevalidate, setSavingRevalidate] = useState(false)
  const [manualRevalidating, setManualRevalidating] = useState(false)
  const [revalidateMessage, setRevalidateMessage] = useState('')

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
        setStatus('success')
      })
      .catch(() => setStatus('error'))
  }, [projectId])

  if (status === 'loading') return <LoadingState />
  if (status === 'error') return <ErrorState onRetry={loadInfo} />

  const isConnected = info?.status === 'connected'
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
        public_site_url: revalidateForm.public_site_url || null,
        revalidate_url: safeEndpoint || null,
        revalidate_secret: revalidateForm.revalidate_secret || undefined,
      })
      const data = await getConnectInfo(projectId)
      setInfo(data)
      setRevalidateForm(cleanRevalidateForm(data))
      setRevalidateMessage('Configuration sauvegardée.')
    } catch (err) {
      setRevalidateMessage(err instanceof Error ? err.message : 'Sauvegarde impossible.')
    } finally {
      setSavingRevalidate(false)
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
        <div className="flex flex-col gap-2">
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
            copyValue={info?.public_tracking_key}
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
          <div className="flex flex-col gap-2">
            {Object.entries(info.public_api_endpoints).map(([key, url]) => (
              <div
                key={key}
                className="flex items-start justify-between gap-3 rounded-[12px] bg-surface-soft px-4 py-3"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5 text-[12px] font-medium uppercase tracking-wider text-tertiary">
                    <Globe size={11} />
                    {key}
                  </div>
                  <p className="mt-0.5 truncate font-mono text-[12px] text-secondary">{url}</p>
                </div>
                <CopyButton value={url} className="shrink-0" />
              </div>
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
                  setRevalidateForm((form) => {
                    const shouldDerive = !form.revalidate_url || looksLikeEmail(form.revalidate_url) || form.revalidate_url === deriveRevalidateUrl(form.public_site_url)
                    return {
                      ...form,
                      public_site_url: nextSiteUrl,
                      revalidate_url: shouldDerive ? deriveRevalidateUrl(nextSiteUrl) : form.revalidate_url,
                    }
                  })
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
            <span className="text-[12px] font-medium text-secondary">
              Secret de revalidation {info?.revalidate_secret_configured ? '(déjà configuré)' : ''}
            </span>
            <input
              value={revalidateForm.revalidate_secret}
              onChange={(event) => setRevalidateForm((form) => ({ ...form, revalidate_secret: event.target.value }))}
              placeholder={info?.revalidate_secret_configured ? 'Laisser vide pour conserver le secret actuel' : 'Secret partagé avec le site public'}
              type="password"
              className="rounded-[10px] border border-border bg-surface px-3 py-2 text-[14px] text-primary outline-none focus:border-accent"
            />
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
