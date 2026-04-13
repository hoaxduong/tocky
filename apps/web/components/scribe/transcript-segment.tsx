"use client"

import { useExtracted } from "next-intl"
import { Badge } from "@workspace/ui/components/badge"

interface TranscriptSegmentProps {
  text: string
  isMedicallyRelevant: boolean
  speakerLabel: string | null
  sequence: number
}

export function TranscriptSegmentItem({
  text,
  isMedicallyRelevant,
  speakerLabel,
  sequence,
}: TranscriptSegmentProps) {
  const t = useExtracted()

  return (
    <div
      className={`rounded-lg border p-3 ${
        isMedicallyRelevant
          ? "border-primary/20 bg-primary/5"
          : "border-muted bg-muted/30 opacity-60"
      }`}
    >
      <div className="mb-1 flex items-center gap-2">
        <span className="text-xs text-muted-foreground">#{sequence}</span>
        {speakerLabel && (
          <Badge variant="outline" className="text-xs">
            {speakerLabel}
          </Badge>
        )}
        <Badge
          variant={isMedicallyRelevant ? "default" : "secondary"}
          className="text-xs"
        >
          {isMedicallyRelevant ? t("Relevant") : t("Small Talk")}
        </Badge>
      </div>
      <p className="text-sm">{text}</p>
    </div>
  )
}
