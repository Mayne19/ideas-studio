import { useRef, useState } from 'react'
import { Image, Upload, Loader2, X } from '@/components/ui/hugeIcons'
import { uploadMedia } from '@/api/media'

export default function MediaPanel({
  coverImageUrl,
  onChange,
  projectId,
}: {
  coverImageUrl: string
  onChange: (url: string) => void
  projectId: string
}) {
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setUploadError('')
    try {
      const media = await uploadMedia(projectId, file)
      onChange(media.public_url ?? media.url)
    } catch {
      setUploadError("Echec de l'upload media.")
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  return (
    <div className="flex flex-col gap-3">
      {coverImageUrl ? (
        <div className="relative">
          <img src={coverImageUrl} alt="" className="h-32 w-full rounded-[10px] object-cover" />
          <button
            type="button"
            onClick={() => onChange('')}
            className="absolute right-1.5 top-1.5 flex h-6 w-6 items-center justify-center rounded-full bg-black/55 text-white transition-colors hover:bg-black/75"
            title="Supprimer l'image"
          >
            <X size={12} />
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          className="flex flex-col items-center gap-2 rounded-[10px] border border-dashed border-border py-6 transition-colors hover:border-accent/50 hover:bg-accent/3"
          disabled={uploading}
        >
          {uploading ? (
            <Loader2 size={20} className="animate-spin text-accent" />
          ) : (
            <Upload size={20} className="text-tertiary" />
          )}
          <p className="text-[11px] text-tertiary">
            {uploading ? 'Upload en cours...' : 'Uploader une image'}
          </p>
        </button>
      )}

      <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleFileChange} />

      <div>
        <label className="mb-1 block text-[11px] font-medium text-secondary">URL de secours</label>
        <input
          type="text"
          value={coverImageUrl}
          onChange={(e) => onChange(e.target.value)}
          placeholder="https://..."
          className="w-full rounded-[8px] border border-border bg-surface px-2.5 py-1.5 text-[12px] text-primary placeholder:text-tertiary transition-colors focus:border-accent/60 focus:outline-none focus:ring-1 focus:ring-accent/50"
        />
      </div>

      {uploadError && <p className="text-[11px] text-danger">{uploadError}</p>}

      <button
        type="button"
        onClick={() => fileRef.current?.click()}
        className="flex items-center justify-center gap-1.5 rounded-[8px] border border-border bg-surface px-3 py-1.5 text-[12px] font-medium text-secondary transition-colors hover:bg-surface-soft hover:text-primary"
        disabled={uploading}
      >
        <Image size={12} />
        {coverImageUrl ? 'Remplacer' : 'Choisir un fichier'}
      </button>
    </div>
  )
}
