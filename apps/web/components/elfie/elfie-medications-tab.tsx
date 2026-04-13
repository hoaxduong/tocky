"use client"

import type { ElfieMedication } from "@/hooks/use-elfie"
import { useExtracted } from "next-intl"
import { Progress } from "@workspace/ui/components/progress"
import { Badge } from "@workspace/ui/components/badge"
import { cn } from "@workspace/ui/lib/utils"

interface ElfieMedicationsTabProps {
  medications: ElfieMedication[]
}

export function ElfieMedicationsTab({ medications }: ElfieMedicationsTabProps) {
  const t = useExtracted()

  if (medications.length === 0) {
    return (
      <p className="text-sm text-muted-foreground italic">
        {t("No medications tracked")}
      </p>
    )
  }

  return (
    <div className="space-y-3">
      {medications.map((med) => (
        <div key={med.name} className="space-y-1.5 rounded-md border p-3">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-sm font-medium">{med.name}</span>
              <span className="text-sm text-muted-foreground ml-1.5">
                {med.dose}
              </span>
            </div>
            <Badge
              variant="outline"
              className={cn(
                "text-xs tabular-nums",
                med.adherence_pct >= 80
                  ? "border-emerald-500 text-emerald-700 dark:text-emerald-400"
                  : med.adherence_pct >= 60
                    ? "border-amber-500 text-amber-700 dark:text-amber-400"
                    : "border-red-500 text-red-700 dark:text-red-400"
              )}
            >
              {med.adherence_pct}%
            </Badge>
          </div>
          <div className="text-xs text-muted-foreground">{med.frequency}</div>
          <Progress
            value={med.adherence_pct}
            className={cn(
              "h-1.5",
              med.adherence_pct >= 80
                ? "[&>[data-slot=progress-indicator]]:bg-emerald-500"
                : med.adherence_pct >= 60
                  ? "[&>[data-slot=progress-indicator]]:bg-amber-500"
                  : "[&>[data-slot=progress-indicator]]:bg-red-500"
            )}
          />
          {med.missed_last_7d > 0 && (
            <div
              className={cn(
                "text-xs",
                med.missed_last_7d > 2
                  ? "text-red-600 dark:text-red-400"
                  : "text-muted-foreground"
              )}
            >
              {t("Missed")} {med.missed_last_7d}x {t("in last 7 days")}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
