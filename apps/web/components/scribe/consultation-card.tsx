"use client"

import { useExtracted } from "next-intl"
import { ChevronRight } from "lucide-react"
import { Badge } from "@workspace/ui/components/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@workspace/ui/components/card"
import { StatusBadge } from "@/components/status-badge"
import Link from "next/link"

interface ConsultationCardProps {
  id: string
  title: string
  language: string
  status: string
  createdAt: string
}

export function ConsultationCard({
  id,
  title,
  language,
  status,
  createdAt,
}: ConsultationCardProps) {
  const t = useExtracted()

  return (
    <Link href={`/consultations/${id}`}>
      <Card className="group cursor-pointer transition-all hover:border-primary/30 hover:shadow-sm">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">
              {title || t("New Consultation")}
            </CardTitle>
            <div className="flex items-center gap-2">
              <StatusBadge status={status} />
              <ChevronRight className="text-muted-foreground h-4 w-4 opacity-0 transition-opacity group-hover:opacity-100" />
            </div>
          </div>
          <CardDescription>
            {new Date(createdAt).toLocaleDateString()}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Badge variant="outline">{language}</Badge>
        </CardContent>
      </Card>
    </Link>
  )
}
