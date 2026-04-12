"use client"

import { Badge } from "@workspace/ui/components/badge"
import { cn } from "@workspace/ui/lib/utils"

const STATUS_CONFIG: Record<
  string,
  { variant: "default" | "secondary" | "outline"; className?: string; pulse?: boolean }
> = {
  recording: {
    variant: "outline",
    className:
      "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
    pulse: true,
  },
  processing: {
    variant: "outline",
    className:
      "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400",
  },
  completed: { variant: "default" },
  idle: { variant: "outline" },
  ready: { variant: "outline" },
}

interface StatusBadgeProps {
  status: string
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? { variant: "outline" as const }

  return (
    <Badge variant={config.variant} className={cn("gap-1.5", config.className)}>
      {config.pulse && (
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
      )}
      {status}
    </Badge>
  )
}
