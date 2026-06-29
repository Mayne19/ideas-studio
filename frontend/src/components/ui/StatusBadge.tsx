import Badge from './Badge'
import type { ArticleStatus } from '@/types'
import { STATUS_LABELS as ARTICLE_STATUS_LABELS } from '@/utils/articleActions'

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

type StatusBadgeProps = {
  status: ArticleStatus | string
  className?: string
}

export default function StatusBadge({ status, className }: StatusBadgeProps) {
  const label = STATUS_LABELS[status as ArticleStatus] ?? status
  const variant = STATUS_VARIANTS[status as ArticleStatus] ?? 'default'
  return <Badge variant={variant} className={className}>{label}</Badge>
}
