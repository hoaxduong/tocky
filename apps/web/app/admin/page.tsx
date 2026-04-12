import { getExtracted } from "next-intl/server"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@workspace/ui/components/card"
import { PageHeader } from "@/components/page-header"

export default async function AdminDashboardPage() {
  const t = await getExtracted()

  return (
    <div className="space-y-6">
      <PageHeader title={t("System Statistics")} />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">
              {t("Total Consultations")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">-</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">
              {t("Active Now")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">-</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">
              {t("Total Users")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">-</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
