import type { ProjectRole } from '@/types'

type RoleBadgeVariant = 'gray' | 'blue' | 'orange' | 'green' | 'purple' | 'pink'

const ROLE_LABELS: Record<ProjectRole, string> = {
  owner:  'Propriétaire',
  admin:  'Administrateur',
  editor: 'Éditeur',
  writer: 'Rédacteur',
  viewer: 'Lecteur',
}

const ROLE_COLORS: Record<ProjectRole, RoleBadgeVariant> = {
  owner:  'purple',
  admin:  'blue',
  editor: 'green',
  writer: 'orange',
  viewer: 'gray',
}

const variantClasses: Record<RoleBadgeVariant, string> = {
  purple: 'border-accent/20 bg-accent/8 text-accent',
  blue:   'border-accent/20 bg-accent/8 text-accent',
  green:  'border-success/20 bg-success/8 text-success',
  orange: 'border-warning/20 bg-warning/8 text-warning',
  pink:   'border-danger/20 bg-danger/8 text-danger',
  gray:   'border-border bg-surface-soft text-secondary',
}

type RoleBadgeProps = {
  role: ProjectRole | string
  className?: string
}

export default function RoleBadge({ role, className }: RoleBadgeProps) {
  const label = ROLE_LABELS[role as ProjectRole] ?? role
  const color = ROLE_COLORS[role as ProjectRole] ?? 'gray'
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[12px] font-medium ${variantClasses[color]} ${className ?? ''}`}
    >
      {label}
    </span>
  )
}
