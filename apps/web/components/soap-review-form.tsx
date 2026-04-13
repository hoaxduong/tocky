"use client"

import { useMemo, useRef, useState } from "react"
import {
  AudioPlayer,
  type AudioPlayerHandle,
} from "@/components/audio-player"
import { useExtracted } from "next-intl"
import { AlertTriangle, Check, Play, RefreshCw } from "lucide-react"
import { Button } from "@workspace/ui/components/button"
import { MarkdownPreview } from "@/components/markdown-preview"
import { Badge } from "@workspace/ui/components/badge"
import { Textarea } from "@workspace/ui/components/textarea"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@workspace/ui/components/card"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@workspace/ui/components/tabs"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@workspace/ui/components/alert-dialog"
import {
  useConsultationAudio,
  useFinalizeSOAPNote,
  useRegenerateSOAPNote,
  useSOAPNote,
  useTranscripts,
  useUpdateSOAPNote,
  type ReviewFlag,
  type SOAPSection,
  type TranscriptSegment,
} from "@/hooks/use-soap-note"
import { toast } from "sonner"
import { SOAPFormSkeleton } from "@/components/skeletons"
import { PageHeader } from "@/components/page-header"

interface SOAPReviewFormProps {
  consultationId: string
}

export function SOAPReviewForm({ consultationId }: SOAPReviewFormProps) {
  const t = useExtracted()
  const playerRef = useRef<AudioPlayerHandle>(null)
  const [dismissedFlags, setDismissedFlags] = useState<Set<number>>(new Set())

  const { data: soap, isLoading } = useSOAPNote(consultationId)
  const updateSOAP = useUpdateSOAPNote(consultationId)
  const finalizeSOAP = useFinalizeSOAPNote(consultationId)
  const regenerateSOAP = useRegenerateSOAPNote(consultationId)
  const { data: transcripts } = useTranscripts(consultationId)
  const hasAudio = !!soap && !soap.is_draft
  const { data: audio } = useConsultationAudio(consultationId, hasAudio)

  const flagTranscriptMatches = useMemo(
    () =>
      matchFlagsToTranscript(
        soap?.review_flags ?? [],
        transcripts?.segments ?? []
      ),
    [soap?.review_flags, transcripts?.segments]
  )

  if (isLoading) {
    return <SOAPFormSkeleton />
  }

  if (!soap) {
    return <p className="text-muted-foreground">SOAP note not found</p>
  }

  const sections: { key: SOAPSection; label: string }[] = [
    { key: "subjective", label: t("Subjective") },
    { key: "objective", label: t("Objective") },
    { key: "assessment", label: t("Assessment") },
    { key: "plan", label: t("Plan") },
  ]

  function handleSave(section: string, value: string) {
    updateSOAP.mutate(
      { [section]: value },
      { onError: () => toast.error(t("Failed to save changes")) }
    )
  }

  function handleFinalize() {
    finalizeSOAP.mutate(undefined, {
      onSuccess: () => toast.success(t("SOAP note finalized")),
      onError: () => toast.error(t("Failed to finalize note")),
    })
  }

  function seekTo(ms: number) {
    playerRef.current?.seekTo(ms)
  }

  const visibleFlags = (soap.review_flags ?? []).filter(
    (_, i) => !dismissedFlags.has(i)
  )

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader
        title={t("SOAP Note")}
        backHref={`/consultations/${consultationId}`}
        breadcrumbs={[
          { label: t("Consultations"), href: "/consultations" },
          { label: t("SOAP Note") },
        ]}
        actions={
          <>
            <Badge variant={soap.is_draft ? "secondary" : "default"}>
              {soap.is_draft ? t("Draft") : t("Completed")}
            </Badge>
            {soap.is_draft && (
              <Button
                variant="outline"
                disabled={regenerateSOAP.isPending}
                className="gap-2"
                onClick={() =>
                  regenerateSOAP.mutate(undefined, {
                    onSuccess: () => toast.success(t("SOAP note regenerated")),
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
            )}
            {soap.is_draft && (
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button disabled={finalizeSOAP.isPending} className="gap-2">
                    <Check className="h-4 w-4" />
                    {t("Finalize Note")}
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>
                      {t("Finalize SOAP Note?")}
                    </AlertDialogTitle>
                    <AlertDialogDescription>
                      {t(
                        "Running the QA reviewer and preparing playback audio. This takes a few seconds and locks the note for editing."
                      )}
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>{t("Cancel")}</AlertDialogCancel>
                    <AlertDialogAction onClick={handleFinalize}>
                      {t("Finalize")}
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            )}
          </>
        }
      />

      {audio?.url && (
        <AudioPlayer
          ref={playerRef}
          src={audio.url}
          durationMs={audio.duration_ms}
        />
      )}

      {visibleFlags.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertTriangle className="h-4 w-4 text-amber-600" />
              {t("Reviewer Flags")}
              <Badge variant="outline">{visibleFlags.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {soap.review_flags.map((flag, i) =>
              dismissedFlags.has(i) ? null : (
                <FlagCard
                  key={i}
                  flag={flag}
                  match={flagTranscriptMatches[i] ?? null}
                  canSeek={!!audio?.url}
                  onSeek={seekTo}
                  onDismiss={() =>
                    setDismissedFlags((prev) => new Set(prev).add(i))
                  }
                  t={t}
                />
              )
            )}
          </CardContent>
        </Card>
      )}

      {sections.map(({ key, label }) => (
        <Card key={key}>
          <CardHeader>
            <CardTitle className="text-base">{label}</CardTitle>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="preview">
              <TabsList>
                <TabsTrigger value="preview">{t("Preview")}</TabsTrigger>
                <TabsTrigger value="raw">{t("Raw")}</TabsTrigger>
              </TabsList>
              <TabsContent value="preview">
                {soap[key] ? (
                  <div className="prose prose-sm max-w-none dark:prose-invert">
                    <MarkdownPreview>{soap[key]}</MarkdownPreview>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground italic">
                    {t("No content yet")}
                  </p>
                )}
              </TabsContent>
              <TabsContent value="raw">
                <Textarea
                  value={soap[key]}
                  onChange={(e) => handleSave(key, e.target.value)}
                  disabled={!soap.is_draft}
                  rows={5}
                  className="resize-none"
                />
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      ))}

      {soap.medical_entities &&
        Object.keys(soap.medical_entities).length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                {t("Medical Entities")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {Object.entries(soap.medical_entities).map(
                  ([category, entities]) =>
                    Array.isArray(entities) &&
                    entities.length > 0 && (
                      <div key={category} className="space-y-1.5">
                        <h4 className="text-xs font-medium tracking-wider text-muted-foreground uppercase">
                          {category}
                        </h4>
                        <div className="flex flex-wrap gap-1.5">
                          {entities.map((entity, i) => (
                            <Badge key={i} variant="outline">
                              {entity}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )
                )}
              </div>
            </CardContent>
          </Card>
        )}
    </div>
  )
}

interface FlagCardProps {
  flag: ReviewFlag
  match: TranscriptSegment | null
  canSeek: boolean
  onSeek: (ms: number) => void
  onDismiss: () => void
  t: (s: string) => string
}

function FlagCard({
  flag,
  match,
  canSeek,
  onSeek,
  onDismiss,
  t,
}: FlagCardProps) {
  const issueLabel = ISSUE_LABELS[flag.issue_type] ?? flag.issue_type

  return (
    <div className="space-y-2 rounded-md border bg-muted/30 p-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Badge variant="secondary" className="capitalize">
            {flag.section}
          </Badge>
          <Badge variant="outline">{t(issueLabel)}</Badge>
          <Badge variant="outline" className={confidenceClass(flag.confidence)}>
            {flag.confidence}
          </Badge>
        </div>
        <Button variant="ghost" size="sm" onClick={onDismiss}>
          {t("Dismiss")}
        </Button>
      </div>
      <blockquote className="border-l-2 pl-2 text-sm italic">
        "{flag.quoted_span}"
      </blockquote>
      <p className="text-sm">{flag.suggestion}</p>
      {match && canSeek && (
        <Button
          variant="outline"
          size="sm"
          className="gap-1"
          onClick={() => onSeek(match.timestamp_start_ms)}
        >
          <Play className="h-3 w-3" />
          {t("Play source audio")}
          <span className="text-muted-foreground tabular-nums">
            {formatMs(match.timestamp_start_ms)}
          </span>
        </Button>
      )}
    </div>
  )
}

const ISSUE_LABELS: Record<string, string> = {
  symptom_diagnosis_mismatch: "Symptom/diagnosis mismatch",
  ambiguous_term: "Ambiguous term",
  translation_uncertainty: "Translation uncertainty",
  missing_information: "Missing information",
}

function confidenceClass(level: ReviewFlag["confidence"]) {
  if (level === "high") return "border-red-500 text-red-700"
  if (level === "medium") return "border-amber-500 text-amber-700"
  return "border-muted-foreground/40 text-muted-foreground"
}

function formatMs(ms: number) {
  const total = Math.floor(ms / 1000)
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m}:${s.toString().padStart(2, "0")}`
}

function matchFlagsToTranscript(
  flags: ReviewFlag[],
  segments: TranscriptSegment[]
): (TranscriptSegment | null)[] {
  return flags.map((flag) => {
    const needle = flag.quoted_span.trim().toLowerCase()
    if (!needle) return null
    const direct = segments.find((s) => s.text.toLowerCase().includes(needle))
    if (direct) return direct
    const words = needle.split(/\s+/).filter((w) => w.length > 3)
    if (words.length === 0) return null
    let best: { seg: TranscriptSegment; score: number } | null = null
    for (const seg of segments) {
      const lower = seg.text.toLowerCase()
      const score = words.reduce(
        (acc, w) => (lower.includes(w) ? acc + 1 : acc),
        0
      )
      if (score > 0 && (!best || score > best.score)) {
        best = { seg, score }
      }
    }
    return best && best.score >= Math.max(2, Math.ceil(words.length / 2))
      ? best.seg
      : null
  })
}
