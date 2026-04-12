import { getExtracted } from "next-intl/server"
import { PageHeader } from "@/components/page-header"

export default async function AdminUsersPage() {
  const t = await getExtracted()

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("User Management")}
        breadcrumbs={[
          { label: t("Admin"), href: "/admin" },
          { label: t("Users") },
        ]}
      />
      <p className="text-muted-foreground">
        {t("User management interface coming soon.")}
      </p>
    </div>
  )
}
