"use client"

import { useState } from "react"
import { useExtracted } from "next-intl"
import { Loader2 } from "lucide-react"
import { Badge } from "@workspace/ui/components/badge"
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
import { Textarea } from "@workspace/ui/components/textarea"
import { MarkdownPreview } from "@/components/markdown-preview"
import { useScribeStore } from "@/lib/stores/use-scribe-store"

export function SOAPEditor() {
  const t = useExtracted()
  const { soapNote, updateSOAPSection, status } = useScribeStore()
  const [viewMode, setViewMode] = useState<"preview" | "raw">("preview")

  const isProcessing = status === "processing"
  const hasContent = !!(
    soapNote.subjective ||
    soapNote.objective ||
    soapNote.assessment ||
    soapNote.plan
  )

  const sections = [
    {
      key: "subjective" as const,
      label: t("Subjective"),
      borderClass: "border-l-4 border-l-blue-500",
    },
    {
      key: "objective" as const,
      label: t("Objective"),
      borderClass: "border-l-4 border-l-emerald-500",
    },
    {
      key: "assessment" as const,
      label: t("Assessment"),
      borderClass: "border-l-4 border-l-amber-500",
    },
    {
      key: "plan" as const,
      label: t("Plan"),
      borderClass: "border-l-4 border-l-violet-500",
    },
  ]

  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold">{t("SOAP Note")}</h3>
          {isProcessing ? (
            <Badge variant="secondary" className="gap-1.5">
              <Loader2 className="h-3 w-3 animate-spin" />
              {t("Generating...")}
            </Badge>
          ) : (
            <Badge variant="secondary">{t("Draft")}</Badge>
          )}
        </div>
        <Tabs
          value={viewMode}
          onValueChange={(v) => setViewMode(v as "preview" | "raw")}
        >
          <TabsList>
            <TabsTrigger value="preview">{t("Preview")}</TabsTrigger>
            <TabsTrigger value="raw">{t("Raw")}</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>
      <div className="flex-1 space-y-4 overflow-y-auto p-1">
        {!hasContent && isProcessing ? (
          <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <div className="space-y-1">
              <p className="text-sm font-medium">
                {t("Generating SOAP Note...")}
              </p>
              <p className="text-xs text-muted-foreground">
                {t(
                  "Analyzing transcript and generating structured clinical notes"
                )}
              </p>
            </div>
          </div>
        ) : (
          sections.map(({ key, label, borderClass }) => (
            <Card key={key} className={borderClass}>
              <CardHeader className="pb-2 pt-3 px-4">
                <CardTitle className="text-sm">{label}</CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-3">
                {viewMode === "preview" ? (
                  soapNote[key] ? (
                    <div className="prose prose-sm max-w-none dark:prose-invert">
                      <MarkdownPreview>{soapNote[key]}</MarkdownPreview>
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground italic">
                      {isProcessing
                        ? t("Waiting for content...")
                        : t("No content yet")}
                    </p>
                  )
                ) : (
                  <Textarea
                    value={soapNote[key]}
                    onChange={(e) => updateSOAPSection(key, e.target.value)}
                    rows={4}
                    className="resize-none"
                  />
                )}
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  )
}
