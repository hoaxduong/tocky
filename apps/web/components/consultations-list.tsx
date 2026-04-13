"use client"

import { useState } from "react"
import { useExtracted } from "next-intl"
import { useConsultations } from "@/hooks/use-consultation"
import { ConsultationCard } from "@/components/scribe/consultation-card"
import { ConsultationGridSkeleton } from "@/components/skeletons"
import { PageHeader } from "@/components/page-header"
import { NewConsultationDialog } from "@/components/new-consultation-dialog"
import { Tabs, TabsList, TabsTrigger } from "@workspace/ui/components/tabs"

export function ConsultationsList() {
  const t = useExtracted()
  const [tab, setTab] = useState<"active" | "archived">("active")
  const { data, isLoading } = useConsultations(
    0,
    50,
    tab === "archived" ? "archived" : undefined
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("Consultations")}
        breadcrumbs={[
          { label: t("Dashboard"), href: "/dashboard" },
          { label: t("Consultations") },
        ]}
        actions={<NewConsultationDialog />}
      />

      <Tabs
        value={tab}
        onValueChange={(v) => setTab(v as "active" | "archived")}
      >
        <TabsList>
          <TabsTrigger value="active">{t("Active")}</TabsTrigger>
          <TabsTrigger value="archived">{t("Archived")}</TabsTrigger>
        </TabsList>
      </Tabs>

      {isLoading ? (
        <ConsultationGridSkeleton />
      ) : data?.items.length === 0 ? (
        <p className="text-muted-foreground">
          {tab === "archived"
            ? t("No archived consultations.")
            : t("No consultations yet. Start your first one!")}
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
