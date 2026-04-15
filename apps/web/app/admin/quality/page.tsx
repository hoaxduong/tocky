import { getExtracted } from "next-intl/server"

import { PageHeader } from "@/components/page-header"
import { QualityDashboard } from "@/components/admin-quality-dashboard"

export default async function QualityPage() {
  const t = await getExtracted()

  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title={t("Quality Metrics")}
        description={t(
          "Measure AI accuracy by comparing AI-generated SOAP notes against doctor corrections."
        )}
        breadcrumbs={[
          { label: t("Admin"), href: "/admin" },
          { label: t("Quality Metrics") },
        ]}
      />
      <QualityDashboard />
    </div>
  )
}
