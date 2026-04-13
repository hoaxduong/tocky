"use client"

import { useExtracted } from "next-intl"
import { Badge } from "@workspace/ui/components/badge"
import { StatusBadge } from "@/components/status-badge"

interface ConsultationHeaderProps {
  title: string
  language: string
  status: string
  elapsedMs: number
}

function formatElapsed(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`
}

export function ConsultationHeader({
  title,
  language,
  status,
  elapsedMs,
}: ConsultationHeaderProps) {
  const t = useExtracted()

  return (
    <div className="flex items-center justify-between border-b pb-4">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold">{title || t("New Consultation")}</h1>
        <Badge variant="outline">{language}</Badge>
        <StatusBadge status={status} />
      </div>
      <div className="font-mono text-lg text-muted-foreground tabular-nums">
        {formatElapsed(elapsedMs)}
      </div>
    </div>
  )
}
