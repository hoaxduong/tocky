"use client"

import Link from "next/link"
import { useExtracted } from "next-intl"
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Loader2,
  Stethoscope,
} from "lucide-react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@workspace/ui/components/card"
import { useConsultations } from "@/hooks/use-consultation"
import { ConsultationCard } from "@/components/scribe/consultation-card"
import {
  ConsultationGridSkeleton,
  StatsGridSkeleton,
} from "@/components/skeletons"
import { PageHeader } from "@/components/page-header"
import { NewConsultationDialog } from "@/components/new-consultation-dialog"
import { EmptyState } from "@/components/empty-state"
import { useSession } from "@/hooks/use-auth"

export function DashboardContent() {
  const t = useExtracted()
  const { data: session } = useSession()
  const { data, isLoading } = useConsultations()
  const userName = session?.user?.name

  const items = data?.items ?? []
  const processingCount = items.filter(
    (c) => c.status === "processing" || c.status === "uploading"
  ).length
  const completedCount = items.filter(
    (c) => c.status === "completed"
  ).length
  const needsAttentionCount = items.filter(
    (c) => c.status === "failed" || c.status === "completed_with_errors"
  ).length

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("Welcome back")}
        description={userName}
        actions={<NewConsultationDialog />}
      />

      {isLoading ? (
        <StatsGridSkeleton />
      ) : (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">
                {t("Total")}
              </CardTitle>
              <Stethoscope className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">{data?.total ?? 0}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">
                {t("Processing")}
              </CardTitle>
              <Loader2 className="h-4 w-4 text-amber-500" />
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">{processingCount}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">
                {t("Completed")}
              </CardTitle>
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">{completedCount}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">
                {t("Needs Attention")}
              </CardTitle>
              <AlertTriangle className="h-4 w-4 text-destructive" />
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">{needsAttentionCount}</p>
            </CardContent>
          </Card>
        </div>
      )}

      <div>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold">
            {t("Recent Consultations")}
          </h2>
          {items.length > 0 && (
            <Link
              href="/consultations"
              className="flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              {t("View All")}
              <ChevronRight className="h-4 w-4" />
            </Link>
          )}
        </div>
        {isLoading ? (
          <ConsultationGridSkeleton />
        ) : items.length === 0 ? (
          <EmptyState
            icon={Stethoscope}
            title={t("No consultations yet")}
            description={t(
              "Start your first consultation to begin documenting patient encounters."
            )}
            action={<NewConsultationDialog />}
          />
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {items.slice(0, 6).map((c) => (
              <ConsultationCard
                key={c.id}
                id={c.id}
                title={c.title}
                language={c.language}
                status={c.status}
                createdAt={c.created_at}
                patientIdentifier={c.patient_identifier}
                mode={c.mode}
                processingProgress={c.processing_progress}
                processingStep={c.processing_step}
                errorMessage={c.error_message}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
