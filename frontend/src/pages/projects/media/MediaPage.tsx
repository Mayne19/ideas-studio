import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { ExternalLink, Image, Upload, Trash2, Copy, Check, Loader2 } from '@/components/ui/hugeIcons'
import { listMedia, uploadMedia, deleteMedia } from '@/api/media'
import type { MediaAsset } from '@/api/media'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'
import Button from '@/components/ui/Button'
import ConfirmModal from '@/components/ui/ConfirmModal'

function formatBytes(n: number | null) {
  if (!n) return ''
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

const API_BASE_URL = (import.meta.env['VITE_API_URL'] as string | undefined) ?? 'http://localhost:8000'

function mediaUrl(asset: MediaAsset) {
  const publicUrl = asset.public_url || ''
  const raw = publicUrl.includes('localhost') || publicUrl.includes('127.0.0.1') ? asset.url : (asset.public_url || asset.url)
  if (!raw) return ''
  if (raw.startsWith('/')) return `${API_BASE_URL}${raw}`
  return raw
}

function mediaUrlCandidates(asset: MediaAsset) {
  const values = [asset.public_url, asset.url]
    .filter((value): value is string => Boolean(value))
    .map((value) => {
      if (value.startsWith('/')) return `${API_BASE_URL}${value}`
      if (!value.startsWith('http') && !value.startsWith('blob:')) return `${API_BASE_URL}/${value.replace(/^\/+/, '')}`
      return value
    })
  return Array.from(new Set(values))
}

function MediaCard({ asset, onDelete }: { asset: MediaAsset; onDelete: () => void }) {
  const [copied, setCopied] = useState(false)
  const [imageIndex, setImageIndex] = useState(0)
  const [imageLoaded, setImageLoaded] = useState(false)
  const candidates = mediaUrlCandidates(asset)
  const src = candidates[imageIndex] || mediaUrl(asset)
  const imageFailed = asset.mime_type?.startsWith('image/') && candidates.length > 0 && imageIndex >= candidates.length

  async function handleCopy() {
    await navigator.clipboard.writeText(src)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="group flex flex-col overflow-hidden rounded-[14px] border border-border bg-surface">
      <div className="relative flex aspect-[4/3] items-center justify-center bg-surface-soft">
        {asset.mime_type?.startsWith('image/') && src && !imageFailed ? (
          <>
          {!imageLoaded && (
            <div className="absolute inset-0 flex items-center justify-center bg-surface-soft text-tertiary">
              <Loader2 size={18} className="animate-spin" />
            </div>
          )}
          <img
            src={src}
            alt={asset.alt_text ?? ''}
            className="h-full w-full object-cover"
            onLoad={() => setImageLoaded(true)}
            onError={() => {
              setImageLoaded(false)
              setImageIndex((index) => index + 1)
            }}
          />
          </>
        ) : (
          <div className="flex flex-col items-center gap-2 text-tertiary">
            <Image size={28} />
            <span className="text-[11px]">{imageFailed ? 'Aperçu indisponible' : asset.mime_type?.split('/')[1]?.toUpperCase() ?? 'FICHIER'}</span>
          </div>
        )}
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100">
          <button
            onClick={handleCopy}
            className="flex h-8 w-8 items-center justify-center rounded-full bg-white/90 text-primary hover:bg-white transition-colors"
            title="Copier l'URL"
          >
            {copied ? <Check size={14} className="text-success" /> : <Copy size={14} />}
          </button>
          {src && (
            <a
              href={src}
              target="_blank"
              rel="noreferrer"
              className="flex h-8 w-8 items-center justify-center rounded-full bg-white/90 text-primary transition-colors hover:bg-white"
              title="Ouvrir"
            >
              <ExternalLink size={14} />
            </a>
          )}
          <button
            onClick={onDelete}
            className="flex h-8 w-8 items-center justify-center rounded-full bg-white/90 text-danger hover:bg-white transition-colors"
            title="Supprimer"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>
      <div className="px-3 py-2">
        <p className="text-[12px] font-medium text-primary truncate" title={asset.filename ?? asset.url}>
          {asset.filename ?? src.split('/').pop() ?? 'Image'}
        </p>
        <p className="mt-0.5 truncate text-[11px] text-tertiary">
          {[formatBytes(asset.size), asset.mime_type ?? 'type inconnu', asset.article_id ? 'lié article' : 'non lié'].filter(Boolean).join(' · ')}
        </p>
        <p className="mt-0.5 text-[11px] text-tertiary">
          {new Date(asset.created_at).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' })}
        </p>
      </div>
    </div>
  )
}

export default function MediaPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [assets, setAssets] = useState<MediaAsset[]>([])
  const [loadStatus, setLoadStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [uploading, setUploading] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<MediaAsset | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [tick, setTick] = useState(0)
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    Promise.resolve().then(() => { if (!cancelled) setLoadStatus('loading') })
    listMedia(projectId)
      .then((data) => { if (!cancelled) { setAssets(data); setLoadStatus('success') } })
      .catch(() => { if (!cancelled) setLoadStatus('error') })
    return () => { cancelled = true }
  }, [projectId, tick])

  async function handleFiles(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? [])
    if (!files.length || !projectId) return
    setUploading(true)
    try {
      for (const file of files) {
        const asset = await uploadMedia(projectId, file)
        setAssets((prev) => [asset, ...prev])
      }
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await deleteMedia(deleteTarget.id)
      setAssets((prev) => prev.filter((asset) => asset.id !== deleteTarget.id))
      setDeleteTarget(null)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="project-page project-page--wide">
      <div className="project-page-header">
        <div>
          <h1 className="text-[20px] font-semibold text-primary tracking-tight">Médiathèque</h1>
          <p className="mt-0.5 text-[13px] text-secondary">Images et fichiers associés à ce projet.</p>
        </div>
        <Button
          icon={uploading ? <Loader2 size={13} className="animate-spin" /> : <Upload size={13} />}
          loading={uploading}
          onClick={() => fileRef.current?.click()}
        >
          Ajouter des médias
        </Button>
      </div>

      <input ref={fileRef} type="file" accept="image/*" multiple className="hidden" onChange={handleFiles} />

      {loadStatus === 'loading' && <LoadingState />}
      {loadStatus === 'error' && <ErrorState onRetry={() => setTick((t) => t + 1)} />}

      {loadStatus === 'success' && assets.length === 0 && (
        <div className="flex flex-col items-center gap-4 py-20 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-[16px] bg-surface-soft text-tertiary">
            <Image size={22} />
          </div>
          <div>
            <p className="text-[15px] font-medium text-primary">Aucun média</p>
            <p className="mt-1 max-w-xs text-[13px] text-secondary">
              Ajoutez des images pour les utiliser dans vos articles.
            </p>
          </div>
          <button
            onClick={() => fileRef.current?.click()}
            className="flex items-center gap-1.5 rounded-[10px] bg-accent px-4 py-2 text-[13px] font-medium text-white hover:bg-accent/90 transition-colors"
          >
            <Upload size={13} />
            Importer des images
          </button>
        </div>
      )}

      {loadStatus === 'success' && assets.length > 0 && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
          {assets.map((asset) => (
            <MediaCard
              key={asset.id}
              asset={asset}
              onDelete={() => setDeleteTarget(asset)}
            />
          ))}
        </div>
      )}

      <ConfirmModal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        title="Supprimer ce média ?"
        description={`Le fichier « ${deleteTarget?.filename ?? 'Image'} » sera supprimé de la médiathèque. Cette action est irréversible.`}
        confirmLabel="Supprimer"
        loading={deleting}
        variant="danger"
      />
    </div>
  )
}
