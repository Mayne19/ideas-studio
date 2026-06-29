import Badge from './Badge'
import type { ArticleStatus } from '@/types'
import { STATUS_LABELS as ARTICLE_STATUS_LABELS } from '@/utils/articleActions'
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

const STATUS_LABELS = ARTICLE_STATUS_LABELS

const STATUS_VARIANTS: Record<ArticleStatus, BadgeVariant> = {
  draft:                'gray',
  idea_proposed:        'blue',
  idea_priority:        'blue',
  idea_rejected:        'red',
  outline_ready:        'blue',
  writing_requested:    'orange',
  writing_in_progress:  'orange',
  draft_ready:          'blue',
  review_needed:        'orange',
  correction_needed:    'red',
  scheduled:            'blue',
  published:            'green',
  ready_to_publish:     'green',
  update_recommended:   'orange',
  unpublished:          'gray',
  archived:             'gray',
  failed:               'red',
  improvement_proposed:   'orange',
  improvement_in_progress: 'orange',
  improvement_ready:      'blue',
}

const STATUS_ICONS: Partial<Record<ArticleStatus, typeof CheckCircle>> = {
  draft: FileText,
  idea_proposed: FileText,
  idea_priority: FileText,
  idea_rejected: XCircle,
  outline_ready: FileText,
  writing_requested: Clock,
  writing_in_progress: Loader2,
  draft_ready: FileText,
  review_needed: AlertCircle,
  correction_needed: AlertCircle,
  scheduled: Clock,
  published: CheckCircle,
  ready_to_publish: CheckCircle,
  update_recommended: AlertCircle,
  unpublished: FileText,
  archived: Archive,
  failed: XCircle,
  improvement_proposed: FileText,
  improvement_in_progress: Loader2,
  improvement_ready: CheckCircle,
}

type StatusBadgeProps = {
  status: ArticleStatus | string
  className?: string
}

export default function StatusBadge({ status, className }: StatusBadgeProps) {
  const label = STATUS_LABELS[status as ArticleStatus] ?? status
  const variant = STATUS_VARIANTS[status as ArticleStatus] ?? 'default'
  const Icon = STATUS_ICONS[status as ArticleStatus] ?? FileText

  return (
    <Badge variant={variant} className={className}>
      <Icon aria-hidden="true" data-icon="inline-start" size={12} className="shrink-0" />
      {label}
    </Badge>
  )
}
