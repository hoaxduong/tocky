"use client"

import { useExtracted } from "next-intl"
import { Mic, Pause, Play, Square } from "lucide-react"
import { Button } from "@workspace/ui/components/button"

interface RecordingControlsProps {
  isRecording: boolean
  isPaused?: boolean
  status: string
  onStart: () => void
  onStop: () => void
  onPause: () => void
  onResume: () => void
}

export function RecordingControls({
  isRecording,
  isPaused,
  status,
  onStart,
  onStop,
  onPause,
  onResume,
}: RecordingControlsProps) {
  const t = useExtracted()

  if (!isRecording && status !== "recording") {
    return (
      <Button
        onClick={onStart}
        size="lg"
        className="gap-2"
        disabled={status === "processing" || status === "completed"}
      >
        <Mic className="h-5 w-5" />
        {t("Start Recording")}
      </Button>
    )
  }

  return (
    <div className="flex items-center gap-2">
      {isPaused ? (
        <Button
          onClick={onResume}
          variant="outline"
          size="lg"
          className="gap-2"
        >
          <Play className="h-5 w-5" />
          {t("Resume")}
        </Button>
      ) : (
        <Button onClick={onPause} variant="outline" size="lg" className="gap-2">
          <Pause className="h-5 w-5" />
          {t("Pause")}
        </Button>
      )}

      <Button
        onClick={onStop}
        variant="destructive"
        size="lg"
        className="gap-2"
      >
        <Square className="h-5 w-5" />
        {t("Stop Recording")}
      </Button>
    </div>
  )
}
