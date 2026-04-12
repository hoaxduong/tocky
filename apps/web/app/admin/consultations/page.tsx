import { getExtracted } from "next-intl/server"

export default async function AdminConsultationsPage() {
  const t = await getExtracted()

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">{t("All Consultations")}</h1>
      <p className="text-muted-foreground">
        {t("All consultations view coming soon.")}
      </p>
    </div>
  )
}
