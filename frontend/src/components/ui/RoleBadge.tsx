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
  purple: 'bg-[#f3eeff] text-[#6f3cc2]',
  blue:   'bg-accent/10 text-accent',
  green:  'bg-success/10 text-[#1a7a3a]',
  orange: 'bg-warning/10 text-[#c07000]',
  pink:   'bg-[#fff0f6] text-[#b83270]',
  gray:   'bg-[#f0f0f2] text-secondary',
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
