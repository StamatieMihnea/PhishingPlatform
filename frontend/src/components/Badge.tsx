interface BadgeProps {
  children: React.ReactNode
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info'
  size?: 'sm' | 'md'
}

export default function Badge({ children, variant = 'default', size = 'md' }: BadgeProps) {
  const variants = {
    default: 'bg-secondary-100 text-secondary-700',
    success: 'bg-green-100 text-green-700',
    warning: 'bg-yellow-100 text-yellow-700',
    danger: 'bg-red-100 text-red-700',
    info: 'bg-blue-100 text-blue-700',
  }

  const sizes = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
  }

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full ${variants[variant]} ${sizes[size]}`}
    >
      {children}
    </span>
  )
}

export function StatusBadge({ status }: { status: string }) {
  const statusConfig: Record<string, { variant: BadgeProps['variant']; label: string }> = {
    DRAFT: { variant: 'default', label: 'Draft' },
    SCHEDULED: { variant: 'info', label: 'Scheduled' },
    RUNNING: { variant: 'warning', label: 'Running' },
    COMPLETED: { variant: 'success', label: 'Completed' },
    PENDING: { variant: 'default', label: 'Pending' },
    QUEUED: { variant: 'info', label: 'Queued' },
    SENT: { variant: 'success', label: 'Sent' },
    FAILED: { variant: 'danger', label: 'Failed' },
    EASY: { variant: 'success', label: 'Easy' },
    MEDIUM: { variant: 'warning', label: 'Medium' },
    HARD: { variant: 'danger', label: 'Hard' },
    LOW: { variant: 'success', label: 'Low' },
    HIGH: { variant: 'danger', label: 'High' },
  }

  const config = statusConfig[status] || { variant: 'default', label: status }

  return <Badge variant={config.variant}>{config.label}</Badge>
}
