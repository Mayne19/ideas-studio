import { useEffect, useState } from 'react'
import { MessageCircle, Check, Trash2, Loader2 } from 'lucide-react'
import { listComments, resolveComment, deleteComment } from '@/api/comments'
import type { ArticleComment } from '@/api/comments'

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "A l'instant"
  if (mins < 60) return `Il y a ${mins} min`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `Il y a ${hours} h`
  const days = Math.floor(hours / 24)
  return `Il y a ${days} j`
}

function CommentItem({
  comment,
  selected,
  onResolve,
  onDelete,
  onSelect,
}: {
  comment: ArticleComment
  selected?: boolean
  onResolve: (id: string, resolved: boolean) => Promise<void> | void
  onDelete: (id: string) => Promise<void> | void
  onSelect?: (comment: ArticleComment) => void
}) {
  const [toggling, setToggling] = useState(false)
  const [deleting, setDeleting] = useState(false)

  async function handleResolve() {
    if (comment.resolved) return
    setToggling(true)
    try { await onResolve(comment.id, true) } finally { setToggling(false) }
  }

  async function handleDelete() {
    setDeleting(true)
    try { await onDelete(comment.id) } finally { setDeleting(false) }
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onSelect?.(comment)}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') onSelect?.(comment)
      }}
      className={`rounded-[10px] border p-3 text-left transition-colors ${
        selected
          ? 'border-accent bg-accent/6'
          : comment.resolved
            ? 'border-border bg-[#f9f9fb] opacity-65'
            : 'border-border bg-surface'
      } ${onSelect ? 'cursor-pointer hover:border-accent/50' : ''}`}
    >
      <div className="mb-1.5 flex items-center justify-between">
        <span className="text-[11px] font-semibold text-primary">{comment.author_name}</span>
        <div className="flex items-center gap-1">
          <span className="text-[10px] text-tertiary">{timeAgo(comment.created_at)}</span>
          <button
            onClick={(event) => {
              event.stopPropagation()
              void handleResolve()
            }}
            disabled={toggling}
            className={`flex h-5 w-5 items-center justify-center rounded-full transition-colors ${
              comment.resolved
                ? 'bg-success/10 text-[#1a7a3a]'
                : 'text-tertiary hover:bg-success/10 hover:text-[#1a7a3a]'
            }`}
            title={comment.resolved ? 'Resolu' : 'Valider le commentaire'}
          >
            {toggling ? <Loader2 size={10} className="animate-spin" /> : <Check size={10} />}
          </button>
          <button
            onClick={(event) => {
              event.stopPropagation()
              void handleDelete()
            }}
            disabled={deleting}
            className="flex h-5 w-5 items-center justify-center rounded-full text-tertiary transition-colors hover:bg-danger/10 hover:text-danger"
            title="Supprimer"
          >
            {deleting ? <Loader2 size={10} className="animate-spin" /> : <Trash2 size={10} />}
          </button>
        </div>
      </div>
      {comment.selected_text && (
        <p className="mb-1.5 rounded-[7px] bg-accent/6 px-2 py-1 text-[10px] leading-snug text-secondary">
          "{comment.selected_text}"
        </p>
      )}
      <p className="text-[12px] leading-snug text-primary">{comment.text}</p>
      {comment.resolved && (
        <span className="mt-1.5 inline-flex items-center gap-1 text-[10px] font-medium text-[#1a7a3a]">
          <Check size={9} />
          Resolu
        </span>
      )}
    </div>
  )
}

export default function CommentsPanel({
  articleId,
  comments: managedComments,
  loading: managedLoading,
  selectedCommentId,
  onResolve,
  onDelete,
  onSelect,
}: {
  articleId: string
  comments?: ArticleComment[]
  loading?: boolean
  selectedCommentId?: string | null
  onResolve?: (id: string, resolved: boolean) => Promise<void> | void
  onDelete?: (id: string) => Promise<void> | void
  onSelect?: (comment: ArticleComment) => void
}) {
  const [localComments, setLocalComments] = useState<ArticleComment[]>([])
  const [localLoading, setLocalLoading] = useState(true)
  const comments = managedComments ?? localComments
  const loading = managedLoading ?? localLoading

  useEffect(() => {
    if (managedComments) return
    let active = true
    Promise.resolve().then(() => { if (active) setLocalLoading(true) })
    listComments(articleId)
      .then((items) => { if (active) setLocalComments(items) })
      .catch(() => {})
      .finally(() => { if (active) setLocalLoading(false) })
    return () => { active = false }
  }, [articleId, managedComments])

  async function handleResolve(id: string, resolved: boolean) {
    if (onResolve) {
      await onResolve(id, resolved)
      return
    }
    const updated = await resolveComment(articleId, id, resolved)
    setLocalComments((prev) => prev.map((c) => c.id === id ? updated : c))
  }

  async function handleDelete(id: string) {
    if (onDelete) {
      await onDelete(id)
      return
    }
    await deleteComment(articleId, id)
    setLocalComments((prev) => prev.filter((c) => c.id !== id))
  }

  const open = comments.filter((c) => !c.resolved)
  const resolved = comments.filter((c) => c.resolved)

  return (
    <div className="flex flex-col gap-3">
      <p className="rounded-[8px] bg-[#f9f9fb] px-2.5 py-2 text-[11px] leading-snug text-secondary">
        Pour ajouter un commentaire, passez en mode Commentaire et selectionnez un passage dans l'article.
      </p>

      {loading && (
        <p className="py-4 text-center text-[11px] text-tertiary">Chargement...</p>
      )}

      {!loading && comments.length === 0 && (
        <div className="flex flex-col items-center gap-2 py-6 text-center">
          <MessageCircle size={18} className="text-tertiary opacity-40" />
          <p className="text-[11px] text-tertiary">Aucun commentaire pour l'instant.</p>
        </div>
      )}

      {open.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-secondary">
            Ouverts ({open.length})
          </p>
          {open.map((c) => (
            <CommentItem
              key={c.id}
              comment={c}
              selected={selectedCommentId === c.id}
              onResolve={handleResolve}
              onDelete={handleDelete}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}

      {resolved.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-secondary">
            Resolus ({resolved.length})
          </p>
          {resolved.map((c) => (
            <CommentItem
              key={c.id}
              comment={c}
              selected={selectedCommentId === c.id}
              onResolve={handleResolve}
              onDelete={handleDelete}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  )
}
