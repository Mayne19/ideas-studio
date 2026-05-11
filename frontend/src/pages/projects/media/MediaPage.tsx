import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Image, Upload, Trash2, Copy, Check, Loader2 } from 'lucide-react'
import { listMedia, uploadMedia, deleteMedia } from '@/api/media'
import type { MediaAsset } from '@/api/media'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'
import Button from '@/components/ui/Button'

function formatBytes(n: number | null) {
  if (!n) return ''
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

function MediaCard({ asset, onDelete }: { asset: MediaAsset; onDelete: () => void }) {
  const [copied, setCopied] = useState(false)
  const [deleting, setDeleting] = useState(false)

  async function handleCopy() {
    await navigator.clipboard.writeText(asset.url)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  async function handleDelete() {
    setDeleting(true)
    try {
      await deleteMedia(asset.id)
      onDelete()
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="group flex flex-col rounded-[16px] bg-surface overflow-hidden">
      <div className="relative bg-[#f5f5f7] h-36 flex items-center justify-center">
        {asset.mime_type?.startsWith('image/') ? (
          <img src={asset.url} alt={asset.alt_text ?? ''} className="w-full h-full object-cover" />
        ) : (
          <Image size={28} className="text-tertiary" />
        )}
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100">
          <button
            onClick={handleCopy}
            className="flex h-8 w-8 items-center justify-center rounded-full bg-white/90 text-primary hover:bg-white transition-colors"
            title="Copier l'URL"
          >
            {copied ? <Check size={14} className="text-success" /> : <Copy size={14} />}
          </button>
          <button
            onClick={handleDelete}
            className="flex h-8 w-8 items-center justify-center rounded-full bg-white/90 text-danger hover:bg-white transition-colors"
            title="Supprimer"
            disabled={deleting}
          >
            {deleting ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
          </button>
        </div>
      </div>
      <div className="px-3 py-2">
        <p className="text-[12px] font-medium text-primary truncate" title={asset.filename ?? asset.url}>
          {asset.filename ?? asset.url.split('/').pop() ?? 'Image'}
        </p>
        {asset.size && (
          <p className="text-[11px] text-tertiary">{formatBytes(asset.size)}</p>
        )}
      </div>
    </div>
  )
}

export default function MediaPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [assets, setAssets] = useState<MediaAsset[]>([])
  const [loadStatus, setLoadStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [uploading, setUploading] = useState(false)
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

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-6 flex items-start justify-between">
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
          <div className="flex h-12 w-12 items-center justify-center rounded-[16px] bg-[#f0f0f2] text-tertiary">
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
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {assets.map((asset) => (
            <MediaCard
              key={asset.id}
              asset={asset}
              onDelete={() => setAssets((prev) => prev.filter((a) => a.id !== asset.id))}
            />
          ))}
        </div>
      )}
    </div>
  )
}
