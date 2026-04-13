"use client"

import { use, useCallback, useEffect, useRef } from "react"
import { useExtracted } from "next-intl"
import { useScribeStore } from "@/lib/stores/use-scribe-store"
import { useConsultation } from "@/hooks/use-consultation"
import { useScribeWebSocket } from "@/hooks/use-scribe-websocket"
import { useAudioRecorder } from "@/hooks/use-audio-recorder"
import { ConsultationHeader } from "@/components/scribe/consultation-header"
import { RecordingControls } from "@/components/scribe/recording-controls"
import { AudioVisualizer } from "@/components/scribe/audio-visualizer"
import { TranscriptPanel } from "@/components/scribe/transcript-panel"
import { SOAPEditor } from "@/components/scribe/soap-editor"
import { ScribeLayout } from "@/components/scribe/scribe-layout"
import { UploadProcessingView } from "@/components/upload-processing-view"
import { Button } from "@workspace/ui/components/button"
import Link from "next/link"

export default function ScribePage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = use(params)
  const { data: consultation } = useConsultation(id)

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

  return (
    <div className="flex h-[calc(100dvh-theme(spacing.14)-theme(spacing.12))] flex-col gap-6">
      <ConsultationHeader
        title={consultation?.title ?? ""}
        language={consultation?.language ?? "vi"}
        status={status}
        elapsedMs={elapsedMs}
      />

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

      <ScribeLayout>
        <ScribeLayout.Left>
          <TranscriptPanel />
        </ScribeLayout.Left>
        <ScribeLayout.Right>
          <SOAPEditor />
        </ScribeLayout.Right>
      </ScribeLayout>

      {status === "completed" && (
        <div className="flex justify-end">
          <Link href={`/consultations/${id}/soap`}>
            <Button>{t("SOAP Note")}</Button>
          </Link>
        </div>
      )}
    </div>
  )
}
