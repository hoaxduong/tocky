"use client"

import { use, useCallback, useEffect, useRef } from "react"
import { useExtracted } from "next-intl"
import {
  CheckCircle2,
  ChevronRight,
  FileText,
  Loader2,
  Mic,
  Stethoscope,
} from "lucide-react"
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

  // Completed/failed live consultations reuse the same results view
  if (
    consultation?.status === "completed" ||
    consultation?.status === "completed_with_errors" ||
    consultation?.status === "failed"
  ) {
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

  const { isConnected, connect, disconnect, sendAudioChunk, sendControl } =
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
    // If WebSocket is already dead, sendControl silently fails.
    // Set processing so the user sees feedback, and the server's
    // disconnect handler will persist whatever data it has.
    if (!isConnected) {
      setStatus("completed")
    }
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
  const consultationTitle = useScribeStore((s) => s.consultationTitle)
  const patientIdentifier = useScribeStore((s) => s.patientIdentifier)
  const detectedLanguage = useScribeStore((s) => s.language)
  const relevantCount = segments.filter((s) => s.isMedicallyRelevant).length

  const isIdle = status === "idle" || status === "ready"

  return (
    <div className="flex h-[calc(100dvh-theme(spacing.14)-theme(spacing.12))] flex-col gap-6">
      {consultation && (
        <ConsultationContextBar
          consultation={{
            ...consultation,
            title: consultationTitle || consultation.title,
            patient_identifier:
              patientIdentifier ?? consultation.patient_identifier,
            language: detectedLanguage || consultation.language,
          }}
          statusOverride={status}
          elapsedMs={elapsedMs}
          backHref="/consultations"
          breadcrumbs={[
            { label: t("Consultations"), href: "/consultations" },
            {
              label:
                consultationTitle ||
                consultation.title ||
                t("New Consultation"),
            },
          ]}
        />
      )}

      {audioError && <p className="text-sm text-destructive">{audioError}</p>}

      {isIdle ? (
        <div className="flex flex-1 items-center justify-center">
          <div className="flex max-w-md flex-col items-center gap-6 text-center">
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-primary/10">
              <Mic className="h-10 w-10 text-primary" />
            </div>
            <div className="space-y-2">
              <h2 className="text-xl font-semibold">
                {t("Ready to Record")}
              </h2>
              <p className="text-sm text-muted-foreground">
                {t(
                  "Start recording your consultation. The AI will transcribe speech in real-time, filter medically relevant information, and generate a SOAP note."
                )}
              </p>
            </div>

            <Button onClick={handleStart} size="lg" className="gap-2 px-8">
              <Mic className="h-5 w-5" />
              {t("Start Recording")}
            </Button>

            <div className="grid w-full grid-cols-2 gap-3 pt-2">
              <div className="flex items-start gap-2.5 rounded-lg border p-3 text-left">
                <Stethoscope className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                <div>
                  <p className="text-xs font-medium">
                    {t("Smart Filtering")}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {t("Small talk is filtered out automatically")}
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-2.5 rounded-lg border p-3 text-left">
                <FileText className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                <div>
                  <p className="text-xs font-medium">{t("SOAP Note")}</p>
                  <p className="text-xs text-muted-foreground">
                    {t("Generated in real-time as you speak")}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <>
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

          {status === "processing" && (
            <div className="flex items-center gap-3 rounded-lg border border-blue-500/30 bg-blue-500/5 p-4">
              <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
              <div>
                <p className="font-medium text-blue-700 dark:text-blue-400">
                  {t("Processing Recording...")}
                </p>
                <p className="text-sm text-muted-foreground">
                  {t(
                    "Finalizing transcription and generating SOAP note. This may take a moment."
                  )}
                </p>
              </div>
            </div>
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
        </>
      )}
    </div>
  )
}
