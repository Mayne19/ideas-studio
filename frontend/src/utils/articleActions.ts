import { ArticleStatus, ARTICLE_STATUS_META, type ArticleStatusCode } from '@/lib/status'

export type ArticleAction = {
  key: string
  label: string
  variant: 'primary' | 'secondary' | 'danger'
}

export const STATUS_LABELS: Record<ArticleStatusCode, string> = Object.fromEntries(
  Object.entries(ARTICLE_STATUS_META).map(([code, meta]) => [Number(code), meta.label]),
) as Record<ArticleStatusCode, string>

export function getAvailableActions(status: ArticleStatusCode): ArticleAction[] {
  const actions: ArticleAction[] = []

  if (status === ArticleStatus.ARCHIVED) {
    actions.push({ key: 'restore', label: 'Restaurer en production', variant: 'secondary' })
    actions.push({ key: 'republish', label: 'Republier directement', variant: 'primary' })
    actions.push({ key: 'delete', label: 'Supprimer', variant: 'danger' })
    return actions
  }

  if (status === ArticleStatus.PUBLISHED) {
    actions.push({ key: 'unpublish', label: 'Dépublier', variant: 'secondary' })
    actions.push({ key: 'archive', label: 'Archiver', variant: 'danger' })
    return actions
  }

  if (status === ArticleStatus.SCHEDULED) {
    actions.push({ key: 'publish', label: 'Publier maintenant', variant: 'primary' })
    actions.push({ key: 'unschedule', label: 'Repasser en prêt', variant: 'secondary' })
    actions.push({ key: 'archive', label: 'Archiver', variant: 'danger' })
    return actions
  }

  if (status === ArticleStatus.READY_TO_PUBLISH || status === ArticleStatus.DRAFT_READY) {
    actions.push({ key: 'publish', label: 'Publier', variant: 'primary' })
    actions.push({ key: 'schedule', label: 'Programmer', variant: 'secondary' })
  }

  if (status !== ArticleStatus.READY_TO_PUBLISH) {
    actions.push({ key: 'mark-ready', label: 'Envoyer en validation', variant: 'secondary' })
  }

  actions.push({ key: 'archive', label: 'Archiver', variant: 'danger' })
  return actions
}
