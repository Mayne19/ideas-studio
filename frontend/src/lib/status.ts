// Miroir frontend de ref.*_status_reasons (schéma v3) — voir
// db/migration-v3/01-schema.sql et app/models/reference.py côté backend.
// Le backend renvoie désormais `status` sous forme d'entier (status_reason_id),
// plus une chaîne. Ce fichier centralise le mapping entier -> code/label/couleur
// pour tout le frontend, remplaçant les chaînes littérales ('draft', 'published', ...).

export const ArticleStatus = {
  DRAFT: 10,
  IDEA_PROPOSED: 20,
  IDEA_PRIORITY: 30,
  OUTLINE_READY: 40,
  WRITING_REQUESTED: 50,
  WRITING_IN_PROGRESS: 60,
  DRAFT_READY: 70,
  REVIEW_NEEDED: 80,
  CORRECTION_NEEDED: 90,
  READY_TO_PUBLISH: 100,
  SCHEDULED: 110,
  PUBLISHED: 120,
  UNPUBLISHED: 130,
  UPDATE_RECOMMENDED: 140,
  IMPROVEMENT_PROPOSED: 150,
  IMPROVEMENT_IN_PROGRESS: 160,
  IMPROVEMENT_READY: 170,
  FAILED: 180,
  BLOCKED_COST_LIMIT: 190,
  IDEA_REJECTED: 200,
  ARCHIVED: 210,
} as const

export type ArticleStatusCode = (typeof ArticleStatus)[keyof typeof ArticleStatus]

type ArticleStatusMeta = {
  code: string
  label: string
  color: string
  compactLabel: string
}

export const ARTICLE_STATUS_META: Record<ArticleStatusCode, ArticleStatusMeta> = {
  [ArticleStatus.DRAFT]: { code: 'draft', label: 'Brouillon', color: '#8892a0', compactLabel: 'Brouillon' },
  [ArticleStatus.IDEA_PROPOSED]: { code: 'idea_proposed', label: 'Idée proposée', color: '#8892a0', compactLabel: 'Proposée' },
  [ArticleStatus.IDEA_PRIORITY]: { code: 'idea_priority', label: 'Prioritaire', color: '#7c9dfd', compactLabel: 'Prioritaire' },
  [ArticleStatus.OUTLINE_READY]: { code: 'outline_ready', label: 'Plan prêt', color: '#7c9dfd', compactLabel: 'Plan prêt' },
  [ArticleStatus.WRITING_REQUESTED]: { code: 'writing_requested', label: "En file d'attente rédaction", color: '#e0a03a', compactLabel: 'En attente' },
  [ArticleStatus.WRITING_IN_PROGRESS]: { code: 'writing_in_progress', label: 'En rédaction', color: '#e0a03a', compactLabel: 'En cours' },
  [ArticleStatus.DRAFT_READY]: { code: 'draft_ready', label: 'Brouillon prêt', color: '#e0a03a', compactLabel: 'Prêt' },
  [ArticleStatus.REVIEW_NEEDED]: { code: 'review_needed', label: 'À relire', color: '#e0a03a', compactLabel: 'À relire' },
  [ArticleStatus.CORRECTION_NEEDED]: { code: 'correction_needed', label: 'À corriger', color: '#c0392b', compactLabel: 'Correction' },
  [ArticleStatus.READY_TO_PUBLISH]: { code: 'ready_to_publish', label: 'Prêt à publier', color: '#1d9e75', compactLabel: 'Validable' },
  [ArticleStatus.SCHEDULED]: { code: 'scheduled', label: 'Programmé', color: '#1d9e75', compactLabel: 'Programmé' },
  [ArticleStatus.PUBLISHED]: { code: 'published', label: 'Publié', color: '#0f6e56', compactLabel: 'Publié' },
  [ArticleStatus.UNPUBLISHED]: { code: 'unpublished', label: 'Dépublié', color: '#6b6b6b', compactLabel: 'Dépublié' },
  [ArticleStatus.UPDATE_RECOMMENDED]: { code: 'update_recommended', label: 'Mise à jour recommandée', color: '#e0a03a', compactLabel: 'MAJ' },
  [ArticleStatus.IMPROVEMENT_PROPOSED]: { code: 'improvement_proposed', label: 'Amélioration proposée', color: '#7c9dfd', compactLabel: 'Amél. proposée' },
  [ArticleStatus.IMPROVEMENT_IN_PROGRESS]: { code: 'improvement_in_progress', label: 'Amélioration en cours', color: '#e0a03a', compactLabel: 'Amél. en cours' },
  [ArticleStatus.IMPROVEMENT_READY]: { code: 'improvement_ready', label: 'Amélioration prête', color: '#1d9e75', compactLabel: 'Amél. prête' },
  [ArticleStatus.FAILED]: { code: 'failed', label: 'Échec', color: '#c0392b', compactLabel: 'Échec' },
  [ArticleStatus.BLOCKED_COST_LIMIT]: { code: 'blocked_cost_limit', label: 'Bloqué (coût)', color: '#c0392b', compactLabel: 'Bloqué' },
  [ArticleStatus.IDEA_REJECTED]: { code: 'idea_rejected', label: 'Rejetée', color: '#c0392b', compactLabel: 'Rejetée' },
  [ArticleStatus.ARCHIVED]: { code: 'archived', label: 'Archivé', color: '#6b6b6b', compactLabel: 'Archivé' },
}

export function articleStatusLabel(status: number | null | undefined): string {
  if (status == null) return '—'
  return ARTICLE_STATUS_META[status as ArticleStatusCode]?.label ?? String(status)
}

export function articleStatusCompactLabel(status: number | null | undefined): string {
  if (status == null) return '—'
  return ARTICLE_STATUS_META[status as ArticleStatusCode]?.compactLabel ?? String(status)
}

export function articleStatusColor(status: number | null | undefined): string {
  if (status == null) return '#8892a0'
  return ARTICLE_STATUS_META[status as ArticleStatusCode]?.color ?? '#8892a0'
}

// Motifs qui font d'un article une "idée" (page /projects/:id/ideas) — miroir
// de IDEA_ARTICLE_STATUSES dans app/models/reference.py.
export const IDEA_ARTICLE_STATUSES: ArticleStatusCode[] = [
  ArticleStatus.DRAFT,
  ArticleStatus.IDEA_PROPOSED,
  ArticleStatus.IDEA_PRIORITY,
  ArticleStatus.IDEA_REJECTED,
]

export const WRITING_ARTICLE_STATUSES: ArticleStatusCode[] = [
  ArticleStatus.OUTLINE_READY,
  ArticleStatus.WRITING_REQUESTED,
  ArticleStatus.WRITING_IN_PROGRESS,
]

// ── Project status (ref.project_status_reasons) ────────────────────────────

export const ProjectStatus = {
  NOT_CONNECTED: 10,
  CONNECTED: 20,
  ARCHIVED: 30,
} as const

export type ProjectStatusCode = (typeof ProjectStatus)[keyof typeof ProjectStatus]

export const PROJECT_STATUS_LABELS: Record<ProjectStatusCode, string> = {
  [ProjectStatus.NOT_CONNECTED]: 'Non connecté',
  [ProjectStatus.CONNECTED]: 'Connecté',
  [ProjectStatus.ARCHIVED]: 'Archivé',
}

export function projectStatusLabel(status: number | null | undefined): string {
  if (status == null) return '—'
  return PROJECT_STATUS_LABELS[status as ProjectStatusCode] ?? String(status)
}

// ── Membership status (ref.membership_status_reasons) ──────────────────────

export const MembershipStatus = {
  INVITED: 10,
  ACTIVE: 20,
  SUSPENDED: 30,
  REMOVED: 40,
} as const

// ── Optimization recommendation status ─────────────────────────────────────
// analytics.optimization_recommendations réutilise ref.run_status_reasons
// (queued/running/succeeded/cancelled) sous ces noms côté API :
// pending/accepted/applied/rejected (voir app/services/optimization_engine.py).
export type RecommendationStatusCode = 'pending' | 'accepted' | 'rejected' | 'applied'

export const RECOMMENDATION_STATUS_LABELS: Record<RecommendationStatusCode, string> = {
  pending: 'En attente',
  accepted: 'Acceptée',
  rejected: 'Rejetée',
  applied: 'Appliquée',
}
