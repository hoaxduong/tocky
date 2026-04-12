import { getExtracted } from "next-intl/server"
import { PageHeader } from "@/components/page-header"

export default async function AdminConsultationsPage() {
  const t = await getExtracted()

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("All Consultations")}
        breadcrumbs={[
          { label: t("Admin"), href: "/admin" },
          { label: t("Consultations") },
        ]}
      />
      <p className="text-muted-foreground">
        {t("All consultations view coming soon.")}
      </p>
    </div>
  )
}
