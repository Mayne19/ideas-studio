import type { ArticleStatus } from '@/types'

export type ArticleAction = {
  key: string
  label: string
  variant: 'primary' | 'secondary' | 'danger'
}

export const STATUS_LABELS: Record<ArticleStatus, string> = {
  draft: 'Brouillon',
  idea_proposed: 'Idée proposée',
  idea_priority: 'Prioritaire',
  idea_rejected: 'Rejetée',
  outline_ready: 'Plan prêt',
  writing_requested: 'Rédaction demandée',
  writing_in_progress: 'En rédaction',
  draft_ready: 'Brouillon prêt',
  review_needed: 'À relire',
  correction_needed: 'À corriger',
  scheduled: 'Programmé',
  published: 'Publié',
  ready_to_publish: 'Prêt à publier',
  update_recommended: 'Mise à jour recommandée',
  unpublished: 'Dépublié',
  archived: 'Archivé',
  failed: 'Échec',
  improvement_proposed: 'Amélioration proposée',
  improvement_in_progress: 'Amélioration en cours',
  improvement_ready: 'Amélioration prête',
}


export function getAvailableActions(status: ArticleStatus): ArticleAction[] {
  const actions: ArticleAction[] = []

  if (status === 'archived') {
    actions.push({ key: 'unarchive', label: 'Restaurer brouillon', variant: 'secondary' })
    actions.push({ key: 'delete', label: 'Supprimer', variant: 'danger' })
    return actions
  }

  if (status === 'published') {
    actions.push({ key: 'unpublish', label: 'Dépublier', variant: 'secondary' })
    actions.push({ key: 'archive', label: 'Archiver', variant: 'danger' })
    return actions
  }

  if (status === 'scheduled') {
    actions.push({ key: 'publish', label: 'Publier maintenant', variant: 'primary' })
    actions.push({ key: 'unschedule', label: 'Repasser en prêt', variant: 'secondary' })
    actions.push({ key: 'archive', label: 'Archiver', variant: 'danger' })
    return actions
  }

  if (status === 'ready_to_publish' || status === 'draft_ready') {
    actions.push({ key: 'publish', label: 'Publier', variant: 'primary' })
    actions.push({ key: 'schedule', label: 'Programmer', variant: 'secondary' })
  }

  if (!['ready_to_publish'].includes(status)) {
    actions.push({ key: 'mark-ready', label: 'Envoyer en validation', variant: 'secondary' })
  }

  actions.push({ key: 'archive', label: 'Archiver', variant: 'danger' })
  return actions
}
