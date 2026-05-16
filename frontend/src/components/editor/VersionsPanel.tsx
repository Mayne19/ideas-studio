import { useEffect, useState } from 'react'
import { RotateCcw } from 'lucide-react'
import { listVersions, restoreVersion } from '@/api/editor'
import type { ArticleVersion, EditorArticle, ProjectMember } from '@/types'
import { formatDateTime } from '@/utils/format'
import ConfirmModal from '@/components/ui/ConfirmModal'

const VERSION_TYPE_LABELS: Record<string, string> = {
  manual: 'Manuel',
  autosave: 'Auto',
  restore: 'Restauration',
}

export default function VersionsPanel({
  projectId,
  articleId,
  members = [],
  onRestore,
}: {
  projectId: string
  articleId: string
  members?: ProjectMember[]
  onRestore: (article: EditorArticle) => void
}) {
  const [versions, setVersions] = useState<ArticleVersion[]>([])
  const [loading, setLoading] = useState(true)
  const [restoring, setRestoring] = useState<string | null>(null)
  const [restoreTarget, setRestoreTarget] = useState<ArticleVersion | null>(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    listVersions(projectId, articleId)
      .then(setVersions)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [projectId, articleId])

  async function handleRestore() {
    if (!restoreTarget) return
    setRestoring(restoreTarget.id)
    setMessage('')
    setError('')
    try {
      const article = await restoreVersion(projectId, articleId, restoreTarget.id)
      onRestore(article)
      setMessage('Version restaurée. Sauvegardez pour confirmer le contenu restauré.')
      setRestoreTarget(null)
    } catch (err) {
      console.error(err)
      setError('Impossible de restaurer cette version.')
    } finally {
      setRestoring(null)
    }
  }

  function authorLabel(authorId: string | null): string {
    if (!authorId) return ''
    const member = members.find((item) => item.user_id === authorId || item.id === authorId)
    return member?.user_name || member?.user_email || authorId
  }

  if (loading) {
    return <p className="text-[11px] text-tertiary text-center py-4">Chargement...</p>
  }

  if (versions.length === 0) {
    return <p className="text-[11px] text-tertiary text-center py-4">Aucune version sauvegardée.</p>
  }

  return (
    <>
      <div className="flex flex-col gap-1.5">
        {message && <p className="rounded-[8px] bg-success/8 px-2 py-1.5 text-[11px] text-success">{message}</p>}
        {error && <p className="rounded-[8px] bg-danger/8 px-2 py-1.5 text-[11px] text-danger">{error}</p>}
        {versions.map((v) => (
          <div
            key={v.id}
            className="flex items-center gap-2 rounded-[8px] border border-transparent px-2 py-1.5 hover:border-border hover:bg-[#f0f0f2]"
          >
            <div className="flex-1 min-w-0">
              <p className="text-[11px] font-medium text-primary truncate">v{v.version_number} — {v.title}</p>
              <p className="text-[10px] text-tertiary">
                {VERSION_TYPE_LABELS[v.version_type] ?? v.version_type} · {formatDateTime(v.created_at)}
                {v.created_by ? ` · Auteur ${authorLabel(v.created_by)}` : ''}
              </p>
            </div>
            <button
              onClick={() => setRestoreTarget(v)}
              disabled={restoring === v.id}
              className="flex h-6 w-6 items-center justify-center rounded-[6px] text-tertiary transition-colors hover:bg-[#e5e5e7] hover:text-primary disabled:opacity-40"
              title="Restaurer cette version"
            >
              <RotateCcw size={12} />
            </button>
          </div>
        ))}
      </div>

      <ConfirmModal
        open={!!restoreTarget}
        onClose={() => setRestoreTarget(null)}
        onConfirm={handleRestore}
        title="Restaurer cette version ?"
        description="Le contenu actuel de l'éditeur sera remplacé par cette version. Vous pourrez encore vérifier le résultat avant de sauvegarder."
        confirmLabel="Restaurer"
        loading={!!restoring}
        variant="primary"
      />
    </>
  )
}
