"use client"

import { useExtracted } from "next-intl"
import { Badge } from "@workspace/ui/components/badge"
import { cn } from "@workspace/ui/lib/utils"
import { AlertCircle } from "lucide-react"

const EMOTION_CONFIG: Record<string, { emoji: string; className: string }> = {
  // DashScope returns these labels from qwen3-asr-flash-realtime
  happy: { emoji: "\u{1F60A}", className: "text-yellow-600 dark:text-yellow-400" },
  sad: { emoji: "\u{1F622}", className: "text-blue-600 dark:text-blue-400" },
  angry: { emoji: "\u{1F621}", className: "text-red-600 dark:text-red-400" },
  fearful: { emoji: "\u{1F628}", className: "text-purple-600 dark:text-purple-400" },
  surprised: { emoji: "\u{1F632}", className: "text-orange-600 dark:text-orange-400" },
  disgusted: { emoji: "\u{1F616}", className: "text-green-600 dark:text-green-400" },
}

interface TranscriptSegmentProps {
  text: string
  isMedicallyRelevant: boolean
  speakerLabel: string | null
  sequence: number
  status?: string
  errorMessage?: string | null
  emotion?: string | null
  isActive?: boolean
  onClick?: () => void
}

export function TranscriptSegmentItem({
  text,
  isMedicallyRelevant,
  speakerLabel,
  sequence,
  status = "classified",
  errorMessage,
  emotion,
  isActive,
  onClick,
}: TranscriptSegmentProps) {
  const t = useExtracted()

  const isFailed = status === "failed_transcription" || status === "failed_classification"
  const isPending = status === "transcribed"
  const emotionInfo = emotion && emotion !== "neutral" ? EMOTION_CONFIG[emotion] : null

  return (
    <div
      id={`segment-${sequence}`}
      className={cn(
        "rounded-lg border p-3 transition-colors",
        isActive && "ring-2 ring-primary border-primary/30 bg-primary/10",
        !isActive && isFailed && "border-red-500/30 bg-red-500/5",
        !isActive && isPending && "border-muted bg-muted/20",
        !isActive && isMedicallyRelevant && "border-primary/20 bg-primary/5",
        !isActive && !isMedicallyRelevant && !isFailed && !isPending && "border-muted bg-muted/30 opacity-60",
        onClick && "cursor-pointer hover:bg-accent/50",
      )}
      onClick={onClick}
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
        {emotionInfo && (
          <span
            className={cn("text-xs", emotionInfo.className)}
            title={emotion ?? undefined}
          >
            {emotionInfo.emoji}
          </span>
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
