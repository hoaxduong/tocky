"use client"

import { useExtracted } from "next-intl"
import { useRouter } from "next/navigation"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import {
  CheckCircle2,
  Circle,
  Loader2,
  AlertCircle,
  AlertTriangle,
  RefreshCw,
  RotateCcw,
} from "lucide-react"
import { Progress } from "@workspace/ui/components/progress"
import { Button } from "@workspace/ui/components/button"
import { MarkdownPreview } from "@/components/markdown-preview"
import { Badge } from "@workspace/ui/components/badge"
import { Input } from "@workspace/ui/components/input"
import { Label } from "@workspace/ui/components/label"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@workspace/ui/components/tabs"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@workspace/ui/components/card"
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@workspace/ui/components/alert"
import {
  useConsultation,
  useConsultationAudio,
  useUpdateConsultation,
  useRetryProcessing,
} from "@/hooks/use-consultation"
import { useSOAPNote, useRegenerateSOAPNote } from "@/hooks/use-soap-note"
import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { TranscriptSegmentItem } from "@/components/scribe/transcript-segment"
import { LanguageSelector } from "@/components/scribe/language-selector"
import { ScribeLayout } from "@/components/scribe/scribe-layout"
import { ConsultationContextBar } from "@/components/consultation-context-bar"
import { useProcessingEvents } from "@/hooks/use-processing-events"
import { AudioPlayer, type AudioPlayerHandle } from "@/components/audio-player"
import { useAudioHotkeys } from "@/hooks/use-audio-hotkeys"
import { UploadProcessingSkeleton } from "@/components/skeletons"
import { toast } from "sonner"

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TranscriptSegment {
  id: string
  sequence_number: number
  text: string
  language: string
  is_medically_relevant: boolean
  status: string
  error_message: string | null
  speaker_label: string | null
  emotion: string | null
  timestamp_start_ms: number
  timestamp_end_ms: number
}

interface TranscriptResponse {
  consultation_id: string
  segments: TranscriptSegment[]
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

function useTranscripts(consultationId: string, enabled: boolean) {
  return useQuery({
    queryKey: ["transcripts", consultationId],
    queryFn: () =>
      apiFetch<TranscriptResponse>(
        `/api/v1/consultations/${consultationId}/transcripts/`,
      ),
    enabled,
  })
}

// ---------------------------------------------------------------------------
// Processing step constants
// ---------------------------------------------------------------------------

const PROCESSING_STEP_KEYS = [
  "converting",
  "transcribing",
  "detecting",
  "classifying",
  "generating_soap",
  "extracting_entities",
] as const

function getStepIndex(step: string | null): number {
  if (!step) return -1
  return PROCESSING_STEP_KEYS.indexOf(step as (typeof PROCESSING_STEP_KEYS)[number])
}

function useProcessingStepLabels() {
  const t = useExtracted()
  return {
    converting: t("Converting audio"),
    transcribing: t("Transcribing"),
    detecting: t("Detecting language & metadata"),
    classifying: t("Filtering relevance"),
    generating_soap: t("Generating SOAP note"),
    extracting_entities: t("Extracting medical entities"),
  } as const
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StepChecklist({
  currentStep,
  stepLabels,
}: {
  currentStep: string | null
  stepLabels: Record<string, string>
}) {
  const currentStepIdx = getStepIndex(currentStep)

  return (
    <div className="space-y-3">
      {PROCESSING_STEP_KEYS.map((key, idx) => {
        const isCurrent = idx === currentStepIdx
        const isDone = idx < currentStepIdx
        return (
          <div key={key} className="flex items-center gap-2.5 text-sm">
            {isDone ? (
              <CheckCircle2 className="text-primary h-4 w-4 shrink-0" />
            ) : isCurrent ? (
              <Loader2 className="text-primary h-4 w-4 shrink-0 animate-spin" />
            ) : (
              <Circle className="text-muted-foreground/30 h-4 w-4 shrink-0" />
            )}
            <span
              className={
                isDone
                  ? "text-foreground"
                  : isCurrent
                    ? "text-foreground font-medium"
                    : "text-muted-foreground/50"
              }
            >
              {stepLabels[key]}
            </span>
          </div>
        )
      })}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface UploadProcessingViewProps {
  consultationId: string
}

export function UploadProcessingView({
  consultationId,
}: UploadProcessingViewProps) {
  const t = useExtracted()
  const router = useRouter()
  const stepLabels = useProcessingStepLabels()
  const { data: consultation } = useConsultation(consultationId, {
    refetchInterval: (query) => {
      const s = query.state.data?.status
      return s === "processing" || s === "uploading" ? 3000 : false
    },
  })

  const isComplete = consultation?.status === "completed"
  const isCompletedWithErrors = consultation?.status === "completed_with_errors"
  const isFailed = consultation?.status === "failed"
  const isProcessing =
    consultation?.status === "processing" ||
    consultation?.status === "uploading"

  const { segments: streamedSegments, progress: sseProgress } =
    useProcessingEvents(consultationId, isProcessing)

  const { data: transcripts } = useTranscripts(
    consultationId,
    isComplete || isCompletedWithErrors || isFailed,
  )
  const { data: soap } = useSOAPNote(
    isComplete || isCompletedWithErrors ? consultationId : "",
  )
  const regenerateSOAP = useRegenerateSOAPNote(
    isComplete || isCompletedWithErrors ? consultationId : "",
  )
  const { data: audio } = useConsultationAudio(
    consultationId,
    isComplete || isCompletedWithErrors,
  )
  const updateConsultation = useUpdateConsultation(consultationId)
  const retryProcessing = useRetryProcessing(consultationId)

  const playerRef = useRef<AudioPlayerHandle>(null)
  useAudioHotkeys(playerRef, (isComplete || isCompletedWithErrors) && !!audio?.url)
  const [currentTimeMs, setCurrentTimeMs] = useState(0)
  const transcriptListRef = useRef<HTMLDivElement>(null)
  const transcriptEndRef = useRef<HTMLDivElement>(null)
  const prevStepRef = useRef<string | null>(null)
  const prevClassifiedCountRef = useRef(0)

  const currentProgress = sseProgress.progress || consultation?.processing_progress || 0
  const currentStep = sseProgress.step || consultation?.processing_step || null

  // During transcription: auto-scroll to bottom as new segments arrive
  const isTranscribing = currentStep === "transcribing"
  useEffect(() => {
    if (isTranscribing && streamedSegments.length > 0) {
      transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }
  }, [isTranscribing, streamedSegments.length])

  // When transcription finishes (step transitions away from "transcribing"): scroll to top
  useEffect(() => {
    if (prevStepRef.current === "transcribing" && currentStep && currentStep !== "transcribing") {
      transcriptListRef.current?.scrollTo({ top: 0, behavior: "smooth" })
    }
    prevStepRef.current = currentStep
  }, [currentStep])

  // During classification: scroll to the latest classified segment
  const classifiedCount = streamedSegments.filter(
    (s) => s.status === "classified" || s.status === "failed_classification",
  ).length
  useEffect(() => {
    if (classifiedCount > prevClassifiedCountRef.current && classifiedCount > 0) {
      // Find the last classified segment's sequence number
      const classified = streamedSegments.filter(
        (s) => s.status === "classified" || s.status === "failed_classification",
      )
      const lastSeq = classified[classified.length - 1]?.sequence
      if (lastSeq != null) {
        const el = document.getElementById(`segment-${lastSeq}`)
        el?.scrollIntoView({ behavior: "smooth", block: "center" })
      }
    }
    prevClassifiedCountRef.current = classifiedCount
  }, [classifiedCount, streamedSegments])

  const handleSegmentClick = useCallback((ms: number) => {
    playerRef.current?.seekTo(ms)
  }, [])

  const segments = transcripts?.segments
  const activeSegmentId = useMemo(() => {
    if (!segments || currentTimeMs <= 0) return null
    const seg = segments.find(
      (s) => s.timestamp_start_ms <= currentTimeMs && currentTimeMs < s.timestamp_end_ms,
    )
    return seg?.id ?? null
  }, [segments, currentTimeMs])

  // Auto-scroll to active transcript segment during playback
  useEffect(() => {
    if (activeSegmentId) {
      const activeSeg = segments?.find((s) => s.id === activeSegmentId)
      if (activeSeg) {
        const el = document.getElementById(`segment-${activeSeg.sequence_number}`)
        el?.scrollIntoView({ behavior: "smooth", block: "nearest" })
      }
    }
  }, [activeSegmentId, segments])

  if (!consultation) return <UploadProcessingSkeleton />

  // ==================================================================
  // Completed view (with or without errors)
  // ==================================================================
  if (isComplete || isCompletedWithErrors) {
    function handleFieldSave(field: string, value: string) {
      updateConsultation.mutate(
        { [field]: value || null },
        { onError: () => toast.error(t("Failed to save changes")) },
      )
    }

    return (
      <div className="flex h-[calc(100dvh-theme(spacing.14)-theme(spacing.12))] flex-col gap-4">
        {isCompletedWithErrors && consultation.error_message && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>{t("Completed with errors")}</AlertTitle>
            <AlertDescription className="flex items-center justify-between">
              <span>{consultation.error_message}</span>
              <Button
                variant="outline"
                size="sm"
                className="ml-4 shrink-0 gap-1.5"
                disabled={retryProcessing.isPending}
                onClick={() =>
                  retryProcessing.mutate(undefined, {
                    onSuccess: () => toast.success(t("Retrying failed segments...")),
                    onError: (err) =>
                      toast.error(err instanceof Error ? err.message : t("Retry failed")),
                  })
                }
              >
                <RotateCcw className={`h-3.5 w-3.5 ${retryProcessing.isPending ? "animate-spin" : ""}`} />
                {t("Retry Failed")}
              </Button>
            </AlertDescription>
          </Alert>
        )}

        <ConsultationContextBar
          consultation={consultation}
          audioDurationMs={audio?.duration_ms}
          backHref="/consultations"
          breadcrumbs={[
            { label: t("Consultations"), href: "/consultations" },
            { label: consultation.title || t("Consultation") },
          ]}
          actions={
            <>
              <Button
                variant="outline"
                disabled={regenerateSOAP.isPending}
                className="gap-2"
                onClick={() =>
                  regenerateSOAP.mutate(undefined, {
                    onSuccess: () => toast.success(t("SOAP note regenerated")),
                    onError: () => toast.error(t("Failed to regenerate SOAP note")),
                  })
                }
              >
                <RefreshCw className={`h-4 w-4 ${regenerateSOAP.isPending ? "animate-spin" : ""}`} />
                {regenerateSOAP.isPending ? t("Regenerating...") : t("Regenerate")}
              </Button>
              <Button onClick={() => router.push(`/consultations/${consultationId}/soap`)}>
                {t("Review SOAP Note")}
              </Button>
            </>
          }
        />

        {/* Editable fields */}
        <div className="grid grid-cols-1 gap-3 border-b pb-4 sm:grid-cols-3">
          <div className="space-y-1">
            <Label className="text-xs">{t("Title")}</Label>
            <Input
              defaultValue={consultation.title}
              placeholder={t("Consultation title")}
              onBlur={(e) => handleFieldSave("title", e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">{t("Patient Identifier")}</Label>
            <Input
              defaultValue={consultation.patient_identifier ?? ""}
              placeholder={t("optional")}
              onBlur={(e) => handleFieldSave("patient_identifier", e.target.value)}
            />
          </div>
          <LanguageSelector
            value={consultation.language}
            onChange={(lang) => handleFieldSave("language", lang)}
          />
        </div>

        {/* Stats row */}
        {transcripts && transcripts.segments.length > 0 && (
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
            {audio?.duration_ms != null && audio.duration_ms > 0 && (
              <span className="font-mono tabular-nums">
                {Math.floor(audio.duration_ms / 60000)}:{String(Math.floor((audio.duration_ms / 1000) % 60)).padStart(2, "0")} {t("duration")}
              </span>
            )}
            <span>{transcripts.segments.length} {t("segments")}</span>
            <span>
              {transcripts.segments.filter((s) => s.is_medically_relevant).length}{" "}
              {t("relevant")}
            </span>
          </div>
        )}

        {audio?.url && (
          <AudioPlayer
            ref={playerRef}
            src={audio.url}
            durationMs={audio.duration_ms}
            onTimeUpdate={setCurrentTimeMs}
          />
        )}

        <ScribeLayout>
          <ScribeLayout.Left>
            <div className="flex h-8 items-center">
              <h3 className="text-sm font-semibold">{t("Transcript")}</h3>
            </div>
            <div className="min-h-0 flex-1 space-y-2 overflow-y-auto px-0.5 pt-4">
              {transcripts?.segments.map((seg) => (
                <TranscriptSegmentItem
                  key={seg.id}
                  text={seg.text}
                  isMedicallyRelevant={seg.is_medically_relevant}
                  speakerLabel={seg.speaker_label}
                  sequence={seg.sequence_number}
                  status={seg.status}
                  errorMessage={seg.error_message}
                  emotion={seg.emotion}
                  isActive={seg.id === activeSegmentId}
                  onClick={
                    audio?.url && seg.timestamp_start_ms > 0
                      ? () => handleSegmentClick(seg.timestamp_start_ms)
                      : undefined
                  }
                />
              ))}
              {(!transcripts || transcripts.segments.length === 0) && (
                <p className="text-muted-foreground text-sm">{t("No transcript segments found.")}</p>
              )}
            </div>
          </ScribeLayout.Left>
          <ScribeLayout.Right>
            <Tabs defaultValue="preview" className="flex h-full flex-col gap-0">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold">{t("SOAP Note")}</h3>
                <div className="flex items-center gap-2">
                  {soap && (
                    <Badge variant={soap.is_draft ? "secondary" : "default"}>
                      {soap.is_draft ? t("Draft") : t("Completed")}
                    </Badge>
                  )}
                  <TabsList>
                    <TabsTrigger value="preview">{t("Preview")}</TabsTrigger>
                    <TabsTrigger value="raw">{t("Raw")}</TabsTrigger>
                  </TabsList>
                </div>
              </div>
              <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-px pt-4">
                {soap ? (
                  <>
                    {(
                      [
                        { key: "subjective", label: t("Subjective") },
                        { key: "objective", label: t("Objective") },
                        { key: "assessment", label: t("Assessment") },
                        { key: "plan", label: t("Plan") },
                      ] as const
                    ).map(({ key, label }) => (
                      <Card key={key}>
                        <CardHeader>
                          <CardTitle className="text-base">{label}</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <TabsContent value="preview" className="mt-0">
                            {soap[key] ? (
                              <div className="prose prose-sm dark:prose-invert max-w-none">
                                <MarkdownPreview>{soap[key]}</MarkdownPreview>
                              </div>
                            ) : (
                              <p className="text-muted-foreground text-sm italic">{t("No content yet")}</p>
                            )}
                          </TabsContent>
                          <TabsContent value="raw" className="mt-0">
                            <div className="text-sm whitespace-pre-wrap">
                              {soap[key] || (
                                <span className="text-muted-foreground italic">{t("Empty")}</span>
                              )}
                            </div>
                          </TabsContent>
                        </CardContent>
                      </Card>
                    ))}
                  </>
                ) : (
                  <p className="text-muted-foreground text-sm">{t("SOAP note not found.")}</p>
                )}
              </div>
            </Tabs>
          </ScribeLayout.Right>
        </ScribeLayout>
      </div>
    )
  }

  // ==================================================================
  // Failed view
  // ==================================================================
  if (isFailed) {
    const hasTranscripts = transcripts && transcripts.segments.length > 0

    return (
      <div className="flex h-[calc(100dvh-theme(spacing.14)-theme(spacing.12))] flex-col gap-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>{t("Processing Failed")}</AlertTitle>
          <AlertDescription className="flex items-center justify-between">
            <span>{consultation.error_message || t("An unknown error occurred.")}</span>
            <div className="ml-4 flex shrink-0 gap-2">
              {hasTranscripts && (
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1.5"
                  disabled={retryProcessing.isPending}
                  onClick={() =>
                    retryProcessing.mutate(undefined, {
                      onSuccess: () => toast.success(t("Retrying failed segments...")),
                      onError: (err) =>
                        toast.error(err instanceof Error ? err.message : t("Retry failed")),
                    })
                  }
                >
                  <RotateCcw className={`h-3.5 w-3.5 ${retryProcessing.isPending ? "animate-spin" : ""}`} />
                  {t("Retry")}
                </Button>
              )}
              <Button variant="outline" size="sm" onClick={() => router.push("/consultations")}>
                {t("Back")}
              </Button>
            </div>
          </AlertDescription>
        </Alert>

        {hasTranscripts ? (
          <ScribeLayout>
            <ScribeLayout.Left>
              <h3 className="mb-3 text-lg font-semibold">{t("Partial Transcripts")}</h3>
              <div className="flex-1 space-y-2 overflow-y-auto px-0.5">
                {transcripts.segments.map((seg) => (
                  <TranscriptSegmentItem
                    key={seg.id}
                    text={seg.text}
                    isMedicallyRelevant={seg.is_medically_relevant}
                    speakerLabel={seg.speaker_label}
                    sequence={seg.sequence_number}
                    status={seg.status}
                    errorMessage={seg.error_message}
                    emotion={seg.emotion}
                  />
                ))}
              </div>
            </ScribeLayout.Left>
            <ScribeLayout.Right>
              <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
                <AlertCircle className="text-muted-foreground h-10 w-10" />
                <p className="text-muted-foreground text-sm">
                  {t("SOAP note could not be generated due to processing errors.")}
                </p>
              </div>
            </ScribeLayout.Right>
          </ScribeLayout>
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
            <p className="text-muted-foreground text-sm">
              {t("No transcripts were produced. Please try uploading the audio file again.")}
            </p>
            <Button variant="outline" onClick={() => router.push("/consultations")}>
              {t("Back to Consultations")}
            </Button>
          </div>
        )}
      </div>
    )
  }

  // ==================================================================
  // Processing view
  // ==================================================================
  const transcribedCount = streamedSegments.filter((s) => s.status !== "failed_transcription").length
  const relevantCount = streamedSegments.filter((s) => s.status === "classified" && s.isMedicallyRelevant).length
  const smallTalkCount = streamedSegments.filter((s) => s.status === "classified" && !s.isMedicallyRelevant).length
  const failedCount = streamedSegments.filter(
    (s) => s.status === "failed_transcription" || s.status === "failed_classification",
  ).length

  return (
    <div className="flex h-[calc(100dvh-theme(spacing.14)-theme(spacing.12))] flex-col gap-6">
      <ConsultationContextBar
        consultation={consultation}
        statusOverride="processing"
        backHref="/consultations"
        breadcrumbs={[
          { label: t("Consultations"), href: "/consultations" },
          { label: consultation.title || t("New Consultation") },
        ]}
        actions={
          <div className="text-muted-foreground font-mono text-lg tabular-nums">
            {currentProgress}%
          </div>
        }
      />

      {/* Progress bar */}
      <div className="flex items-center gap-3">
        <Progress value={currentProgress} className="h-2 flex-1" />
      </div>

      {/* Two-column content */}
      <ScribeLayout>
        {/* Left: Live transcript */}
        <ScribeLayout.Left>
          <div className="flex h-full flex-col">
            <h3 className="mb-3 text-lg font-semibold">
              {t("Transcript")}
              {streamedSegments.length > 0 && (
                <span className="text-muted-foreground ml-2 text-sm font-normal">
                  ({streamedSegments.length})
                </span>
              )}
            </h3>
            <div ref={transcriptListRef} className="flex-1 space-y-2 overflow-y-auto px-0.5">
              {streamedSegments.length > 0 ? (
                <>
                  {streamedSegments.map((seg) => (
                    <div key={seg.sequence} id={`segment-${seg.sequence}`}>
                      <TranscriptSegmentItem
                        text={seg.text}
                        isMedicallyRelevant={seg.isMedicallyRelevant}
                        speakerLabel={null}
                        sequence={seg.sequence}
                        status={seg.status}
                        errorMessage={seg.errorMessage}
                        emotion={seg.emotion}
                      />
                    </div>
                  ))}
                  <div ref={transcriptEndRef} />
                </>
              ) : (
                <p className="text-muted-foreground text-sm">
                  {t("Waiting for transcription to begin...")}
                </p>
              )}
            </div>
          </div>
        </ScribeLayout.Left>

        {/* Right: Processing info */}
        <ScribeLayout.Right>
          <div className="flex h-full flex-col">
            <h3 className="mb-3 text-lg font-semibold">
              {t("Processing")}
            </h3>
            <div className="flex-1 space-y-6 overflow-y-auto">
              {/* Steps */}
              <StepChecklist currentStep={currentStep} stepLabels={stepLabels} />

              {/* Stats */}
              {streamedSegments.length > 0 && (
                <div className="border-t pt-6">
                  <div className="grid grid-cols-2 gap-x-6 gap-y-4">
                    <div>
                      <div className="text-foreground text-2xl font-bold tabular-nums">
                        {transcribedCount}
                      </div>
                      <div className="text-muted-foreground text-xs">
                        {t("Transcribed")}
                      </div>
                    </div>
                    <div>
                      <div className="text-primary text-2xl font-bold tabular-nums">
                        {relevantCount}
                      </div>
                      <div className="text-muted-foreground text-xs">
                        {t("Relevant")}
                      </div>
                    </div>
                    <div>
                      <div className="text-muted-foreground text-2xl font-bold tabular-nums">
                        {smallTalkCount}
                      </div>
                      <div className="text-muted-foreground text-xs">
                        {t("Small Talk")}
                      </div>
                    </div>
                    {failedCount > 0 && (
                      <div>
                        <div className="text-destructive text-2xl font-bold tabular-nums">
                          {failedCount}
                        </div>
                        <div className="text-muted-foreground text-xs">
                          {t("Failed")}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </ScribeLayout.Right>
      </ScribeLayout>
    </div>
  )
}
