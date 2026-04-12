"use client"

import { useExtracted } from "next-intl"
import { Plus } from "lucide-react"
import { Button } from "@workspace/ui/components/button"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@workspace/ui/components/card"
import { useConsultations } from "@/hooks/use-consultation"
import { ConsultationCard } from "@/components/scribe/consultation-card"
import Link from "next/link"

interface DashboardContentProps {
  userName: string | undefined
}

export function DashboardContent({ userName }: DashboardContentProps) {
  const t = useExtracted()
  const token = "" // TODO: get JWT token from session
  const { data } = useConsultations(token)

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{t("Welcome back")}</h1>
          <p className="text-muted-foreground">{userName}</p>
        </div>
        <Link href="/consultations/new">
          <Button className="gap-2">
            <Plus className="h-4 w-4" />
            {t("New Consultation")}
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">
              {t("Total Consultations")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{data?.total ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">
              {t("Active")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">
              {data?.items.filter((c) => c.status === "recording").length ?? 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">
              {t("Completed")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">
              {data?.items.filter((c) => c.status === "completed").length ?? 0}
            </p>
          </CardContent>
        </Card>
      </div>

      <div>
        <h2 className="mb-4 text-xl font-semibold">
          {t("Recent Consultations")}
        </h2>
        {data?.items.length === 0 ? (
          <p className="text-muted-foreground">
            {t("No consultations yet. Start your first one!")}
          </p>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {data?.items.slice(0, 6).map((c) => (
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
    </div>
  )
}
