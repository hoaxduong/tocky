"use client"

import React from "react"
import { ArrowLeft, Calendar, Clock, Mic, Upload, User } from "lucide-react"
import { useExtracted } from "next-intl"
import Link from "next/link"
import { Button } from "@workspace/ui/components/button"
import { Badge } from "@workspace/ui/components/badge"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@workspace/ui/components/breadcrumb"
import { StatusBadge } from "@/components/status-badge"
import type { Consultation } from "@/hooks/use-consultation"

interface BreadcrumbEntry {
  label: string
  href?: string
}

interface ConsultationContextBarProps {
  consultation: Pick<
    Consultation,
    | "title"
    | "patient_identifier"
    | "language"
    | "mode"
    | "status"
    | "started_at"
    | "ended_at"
    | "created_at"
  >
  /** Override status (e.g. from scribe store) */
  statusOverride?: string
  /** Override elapsed time display (e.g. from scribe store timer) */
  elapsedMs?: number
  /** Audio duration in ms (used when elapsedMs not available) */
  audioDurationMs?: number
  backHref?: string
  breadcrumbs?: BreadcrumbEntry[]
  actions?: React.ReactNode
}

function formatDuration(ms: number): string {
  const total = Math.floor(ms / 1000)
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`
}

function computeDurationMs(
  startedAt: string | null,
  endedAt: string | null,
): number | null {
  if (!startedAt || !endedAt) return null
  const diff = new Date(endedAt).getTime() - new Date(startedAt).getTime()
  return diff > 0 ? diff : null
}

export function ConsultationContextBar({
  consultation,
  statusOverride,
  elapsedMs,
  audioDurationMs,
  backHref,
  breadcrumbs,
  actions,
}: ConsultationContextBarProps) {
  const t = useExtracted()

  const status = statusOverride ?? consultation.status
  const durationMs =
    elapsedMs ??
    audioDurationMs ??
    computeDurationMs(consultation.started_at, consultation.ended_at)

  return (
    <div className="space-y-2">
      {breadcrumbs && breadcrumbs.length > 0 && (
        <Breadcrumb>
          <BreadcrumbList>
            {breadcrumbs.map((crumb, i) => (
              <React.Fragment key={crumb.label}>
                {i > 0 && <BreadcrumbSeparator />}
                <BreadcrumbItem>
                  {crumb.href ? (
                    <BreadcrumbLink asChild>
                      <Link href={crumb.href}>{crumb.label}</Link>
                    </BreadcrumbLink>
                  ) : (
                    <BreadcrumbPage>{crumb.label}</BreadcrumbPage>
                  )}
                </BreadcrumbItem>
              </React.Fragment>
            ))}
          </BreadcrumbList>
        </Breadcrumb>
      )}

      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 space-y-1.5">
          <div className="flex items-center gap-3">
            {backHref && (
              <Button variant="ghost" size="icon-sm" asChild>
                <Link href={backHref}>
                  <ArrowLeft className="h-4 w-4" />
                </Link>
              </Button>
            )}
            <h1 className="truncate text-2xl font-semibold tracking-tight">
              {consultation.title || t("New Consultation")}
            </h1>
            <StatusBadge status={status} />
          </div>

          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
            {consultation.patient_identifier && (
              <span className="flex items-center gap-1">
                <User className="h-3.5 w-3.5" />
                {consultation.patient_identifier}
              </span>
            )}
            <Badge variant="outline" className="text-xs">
              {consultation.language}
            </Badge>
            <span className="flex items-center gap-1 capitalize">
              {consultation.mode === "upload" ? (
                <Upload className="h-3.5 w-3.5" />
              ) : (
                <Mic className="h-3.5 w-3.5" />
              )}
              {consultation.mode === "upload" ? t("Upload") : t("Live")}
            </span>
            <span className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5" />
              {new Date(
                consultation.started_at || consultation.created_at,
              ).toLocaleDateString()}
            </span>
            {durationMs != null && durationMs > 0 && (
              <span className="flex items-center gap-1 font-mono tabular-nums">
                <Clock className="h-3.5 w-3.5" />
                {formatDuration(durationMs)}
              </span>
            )}
          </div>
        </div>

        {actions && (
          <div className="flex shrink-0 items-center gap-2">{actions}</div>
        )}
      </div>
    </div>
  )
}
