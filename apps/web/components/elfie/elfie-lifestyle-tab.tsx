"use client"

import type { ElfieLifestyleStats } from "@/hooks/use-elfie"
import { useExtracted } from "next-intl"
import { Footprints, Moon, Flame } from "lucide-react"
import { cn } from "@workspace/ui/lib/utils"

interface ElfieLifestyleTabProps {
  lifestyle: ElfieLifestyleStats
}

function ratingClass(rating: "good" | "warning" | "poor") {
  if (rating === "good") return "text-emerald-600 dark:text-emerald-400"
  if (rating === "warning") return "text-amber-600 dark:text-amber-400"
  return "text-red-600 dark:text-red-400"
}

export function ElfieLifestyleTab({ lifestyle }: ElfieLifestyleTabProps) {
  const t = useExtracted()

  const stepsRating =
    lifestyle.avg_daily_steps >= 7000
      ? "good"
      : lifestyle.avg_daily_steps >= 4000
        ? "warning"
        : "poor"
  const sleepRating =
    lifestyle.avg_sleep_hours >= 7
      ? "good"
      : lifestyle.avg_sleep_hours >= 6
        ? "warning"
        : "poor"
  const caloriesRating =
    lifestyle.avg_calories <= 2000
      ? "good"
      : lifestyle.avg_calories <= 2500
        ? "warning"
        : "poor"

  return (
    <div className="grid grid-cols-3 gap-3">
      <div className="space-y-1 rounded-md border p-3 text-center">
        <Footprints className="mx-auto h-4 w-4 text-muted-foreground" />
        <div
          className={cn("text-lg font-bold tabular-nums", ratingClass(stepsRating))}
        >
          {lifestyle.avg_daily_steps.toLocaleString()}
        </div>
        <div className="text-xs text-muted-foreground">
          {t("steps/day")}
        </div>
      </div>
      <div className="space-y-1 rounded-md border p-3 text-center">
        <Moon className="mx-auto h-4 w-4 text-muted-foreground" />
        <div
          className={cn("text-lg font-bold tabular-nums", ratingClass(sleepRating))}
        >
          {lifestyle.avg_sleep_hours}h
        </div>
        <div className="text-xs text-muted-foreground">
          {t("avg sleep")}
        </div>
      </div>
      <div className="space-y-1 rounded-md border p-3 text-center">
        <Flame className="mx-auto h-4 w-4 text-muted-foreground" />
        <div
          className={cn(
            "text-lg font-bold tabular-nums",
            ratingClass(caloriesRating)
          )}
        >
          {lifestyle.avg_calories.toLocaleString()}
        </div>
        <div className="text-xs text-muted-foreground">
          {t("cal/day")}
        </div>
      </div>
    </div>
  )
}
