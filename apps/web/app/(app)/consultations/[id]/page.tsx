"use client"

import { use, useCallback, useEffect, useRef } from "react"
import { useExtracted } from "next-intl"
import { CheckCircle2, ChevronRight } from "lucide-react"
import { useScribeStore } from "@/lib/stores/use-scribe-store"
import {
  useConsultation,
  useConsultationAudio,
} from "@/hooks/use-consultation"
import { useScribeWebSocket } from "@/hooks/use-scribe-websocket"
import { useAudioRecorder } from "@/hooks/use-audio-recorder"
import { ConsultationContextBar } from "@/components/consultation-context-bar"
import { RecordingControls } from "@/components/scribe/recording-controls"
import { AudioVisualizer } from "@/components/scribe/audio-visualizer"
import { TranscriptPanel } from "@/components/scribe/transcript-panel"
import { SOAPEditor } from "@/components/scribe/soap-editor"
import { ScribeLayout } from "@/components/scribe/scribe-layout"
import { UploadProcessingView } from "@/components/upload-processing-view"
import { AudioPlayer } from "@/components/audio-player"
import { Button } from "@workspace/ui/components/button"
import { ScribePageSkeleton } from "@/components/skeletons"
import Link from "next/link"

export default function ScribePage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = use(params)
  const { data: consultation, isLoading } = useConsultation(id)

  if (isLoading) {
    return <ScribePageSkeleton />
  }

  // Show upload processing view for upload-mode consultations
  if (consultation?.mode === "upload") {
    return <UploadProcessingView consultationId={id} />
  }

  return <LiveScribeView id={id} />
}

function LiveScribeView({ id }: { id: string }) {
  const t = useExtracted()
  const { data: consultation } = useConsultation(id)
  const { status, elapsedMs, setConsultationId, setStatus, reset } =
    useScribeStore()

  const { data: audio } = useConsultationAudio(
    id,
    !!consultation?.has_audio && status === "completed"
  )

  const { connect, disconnect, sendAudioChunk, sendControl } =
    useScribeWebSocket({ consultationId: id })

  const onAudioChunk = useCallback(
    (data: string, sequence: number, timestampMs: number) => {
      sendAudioChunk(data, sequence, timestampMs)
    },
    [sendAudioChunk]
  )

  const {
    isRecording,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    audioLevel,
    error: audioError,
  } = useAudioRecorder(onAudioChunk)

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const { setElapsedMs } = useScribeStore()

  useEffect(() => {
    setConsultationId(id)
    return () => {
      reset()
      disconnect()
    }
  }, [id, setConsultationId, reset, disconnect])

  useEffect(() => {
    if (isRecording) {
      const startTime = Date.now() - elapsedMs
      timerRef.current = setInterval(() => {
        setElapsedMs(Date.now() - startTime)
      }, 1000)
    } else if (timerRef.current) {
      clearInterval(timerRef.current)
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [isRecording, elapsedMs, setElapsedMs])

  async function handleStart() {
    connect()
    // Wait a tick for connection
    setTimeout(async () => {
      sendControl("start")
      await startRecording()
      setStatus("recording")
    }, 500)
  }

  function handleStop() {
    stopRecording()
    sendControl("stop")
  }

  function handlePause() {
    pauseRecording()
    sendControl("pause")
  }

  function handleResume() {
    resumeRecording()
    sendControl("resume")
  }

  const segments = useScribeStore((s) => s.transcriptSegments)
  const relevantCount = segments.filter((s) => s.isMedicallyRelevant).length

  return (
    <div className="flex h-[calc(100dvh-theme(spacing.14)-theme(spacing.12))] flex-col gap-6">
      {consultation && (
        <ConsultationContextBar
          consultation={consultation}
          statusOverride={status}
          elapsedMs={elapsedMs}
          backHref="/consultations"
          breadcrumbs={[
            { label: t("Consultations"), href: "/consultations" },
            { label: consultation.title || t("New Consultation") },
          ]}
        />
      )}

      {audioError && <p className="text-sm text-destructive">{audioError}</p>}

      <div className="flex items-center gap-4">
        <RecordingControls
          isRecording={isRecording}
          status={status}
          onStart={handleStart}
          onStop={handleStop}
          onPause={handlePause}
          onResume={handleResume}
        />
        <AudioVisualizer level={audioLevel} isRecording={isRecording} />
      </div>

      {audio?.url && (
        <AudioPlayer src={audio.url} durationMs={audio.duration_ms} />
      )}

      {status === "completed" && (
        <div className="flex items-center justify-between rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-4">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="h-5 w-5 text-emerald-600" />
            <div>
              <p className="font-medium text-emerald-700 dark:text-emerald-400">
                {t("Recording Complete")}
              </p>
              <p className="text-sm text-muted-foreground">
                {segments.length > 0 &&
                  `${segments.length} ${t("segments")} · ${relevantCount} ${t("relevant")}`}
              </p>
            </div>
          </div>
          <Button asChild className="gap-1.5">
            <Link href={`/consultations/${id}/soap`}>
              {t("Review SOAP Note")}
              <ChevronRight className="h-4 w-4" />
            </Link>
          </Button>
        </div>
      )}

      <ScribeLayout>
        <ScribeLayout.Left>
          <TranscriptPanel />
        </ScribeLayout.Left>
        <ScribeLayout.Right>
          <SOAPEditor />
        </ScribeLayout.Right>
      </ScribeLayout>
    </div>
  )
}
