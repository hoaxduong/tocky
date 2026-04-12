"use client"

import { useExtracted } from "next-intl"
import { useRouter } from "next/navigation"
import {
  CheckCircle2,
  Circle,
  Loader2,
  AlertCircle,
  FileAudio,
  RefreshCw,
} from "lucide-react"
import { Progress } from "@workspace/ui/components/progress"
import { Button } from "@workspace/ui/components/button"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@workspace/ui/components/card"
import { Badge } from "@workspace/ui/components/badge"
import { Input } from "@workspace/ui/components/input"
import { Label } from "@workspace/ui/components/label"
import { useConsultation, useUpdateConsultation } from "@/hooks/use-consultation"
import { useSOAPNote, useRegenerateSOAPNote } from "@/hooks/use-soap-note"
import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { TranscriptSegmentItem } from "@/components/scribe/transcript-segment"
import { LanguageSelector } from "@/components/scribe/language-selector"
import { ScribeLayout } from "@/components/scribe/scribe-layout"
import { toast } from "sonner"

interface TranscriptSegment {
  id: string
  sequence_number: number
  text: string
  language: string
  is_medically_relevant: boolean
  speaker_label: string | null
  timestamp_start_ms: number
  timestamp_end_ms: number
}

interface TranscriptResponse {
  consultation_id: string
  segments: TranscriptSegment[]
}

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
  const isFailed = consultation?.status === "failed"

  const { data: transcripts } = useTranscripts(consultationId, isComplete)
  const { data: soap } = useSOAPNote(isComplete ? consultationId : "")
  const regenerateSOAP = useRegenerateSOAPNote(isComplete ? consultationId : "")
  const updateConsultation = useUpdateConsultation(consultationId)

  if (!consultation) return null

  // Completed view — transcript + SOAP side by side
  if (isComplete) {
    function handleFieldSave(field: string, value: string) {
      updateConsultation.mutate(
        { [field]: value || null },
        {
          onError: () => toast.error(t("Failed to save changes")),
        },
      )
    }

    return (
      <div className="flex h-[calc(100dvh-theme(spacing.14)-theme(spacing.12))] flex-col gap-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="grid flex-1 grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="space-y-1">
              <Label className="text-xs">{t("Title")}</Label>
              <Input
                defaultValue={consultation.title}
                placeholder={t("Consultation title")}
                onBlur={(e) => handleFieldSave("title", e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">
                {t("Patient Identifier")}
              </Label>
              <Input
                defaultValue={consultation.patient_identifier ?? ""}
                placeholder={t("optional")}
                onBlur={(e) =>
                  handleFieldSave("patient_identifier", e.target.value)
                }
              />
            </div>
            <LanguageSelector
              value={consultation.language}
              onChange={(lang) => handleFieldSave("language", lang)}
            />
          </div>
          <div className="flex shrink-0 gap-2">
            <Button
              variant="outline"
              disabled={regenerateSOAP.isPending}
              className="gap-2"
              onClick={() =>
                regenerateSOAP.mutate(undefined, {
                  onSuccess: () =>
                    toast.success(t("SOAP note regenerated")),
                  onError: () =>
                    toast.error(t("Failed to regenerate SOAP note")),
                })
              }
            >
              <RefreshCw
                className={`h-4 w-4 ${regenerateSOAP.isPending ? "animate-spin" : ""}`}
              />
              {regenerateSOAP.isPending
                ? t("Regenerating...")
                : t("Regenerate")}
            </Button>
            <Button
              onClick={() =>
                router.push(`/consultations/${consultationId}/soap`)
              }
            >
              {t("Review SOAP Note")}
            </Button>
          </div>
        </div>

        <ScribeLayout>
          <ScribeLayout.Left>
            <h3 className="mb-3 text-lg font-semibold">{t("Transcript")}</h3>
            <div className="flex-1 space-y-2 overflow-y-auto">
              {transcripts?.segments.map((seg) => (
                <TranscriptSegmentItem
                  key={seg.id}
                  text={seg.text}
                  isMedicallyRelevant={seg.is_medically_relevant}
                  speakerLabel={seg.speaker_label}
                  sequence={seg.sequence_number}
                />
              ))}
              {(!transcripts || transcripts.segments.length === 0) && (
                <p className="text-muted-foreground text-sm">
                  {t("No transcript segments found.")}
                </p>
              )}
            </div>
          </ScribeLayout.Left>
          <ScribeLayout.Right>
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-lg font-semibold">{t("SOAP Note")}</h3>
              {soap && (
                <Badge variant={soap.is_draft ? "secondary" : "default"}>
                  {soap.is_draft ? t("Draft") : t("Completed")}
                </Badge>
              )}
            </div>
            <div className="flex-1 space-y-4 overflow-y-auto">
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
                    <div key={key} className="space-y-1">
                      <label className="text-sm font-semibold">{label}</label>
                      <div className="bg-muted/50 rounded-md border p-3 text-sm whitespace-pre-wrap">
                        {soap[key] || (
                          <span className="text-muted-foreground italic">
                            {t("Empty")}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </>
              ) : (
                <p className="text-muted-foreground text-sm">
                  {t("SOAP note not found.")}
                </p>
              )}
            </div>
          </ScribeLayout.Right>
        </ScribeLayout>
      </div>
    )
  }

  // Failed view
  if (isFailed) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-20">
        <AlertCircle className="text-destructive h-12 w-12" />
        <h2 className="text-lg font-semibold">{t("Processing Failed")}</h2>
        {consultation.error_message && (
          <p className="text-muted-foreground max-w-md text-center text-sm">
            {consultation.error_message}
          </p>
        )}
        <Button variant="outline" onClick={() => router.push("/consultations")}>
          {t("Back to Consultations")}
        </Button>
      </div>
    )
  }

  // Processing view
  const currentStepIdx = getStepIndex(consultation.processing_step)

  return (
    <div className="flex flex-col items-center justify-center gap-8 py-20">
      <FileAudio className="text-primary h-12 w-12" />
      <div className="text-center">
        <h2 className="text-xl font-semibold">
          {t("Processing your audio...")}
        </h2>
        <p className="text-muted-foreground mt-1 text-sm">
          {t("This may take a few minutes depending on the file length.")}
        </p>
      </div>

      <Card className="w-full max-w-md">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center justify-between text-sm">
            <span>{t("Progress")}</span>
            <span className="text-muted-foreground">
              {consultation.processing_progress}%
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Progress value={consultation.processing_progress} className="h-2" />
          <div className="space-y-2">
            {PROCESSING_STEP_KEYS.map((key, idx) => {
              const isCurrent = idx === currentStepIdx
              const isDone = idx < currentStepIdx
              return (
                <div
                  key={key}
                  className="flex items-center gap-2 text-sm"
                >
                  {isDone ? (
                    <CheckCircle2 className="text-primary h-4 w-4 shrink-0" />
                  ) : isCurrent ? (
                    <Loader2 className="text-primary h-4 w-4 shrink-0 animate-spin" />
                  ) : (
                    <Circle className="text-muted-foreground/40 h-4 w-4 shrink-0" />
                  )}
                  <span
                    className={
                      isDone
                        ? "text-primary"
                        : isCurrent
                          ? "font-medium"
                          : "text-muted-foreground"
                    }
                  >
                    {stepLabels[key]}
                  </span>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
