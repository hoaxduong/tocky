"use client"

import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"

export interface SectionEditMetrics {
  section: string
  avg_edit_distance: number
  pct_edited: number
  total_compared: number
}

export interface QualityMetricsResponse {
  overall_edit_rate: number
  total_finalized: number
  total_with_history: number
  by_section: SectionEditMetrics[]
  by_language: Record<string, SectionEditMetrics[]>
  period_start: string | null
  period_end: string | null
}

export function useQualityMetrics(params?: {
  language?: string
  date_from?: string
  date_to?: string
}) {
  const searchParams = new URLSearchParams()
  if (params?.language) searchParams.set("language", params.language)
  if (params?.date_from) searchParams.set("date_from", params.date_from)
  if (params?.date_to) searchParams.set("date_to", params.date_to)
  const qs = searchParams.toString()

  return useQuery({
    queryKey: ["admin-quality-metrics", params],
    queryFn: () =>
      apiFetch<QualityMetricsResponse>(
        `/api/v1/admin/quality-metrics${qs ? `?${qs}` : ""}`
      ),
  })
}

export interface FlagTypeStats {
  issue_type: string
  total: number
  accepted: number
  dismissed: number
  acceptance_rate: number
}

export interface FlagStatsResponse {
  total_flags: number
  total_feedback: number
  by_issue_type: FlagTypeStats[]
  by_section: FlagTypeStats[]
}

export function useFlagStats() {
  return useQuery({
    queryKey: ["admin-flag-stats"],
    queryFn: () => apiFetch<FlagStatsResponse>("/api/v1/admin/flag-stats"),
  })
}

export function getTrainingDataExportUrl(params?: {
  language?: string
  date_from?: string
  date_to?: string
}) {
  const base =
    (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000") +
    "/api/v1/admin/export-training-data"
  const searchParams = new URLSearchParams()
  if (params?.language) searchParams.set("language", params.language)
  if (params?.date_from) searchParams.set("date_from", params.date_from)
  if (params?.date_to) searchParams.set("date_to", params.date_to)
  const qs = searchParams.toString()
  return `${base}${qs ? `?${qs}` : ""}`
}
