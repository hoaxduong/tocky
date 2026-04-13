"use client"

import { useMemo, useRef, useState } from "react"
import {
  AudioPlayer,
  type AudioPlayerHandle,
} from "@/components/audio-player"
import { useExtracted } from "next-intl"
import {
  Activity,
  AlertTriangle,
  Check,
  FlaskConical,
  Play,
  Pill,
  RefreshCw,
  Stethoscope,
  Syringe,
  Tag,
} from "lucide-react"
import { cn } from "@workspace/ui/lib/utils"
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
  useResuggestICD10,
  useSOAPNote,
  useTranscripts,
  useUpdateSOAPNote,
  type ICD10Code,
  type ReviewFlag,
  type SOAPSection,
  type TranscriptSegment,
} from "@/hooks/use-soap-note"
import { useConsultation } from "@/hooks/use-consultation"
import { toast } from "sonner"
import { SOAPFormSkeleton } from "@/components/skeletons"
import { ConsultationContextBar } from "@/components/consultation-context-bar"
import { ICD10CodeCard } from "@/components/icd10-code-card"
import { ElfiePatientCard, ElfiePushDialog } from "@/components/elfie"
import { useAudioHotkeys } from "@/hooks/use-audio-hotkeys"

interface SOAPReviewFormProps {
  consultationId: string
}

export function SOAPReviewForm({ consultationId }: SOAPReviewFormProps) {
  const t = useExtracted()
  const playerRef = useRef<AudioPlayerHandle>(null)
  const [dismissedFlags, setDismissedFlags] = useState<Set<number>>(new Set())

  const { data: consultation } = useConsultation(consultationId)
  const { data: soap, isLoading } = useSOAPNote(consultationId)
  const hasAudioForHotkeys = !!soap && !soap.is_draft
  useAudioHotkeys(playerRef, hasAudioForHotkeys)
  const updateSOAP = useUpdateSOAPNote(consultationId)
  const finalizeSOAP = useFinalizeSOAPNote(consultationId)
  const regenerateSOAP = useRegenerateSOAPNote(consultationId)
  const resuggestICD10 = useResuggestICD10(consultationId)
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

  const sections: {
    key: SOAPSection
    label: string
    borderClass: string
  }[] = [
    {
      key: "subjective",
      label: t("Subjective"),
      borderClass: "border-l-4 border-l-blue-500",
    },
    {
      key: "objective",
      label: t("Objective"),
      borderClass: "border-l-4 border-l-emerald-500",
    },
    {
      key: "assessment",
      label: t("Assessment"),
      borderClass: "border-l-4 border-l-amber-500",
    },
    {
      key: "plan",
      label: t("Plan"),
      borderClass: "border-l-4 border-l-violet-500",
    },
  ]

  function handleSave(section: string, value: string) {
    updateSOAP.mutate(
      { [section]: value },
      { onError: () => toast.error(t("Failed to save changes")) }
    )
  }

  function handleSaveICD10(codes: ICD10Code[]) {
    updateSOAP.mutate(
      { icd10_codes: codes },
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

  function scrollToSection(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" })
  }

  const visibleFlags = (soap.review_flags ?? []).filter(
    (_, i) => !dismissedFlags.has(i)
  )

  const confirmedCodes = (soap.icd10_codes ?? []).filter(
    (c) => c.status === "confirmed"
  ).length
  const totalCodes = (soap.icd10_codes ?? []).filter(
    (c) => c.status !== "rejected"
  ).length
  const entityCount = soap.medical_entities
    ? Object.values(soap.medical_entities).reduce(
        (acc, v) => acc + (Array.isArray(v) ? v.length : 0),
        0
      )
    : 0

  return (
    <div className="space-y-6">
      {consultation && (
        <ConsultationContextBar
          consultation={consultation}
          audioDurationMs={audio?.duration_ms}
          backHref={`/consultations/${consultationId}`}
          breadcrumbs={[
            { label: t("Consultations"), href: "/consultations" },
            {
              label: consultation.title || t("Consultation"),
              href: `/consultations/${consultationId}`,
            },
            { label: t("SOAP Note") },
          ]}
          actions={
            <>
              {!soap.is_draft && consultation.patient_identifier && (
                <ElfiePushDialog
                  consultationId={consultationId}
                  patientIdentifier={consultation.patient_identifier}
                  planText={soap.plan ?? ""}
                />
              )}
              {soap.is_draft && (
                <Badge variant="secondary">{t("Draft")}</Badge>
              )}
              {soap.is_draft && (
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
              )}
              {soap.is_draft && (
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button
                      disabled={finalizeSOAP.isPending}
                      className="gap-2"
                    >
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
      )}

      {/* Summary stats */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <button
          type="button"
          className={cn(
            "rounded-lg border p-3 text-left transition-colors hover:bg-accent/50",
            visibleFlags.length > 0 &&
              "border-amber-500/30 bg-amber-500/5"
          )}
          onClick={() => scrollToSection("reviewer-flags")}
        >
          <div
            className={cn(
              "text-2xl font-bold tabular-nums",
              visibleFlags.length > 0
                ? "text-amber-600 dark:text-amber-400"
                : "text-muted-foreground"
            )}
          >
            {visibleFlags.length}
          </div>
          <div className="text-xs text-muted-foreground">{t("Flags")}</div>
        </button>
        <button
          type="button"
          className="rounded-lg border p-3 text-left transition-colors hover:bg-accent/50"
          onClick={() => scrollToSection("icd10-codes")}
        >
          <div className="text-2xl font-bold tabular-nums">
            {confirmedCodes}/{totalCodes}
          </div>
          <div className="text-xs text-muted-foreground">
            {t("ICD-10 Confirmed")}
          </div>
        </button>
        <div className="rounded-lg border p-3">
          <div className="text-2xl font-bold tabular-nums text-muted-foreground">
            v{soap.version}
          </div>
          <div className="text-xs text-muted-foreground">{t("Version")}</div>
        </div>
        <button
          type="button"
          className="rounded-lg border p-3 text-left transition-colors hover:bg-accent/50"
          onClick={() => scrollToSection("medical-entities")}
        >
          <div className="text-2xl font-bold tabular-nums">{entityCount}</div>
          <div className="text-xs text-muted-foreground">
            {t("Entities")}
          </div>
        </button>
      </div>

      {audio?.url && (
        <AudioPlayer
          ref={playerRef}
          src={audio.url}
          durationMs={audio.duration_ms}
        />
      )}

      {visibleFlags.length > 0 && (
        <Card id="reviewer-flags">
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

      <div id="icd10-codes">
        <ICD10CodeCard
          codes={soap.icd10_codes ?? []}
          isDraft={soap.is_draft}
          onUpdate={handleSaveICD10}
          onResuggest={() =>
            resuggestICD10.mutate(undefined, {
              onSuccess: () => toast.success(t("ICD-10 codes re-suggested")),
              onError: () => toast.error(t("Failed to suggest ICD-10 codes")),
            })
          }
          isResuggesting={resuggestICD10.isPending}
        />
      </div>

      {consultation && (
        <ElfiePatientCard
          patientIdentifier={consultation.patient_identifier}
        />
      )}

      {sections.map(({ key, label, borderClass }) => (
        <Card key={key} id={`soap-${key}`} className={borderClass}>
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
          <Card id="medical-entities">
            <CardHeader>
              <CardTitle className="text-base">
                {t("Medical Entities")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {sortEntityCategories(
                  Object.entries(soap.medical_entities)
                ).map(
                  ([category, entities]) =>
                    Array.isArray(entities) &&
                    entities.length > 0 && (
                      <div key={category} className="space-y-1.5">
                        <h4 className="flex items-center gap-1.5 text-xs font-medium tracking-wider text-muted-foreground uppercase">
                          <EntityCategoryIcon category={category} />
                          {category}
                          <Badge
                            variant="secondary"
                            className="ml-1 text-[10px]"
                          >
                            {entities.length}
                          </Badge>
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

// ---------------------------------------------------------------------------
// Medical entity helpers
// ---------------------------------------------------------------------------

const ENTITY_CATEGORY_ORDER = [
  "symptoms",
  "diagnoses",
  "medications",
  "vitals",
  "procedures",
  "lab_results",
]

const ENTITY_CATEGORY_ICONS: Record<
  string,
  React.ComponentType<{ className?: string }>
> = {
  symptoms: Stethoscope,
  diagnoses: Activity,
  medications: Pill,
  vitals: Activity,
  procedures: Syringe,
  lab_results: FlaskConical,
}

function EntityCategoryIcon({ category }: { category: string }) {
  const key = category.toLowerCase().replace(/\s+/g, "_")
  const Icon = ENTITY_CATEGORY_ICONS[key] ?? Tag
  return <Icon className="h-3.5 w-3.5" />
}

function sortEntityCategories(
  entries: [string, unknown][]
): [string, unknown][] {
  return [...entries].sort((a, b) => {
    const aKey = a[0].toLowerCase().replace(/\s+/g, "_")
    const bKey = b[0].toLowerCase().replace(/\s+/g, "_")
    const aIdx = ENTITY_CATEGORY_ORDER.indexOf(aKey)
    const bIdx = ENTITY_CATEGORY_ORDER.indexOf(bKey)
    const aOrder = aIdx === -1 ? ENTITY_CATEGORY_ORDER.length : aIdx
    const bOrder = bIdx === -1 ? ENTITY_CATEGORY_ORDER.length : bIdx
    return aOrder - bOrder
  })
}
