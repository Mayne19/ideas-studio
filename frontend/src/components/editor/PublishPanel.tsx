import { useState } from 'react'
import { AlertCircle, Calendar } from '@/components/ui/hugeIcons'
import { publishArticle, unpublishArticle, markReadyArticle, archiveArticle, scheduleArticle, rollbackArticle } from '@/api/articles'
import { ApiError } from '@/api/client'
import type { EditorArticle } from '@/types'
import { formatDate } from '@/utils/format'
import Button from '@/components/ui/Button'
import StatusBadge from '@/components/ui/StatusBadge'

function translatePublishError(err: unknown): string {
  if (err instanceof ApiError) {
    switch (err.status) {
      case 403: return 'Vous n\'avez pas la permission d\'effectuer cette action.'
      case 409: return 'Cette action n\'est pas possible dans l\'état actuel de l\'article.'
      case 422: return 'Données invalides. Vérifiez le contenu de l\'article.'
      default: return err.message || `Erreur ${err.status}`
    }
  }
  return 'Une erreur inattendue est survenue.'
}

export default function PublishPanel({
  article,
  projectId,
  onUpdate,
}: {
  article: EditorArticle
  projectId: string
  onUpdate: (a: EditorArticle) => void
}) {
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [scheduleOpen, setScheduleOpen] = useState(false)
  const [scheduleDate, setScheduleDate] = useState('')

  async function doAction(key: string) {
    setLoadingAction(key)
    setError('')
    try {
      let updated
      if (key === 'publish') updated = await publishArticle(projectId, article.id)
      else if (key === 'unpublish') updated = await unpublishArticle(projectId, article.id)
      else if (key === 'mark-ready') updated = await markReadyArticle(projectId, article.id)
      else if (key === 'archive') updated = await archiveArticle(projectId, article.id)
      if (updated) onUpdate({ ...article, ...updated })
    } catch (err) {
      setError(translatePublishError(err))
    } finally {
      setLoadingAction(null)
    }
  }

  async function handleSchedule() {
    if (!scheduleDate) return
    setLoadingAction('schedule')
    setError('')
    try {
      const updated = await scheduleArticle(projectId, article.id, new Date(scheduleDate).toISOString())
      onUpdate({ ...article, ...updated })
      setScheduleOpen(false)
      setScheduleDate('')
    } catch (err) {
      setError(translatePublishError(err))
    } finally {
      setLoadingAction(null)
    }
  }

  const busy = loadingAction !== null

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-[12px] text-secondary">Statut</span>
        <StatusBadge status={article.status} />
      </div>
      {article.word_count > 0 && (
        <div className="flex items-center justify-between">
          <span className="text-[12px] text-secondary">Mots</span>
          <span className="text-[12px] text-primary">{article.word_count.toLocaleString('fr-FR')}</span>
        </div>
      )}
      {article.published_at && (
        <div className="flex items-center justify-between">
          <span className="text-[12px] text-secondary">Publié le</span>
          <span className="text-[12px] text-primary">{formatDate(article.published_at)}</span>
        </div>
      )}
      {article.scheduled_at && (
        <div className="flex items-center justify-between">
          <span className="text-[12px] text-secondary">Planifié le</span>
          <span className="text-[12px] text-primary">{formatDate(article.scheduled_at)}</span>
        </div>
      )}

      {error && (
        <div className="flex items-start gap-2 rounded-[8px] border border-danger/20 bg-danger/5 px-2.5 py-2 text-[12px] text-danger">
          <AlertCircle size={12} className="mt-0.5 shrink-0" />
          <span className="leading-snug">{error}</span>
        </div>
      )}

      <div className="flex flex-col gap-1.5 pt-1">
        {article.status !== 'published' && (
          <Button
            size="sm"
            className="w-full justify-center"
            loading={loadingAction === 'publish'}
            disabled={busy}
            onClick={() => doAction('publish')}
          >
            Publier
          </Button>
        )}
        {article.status === 'published' && (
          <>
            <Button
              size="sm"
              variant="secondary"
              className="w-full justify-center"
              loading={loadingAction === 'unpublish'}
              disabled={busy}
              onClick={() => doAction('unpublish')}
            >
              Dépublier
            </Button>
            <Button
              size="sm"
              variant="secondary"
              className="w-full justify-center"
              loading={loadingAction === 'rollback'}
              disabled={busy}
              onClick={async () => {
                if (!window.confirm('Revenir à la version précédente publiée ?')) return
                setLoadingAction('rollback')
                setError('')
                try {
                  const updated = await rollbackArticle(projectId, article.id)
                  onUpdate({ ...article, ...updated })
                } catch (err) {
                  setError(err instanceof ApiError && err.status === 404
                    ? 'Aucun snapshot de publication disponible.'
                    : translatePublishError(err))
                } finally {
                  setLoadingAction(null)
                }
              }}
            >
              Revenir à la version précédente
            </Button>
          </>
        )}
        {!['published', 'ready_to_publish', 'archived'].includes(article.status) && (
          <Button
            size="sm"
            variant="secondary"
            className="w-full justify-center"
            loading={loadingAction === 'mark-ready'}
            disabled={busy}
            onClick={() => doAction('mark-ready')}
          >
            Marquer prêt à publier
          </Button>
        )}

        {/* Schedule button */}
        {!['published', 'archived', 'scheduled'].includes(article.status) && (
          <Button
            size="sm"
            variant="secondary"
            icon={<Calendar size={12} />}
            className="w-full justify-center"
            disabled={busy}
            onClick={() => setScheduleOpen(!scheduleOpen)}
          >
            Programmer
          </Button>
        )}

        {scheduleOpen && (
          <div className="rounded-[10px] border border-border bg-surface-soft p-3 flex flex-col gap-2">
            <label className="text-[12px] text-secondary">Date et heure de publication</label>
            <input
              type="datetime-local"
              value={scheduleDate}
              onChange={(e) => setScheduleDate(e.target.value)}
              className="w-full rounded-[8px] border border-border bg-white px-2.5 py-1.5 text-[12px] text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent/20"
            />
            <div className="flex gap-1.5">
              <button
                onClick={() => { setScheduleOpen(false); setScheduleDate('') }}
                className="flex-1 rounded-[8px] border border-border py-1.5 text-[12px] text-secondary hover:bg-surface-muted transition-colors"
              >
                Annuler
              </button>
              <button
                onClick={handleSchedule}
                disabled={!scheduleDate || busy}
                className="flex-1 rounded-[8px] bg-accent py-1.5 text-[12px] font-medium text-white hover:bg-accent/90 transition-colors disabled:opacity-40"
              >
                {loadingAction === 'schedule' ? '…' : 'Confirmer'}
              </button>
            </div>
          </div>
        )}

        {article.status !== 'archived' && (
          <Button
            size="sm"
            variant="ghost"
            className="w-full justify-center text-danger hover:text-danger"
            loading={loadingAction === 'archive'}
            disabled={busy}
            onClick={() => doAction('archive')}
          >
            Archiver
          </Button>
        )}
      </div>
    </div>
  )
}
