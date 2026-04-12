import { getExtracted } from "next-intl/server"

export default async function AdminUsersPage() {
  const t = await getExtracted()

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">{t("User Management")}</h1>
      <p className="text-muted-foreground">
        {t("User management interface coming soon.")}
      </p>
    </div>
  )
}
