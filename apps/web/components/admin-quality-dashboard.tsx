"use client"

import { useState } from "react"
import { useExtracted } from "next-intl"
import {
  BarChart3,
  Download,
  FileText,
  Languages,
  TrendingUp,
} from "lucide-react"
import { Button } from "@workspace/ui/components/button"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@workspace/ui/components/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@workspace/ui/components/select"
import { Badge } from "@workspace/ui/components/badge"
import {
  useQualityMetrics,
  getTrainingDataExportUrl,
  type SectionEditMetrics,
} from "@/hooks/use-admin-quality"

const SECTION_LABELS: Record<string, string> = {
  subjective: "Subjective",
  objective: "Objective",
  assessment: "Assessment",
  plan: "Plan",
}

const LANGUAGE_LABELS: Record<string, string> = {
  en: "English",
  vi: "Vietnamese",
  fr: "French",
  "ar-eg": "Egyptian Arabic",
  "ar-gulf": "Gulf Arabic",
}

function EditDistanceBar({
  metrics,
}: {
  metrics: SectionEditMetrics
}) {
  const pctWidth = Math.min(metrics.pct_edited, 100)
  const avgPct = Math.round(metrics.avg_edit_distance * 100)

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">
          {SECTION_LABELS[metrics.section] || metrics.section}
        </span>
        <span className="text-muted-foreground">
          {metrics.pct_edited.toFixed(0)}% edited ({avgPct}% avg change)
        </span>
      </div>
      <div className="h-2.5 w-full rounded-full bg-muted">
        <div
          className="h-2.5 rounded-full bg-primary transition-all"
          style={{ width: `${pctWidth}%` }}
        />
      </div>
      <div className="text-xs text-muted-foreground">
        {metrics.total_compared} consultations compared
      </div>
    </div>
  )
}

export function QualityDashboard() {
  const t = useExtracted()
  const [language, setLanguage] = useState<string>("all")

  const filterParams =
    language !== "all" ? { language } : undefined
  const { data: metrics, isLoading } = useQualityMetrics(filterParams)

  function handleDownload() {
    const url = getTrainingDataExportUrl(filterParams)
    window.open(url, "_blank")
  }

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <Card key={i}>
            <CardContent className="p-6">
              <div className="h-20 animate-pulse rounded bg-muted" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  if (!metrics) {
    return (
      <Card>
        <CardContent className="p-6 text-center text-muted-foreground">
          {t("Failed to load quality metrics.")}
        </CardContent>
      </Card>
    )
  }

  const sectionData = metrics.by_section
  const hasData = metrics.total_with_history > 0
  const mostEditedSection = sectionData.reduce(
    (max, s) => (s.pct_edited > (max?.pct_edited ?? 0) ? s : max),
    sectionData[0]
  )

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="flex items-center gap-3">
        <Select value={language} onValueChange={setLanguage}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder={t("All Languages")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t("All Languages")}</SelectItem>
            {Object.entries(LANGUAGE_LABELS).map(([code, label]) => (
              <SelectItem key={code} value={code}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button
          variant="outline"
          className="ml-auto gap-2"
          onClick={handleDownload}
          disabled={!hasData}
        >
          <Download className="h-4 w-4" />
          {t("Export Training Data")}
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              {t("Total Finalized")}
            </CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.total_finalized}</div>
            <p className="text-xs text-muted-foreground">
              {t("SOAP notes finalized by doctors")}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              {t("With Version History")}
            </CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {metrics.total_with_history}
            </div>
            <p className="text-xs text-muted-foreground">
              {t("Available for quality comparison")}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              {t("Overall Edit Rate")}
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {metrics.overall_edit_rate.toFixed(1)}%
            </div>
            <p className="text-xs text-muted-foreground">
              {t("Notes with any doctor corrections")}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              {t("Most Edited Section")}
            </CardTitle>
            <Languages className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {mostEditedSection
                ? SECTION_LABELS[mostEditedSection.section]
                : "-"}
            </div>
            <p className="text-xs text-muted-foreground">
              {mostEditedSection
                ? `${mostEditedSection.pct_edited.toFixed(0)}% ${t("edited")}`
                : t("No data yet")}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Section Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>{t("Edit Rate by Section")}</CardTitle>
        </CardHeader>
        <CardContent>
          {hasData ? (
            <div className="space-y-4">
              {sectionData.map((s) => (
                <EditDistanceBar key={s.section} metrics={s} />
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              {t(
                "No version history data yet. Quality metrics will appear after doctors review and finalize SOAP notes."
              )}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Language Breakdown */}
      {language === "all" &&
        Object.keys(metrics.by_language).length > 1 && (
          <Card>
            <CardHeader>
              <CardTitle>{t("Edit Rate by Language")}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {Object.entries(metrics.by_language).map(
                  ([lang, sections]) => (
                    <div key={lang}>
                      <div className="mb-3 flex items-center gap-2">
                        <Badge variant="outline">
                          {LANGUAGE_LABELS[lang] || lang}
                        </Badge>
                      </div>
                      <div className="space-y-3 pl-2">
                        {sections.map((s) => (
                          <EditDistanceBar
                            key={`${lang}-${s.section}`}
                            metrics={s}
                          />
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
