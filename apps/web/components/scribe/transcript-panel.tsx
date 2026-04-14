"use client"

import { useEffect, useRef } from "react"
import { useExtracted } from "next-intl"
import { useScribeStore } from "@/lib/stores/use-scribe-store"
import { TranscriptSegmentItem } from "./transcript-segment"

export function TranscriptPanel() {
  const t = useExtracted()
  const segments = useScribeStore((s) => s.transcriptSegments)
  const status = useScribeStore((s) => s.status)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [segments.length])

  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 flex min-h-9 items-center">
        <h3 className="text-lg font-semibold">{t("Transcript")}</h3>
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto p-1">
        {segments.length === 0 && status === "recording" && (
          <p className="text-sm text-muted-foreground">
            {t("Listening for speech...")}
          </p>
        )}
        {segments.map((seg, i) => (
          <TranscriptSegmentItem
            key={i}
            text={seg.text}
            isMedicallyRelevant={seg.isMedicallyRelevant}
            speakerLabel={seg.speakerLabel}
            sequence={seg.sequence}
            emotion={seg.emotion}
          />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
