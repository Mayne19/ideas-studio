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
  purple: 'border-purple-200 bg-purple-50 text-purple-700',
  blue:   'border-blue-200 bg-blue-50 text-blue-700',
  green:  'border-green-200 bg-green-50 text-green-700',
  orange: 'border-amber-200 bg-amber-50 text-amber-700',
  pink:   'border-pink-200 bg-pink-50 text-pink-700',
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
