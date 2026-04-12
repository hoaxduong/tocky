import { getExtracted } from "next-intl/server"
import { PageHeader } from "@/components/page-header"
import { AdminUsersTable } from "@/components/admin-users-table"

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
      <AdminUsersTable />
    </div>
  )
}
