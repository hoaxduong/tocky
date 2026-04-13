"use client"

import { useExtracted } from "next-intl"
import { Badge } from "@workspace/ui/components/badge"
import { AlertCircle } from "lucide-react"

interface TranscriptSegmentProps {
  text: string
  isMedicallyRelevant: boolean
  speakerLabel: string | null
  sequence: number
  status?: string
  errorMessage?: string | null
}

export function TranscriptSegmentItem({
  text,
  isMedicallyRelevant,
  speakerLabel,
  sequence,
  status = "classified",
  errorMessage,
}: TranscriptSegmentProps) {
  const t = useExtracted()

  const isFailed = status === "failed_transcription" || status === "failed_classification"
  const isPending = status === "transcribed"

  return (
    <div
      className={`rounded-lg border p-3 ${
        isFailed
          ? "border-red-500/30 bg-red-500/5"
          : isPending
            ? "border-muted bg-muted/20"
            : isMedicallyRelevant
              ? "border-primary/20 bg-primary/5"
              : "border-muted bg-muted/30 opacity-60"
      }`}
    >
      <div className="mb-1 flex items-center gap-2">
        <span className="text-muted-foreground text-xs">#{sequence}</span>
        {speakerLabel && (
          <Badge variant="outline" className="text-xs">
            {speakerLabel}
          </Badge>
        )}
        {isFailed ? (
          <Badge
            variant="outline"
            className="border-red-500/30 bg-red-500/10 text-red-700 text-xs dark:text-red-400"
          >
            {status === "failed_transcription"
              ? t("Failed")
              : t("Unclassified")}
          </Badge>
        ) : isPending ? (
          <Badge variant="secondary" className="text-xs">
            {t("Pending")}
          </Badge>
        ) : (
          <Badge
            variant={isMedicallyRelevant ? "default" : "secondary"}
            className="text-xs"
          >
            {isMedicallyRelevant ? t("Relevant") : t("Small Talk")}
          </Badge>
        )}
      </div>
      {status === "failed_transcription" ? (
        <div className="flex items-center gap-1.5 text-sm text-red-600 dark:text-red-400">
          <AlertCircle className="h-3.5 w-3.5 shrink-0" />
          <span>{t("Transcription failed")}</span>
        </div>
      ) : (
        <p className="text-sm">{text}</p>
      )}
      {errorMessage && (
        <p className="text-muted-foreground mt-1 text-xs">{errorMessage}</p>
      )}
    </div>
  )
}
