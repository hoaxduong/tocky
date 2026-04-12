"use client"

import { useExtracted } from "next-intl"
import { Plus } from "lucide-react"
import { Button } from "@workspace/ui/components/button"
import { useConsultations } from "@/hooks/use-consultation"
import { ConsultationCard } from "@/components/scribe/consultation-card"
import { ConsultationGridSkeleton } from "@/components/skeletons"
import { PageHeader } from "@/components/page-header"
import Link from "next/link"

export function ConsultationsList() {
  const t = useExtracted()
  const token = "" // TODO: get JWT token from session
  const { data, isLoading } = useConsultations(token)

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("Consultations")}
        breadcrumbs={[
          { label: t("Dashboard"), href: "/dashboard" },
          { label: t("Consultations") },
        ]}
        actions={
          <Link href="/consultations/new">
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              {t("New Consultation")}
            </Button>
          </Link>
        }
      />

      {isLoading ? (
        <ConsultationGridSkeleton />
      ) : data?.items.length === 0 ? (
        <p className="text-muted-foreground">
          {t("No consultations yet. Start your first one!")}
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {data?.items.map((c) => (
            <ConsultationCard
              key={c.id}
              id={c.id}
              title={c.title}
              language={c.language}
              status={c.status}
              createdAt={c.created_at}
            />
          ))}
        </div>
      )}
    </div>
  )
}
