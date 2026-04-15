"use client"

import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"

export interface SOAPNoteVersion {
  id: string
  soap_note_id: string
  version: number
  subjective: string
  objective: string
  assessment: string
  plan: string
  medical_entities: Record<string, string[]>
  icd10_codes: Array<Record<string, string>>
  review_flags: Array<Record<string, string>>
  is_draft: boolean
  source: string
  edited_by: string | null
  created_at: string
}

interface SOAPNoteVersionListResponse {
  items: SOAPNoteVersion[]
  total: number
}

export function useSOAPVersions(consultationId: string, enabled = true) {
  return useQuery({
    queryKey: ["soap-versions", consultationId],
    queryFn: () =>
      apiFetch<SOAPNoteVersionListResponse>(
        `/api/v1/consultations/${consultationId}/soap-note/versions`
      ),
    enabled: enabled && !!consultationId,
  })
}
