import { HugeiconsIcon } from '@hugeicons/react'
import type { IconSvgElement } from '@hugeicons/react'

type HugeIconProps = {
  icon: IconSvgElement
  size?: number | string
  strokeWidth?: number
  className?: string
}

export default function HugeIcon({ icon, size = 16, strokeWidth = 1.8, className }: HugeIconProps) {
  return (
    <HugeiconsIcon
      icon={icon}
      size={size}
      strokeWidth={strokeWidth}
      color="currentColor"
      className={className}
    />
  )
}
