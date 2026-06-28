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
  purple: 'bg-brand-soft text-accent border border-accent/20',
  blue:   'bg-brand-soft text-accent border border-accent/20',
  green:  'bg-success/10 text-success border border-success/20',
  orange: 'bg-warning/10 text-warning border border-warning/20',
  pink:   'bg-danger/10 text-danger border border-danger/20',
  gray:   'bg-surface-soft text-secondary border border-border',
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
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${variantClasses[color]} ${className ?? ''}`}
    >
      {label}
    </span>
  )
}
