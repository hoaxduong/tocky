"use client"

import { useElfiePatient } from "@/hooks/use-elfie"
import { useExtracted } from "next-intl"
import { Heart, Coins } from "lucide-react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@workspace/ui/components/card"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@workspace/ui/components/tabs"
import { Badge } from "@workspace/ui/components/badge"
import { Skeleton } from "@workspace/ui/components/skeleton"
import { ElfieVitalsTab } from "./elfie-vitals-tab"
import { ElfieMedicationsTab } from "./elfie-medications-tab"
import { ElfieLifestyleTab } from "./elfie-lifestyle-tab"
import { cn } from "@workspace/ui/lib/utils"

interface ElfiePatientCardProps {
  patientIdentifier: string | null
}

export function ElfiePatientCard({ patientIdentifier }: ElfiePatientCardProps) {
  const t = useExtracted()
  const { data, isLoading, isError } = useElfiePatient(patientIdentifier)

  if (!patientIdentifier) return null
  if (isError) return null
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-48" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-16 w-full" />
        </CardContent>
      </Card>
    )
  }
  if (!data) return null

  return (
    <Card className="border-l-4 border-l-teal-500" id="elfie-patient">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <Heart className="h-4 w-4 text-teal-600" />
            <span className="text-teal-700 dark:text-teal-400">Elfie</span>
            <span className="text-muted-foreground">—</span>
            {data.name}, {data.age}
          </CardTitle>
          <div className="flex items-center gap-1.5 shrink-0">
            <Badge
              variant="outline"
              className={cn(
                "text-xs tabular-nums",
                data.adherence_score >= 80
                  ? "border-emerald-500 text-emerald-700 dark:text-emerald-400"
                  : data.adherence_score >= 60
                    ? "border-amber-500 text-amber-700 dark:text-amber-400"
                    : "border-red-500 text-red-700 dark:text-red-400"
              )}
            >
              {data.adherence_score}%
            </Badge>
            <Badge variant="secondary" className="gap-1 text-xs">
              <Coins className="h-3 w-3" />
              {data.elfie_coins.toLocaleString()} · {data.tier}
            </Badge>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {data.conditions.map((c) => (
            <Badge key={c} variant="outline" className="text-xs">
              {c}
            </Badge>
          ))}
          <span className="text-[11px] text-muted-foreground ml-0.5">
            {t("since")} {new Date(data.member_since).toLocaleDateString()}
          </span>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <Tabs defaultValue="vitals">
          <TabsList>
            <TabsTrigger value="vitals">{t("Vitals")}</TabsTrigger>
            <TabsTrigger value="medications">{t("Medications")}</TabsTrigger>
            <TabsTrigger value="lifestyle">{t("Lifestyle")}</TabsTrigger>
          </TabsList>
          <TabsContent value="vitals" className="mt-2">
            <ElfieVitalsTab vitals={data.vitals} />
          </TabsContent>
          <TabsContent value="medications" className="mt-2">
            <ElfieMedicationsTab medications={data.medications} />
          </TabsContent>
          <TabsContent value="lifestyle" className="mt-2">
            <ElfieLifestyleTab lifestyle={data.lifestyle} />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
