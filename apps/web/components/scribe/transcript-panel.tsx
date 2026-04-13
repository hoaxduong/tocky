"use client"

import { useEffect, useRef } from "react"
import { useExtracted } from "next-intl"
import { useScribeStore } from "@/lib/stores/use-scribe-store"
import { TranscriptSegmentItem } from "./transcript-segment"

export function TranscriptPanel() {
  const t = useExtracted()
  const segments = useScribeStore((s) => s.transcriptSegments)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [segments.length])

  return (
    <div className="flex h-full flex-col">
      <h3 className="mb-3 text-lg font-semibold">{t("Transcript")}</h3>
      <div className="flex-1 space-y-2 overflow-y-auto px-0.5">
        {segments.length === 0 && (
          <p className="text-sm text-muted-foreground">{t("Recording...")}</p>
        )}
        {segments.map((seg, i) => (
          <TranscriptSegmentItem
            key={i}
            text={seg.text}
            isMedicallyRelevant={seg.isMedicallyRelevant}
            speakerLabel={seg.speakerLabel}
            sequence={seg.sequence}
          />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
