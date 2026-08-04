import Badge from './Badge'
import { ArticleStatus, ARTICLE_STATUS_META, type ArticleStatusCode } from '@/lib/status'
import {
  AlertCircle,
  Archive,
  CheckCircle,
  Clock,
  FileText,
  Loader2,
  XCircle,
} from '@/components/ui/hugeIcons'

type BadgeVariant = 'default' | 'blue' | 'green' | 'orange' | 'red' | 'gray'

const STATUS_VARIANTS: Record<ArticleStatusCode, BadgeVariant> = {
  [ArticleStatus.DRAFT]: 'gray',
  [ArticleStatus.IDEA_PROPOSED]: 'blue',
  [ArticleStatus.IDEA_PRIORITY]: 'blue',
  [ArticleStatus.IDEA_REJECTED]: 'red',
  [ArticleStatus.OUTLINE_READY]: 'blue',
  [ArticleStatus.WRITING_REQUESTED]: 'orange',
  [ArticleStatus.WRITING_IN_PROGRESS]: 'orange',
  [ArticleStatus.DRAFT_READY]: 'blue',
  [ArticleStatus.REVIEW_NEEDED]: 'orange',
  [ArticleStatus.CORRECTION_NEEDED]: 'red',
  [ArticleStatus.READY_TO_PUBLISH]: 'green',
  [ArticleStatus.SCHEDULED]: 'blue',
  [ArticleStatus.PUBLISHED]: 'green',
  [ArticleStatus.UNPUBLISHED]: 'gray',
  [ArticleStatus.UPDATE_RECOMMENDED]: 'orange',
  [ArticleStatus.IMPROVEMENT_PROPOSED]: 'orange',
  [ArticleStatus.IMPROVEMENT_IN_PROGRESS]: 'orange',
  [ArticleStatus.IMPROVEMENT_READY]: 'blue',
  [ArticleStatus.FAILED]: 'red',
  [ArticleStatus.BLOCKED_COST_LIMIT]: 'red',
  [ArticleStatus.ARCHIVED]: 'gray',
}

const STATUS_ICONS: Partial<Record<ArticleStatusCode, typeof CheckCircle>> = {
  [ArticleStatus.DRAFT]: FileText,
  [ArticleStatus.IDEA_PROPOSED]: FileText,
  [ArticleStatus.IDEA_PRIORITY]: FileText,
  [ArticleStatus.IDEA_REJECTED]: XCircle,
  [ArticleStatus.OUTLINE_READY]: FileText,
  [ArticleStatus.WRITING_REQUESTED]: Clock,
  [ArticleStatus.WRITING_IN_PROGRESS]: Loader2,
  [ArticleStatus.DRAFT_READY]: FileText,
  [ArticleStatus.REVIEW_NEEDED]: AlertCircle,
  [ArticleStatus.CORRECTION_NEEDED]: AlertCircle,
  [ArticleStatus.READY_TO_PUBLISH]: CheckCircle,
  [ArticleStatus.SCHEDULED]: Clock,
  [ArticleStatus.PUBLISHED]: CheckCircle,
  [ArticleStatus.UNPUBLISHED]: FileText,
  [ArticleStatus.UPDATE_RECOMMENDED]: AlertCircle,
  [ArticleStatus.IMPROVEMENT_PROPOSED]: FileText,
  [ArticleStatus.IMPROVEMENT_IN_PROGRESS]: Loader2,
  [ArticleStatus.IMPROVEMENT_READY]: CheckCircle,
  [ArticleStatus.FAILED]: XCircle,
  [ArticleStatus.ARCHIVED]: Archive,
}

type StatusBadgeProps = {
  status: ArticleStatusCode | number | null | undefined
  className?: string
}

export default function StatusBadge({ status, className }: StatusBadgeProps) {
  const meta = status != null ? ARTICLE_STATUS_META[status as ArticleStatusCode] : undefined
  const label = meta?.label ?? String(status ?? '—')
  const visibleLabel = meta?.compactLabel ?? label
  const variant = (status != null ? STATUS_VARIANTS[status as ArticleStatusCode] : undefined) ?? 'default'
  const Icon = (status != null ? STATUS_ICONS[status as ArticleStatusCode] : undefined) ?? FileText

  return (
    <Badge variant={variant} className={className} title={label}>
      <Icon aria-hidden="true" data-icon="inline-start" size={12} className="shrink-0" />
      <span className="max-w-[92px] truncate">{visibleLabel}</span>
    </Badge>
  )
}
