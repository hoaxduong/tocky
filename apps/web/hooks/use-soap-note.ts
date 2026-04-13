"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"

export type SOAPSection = "subjective" | "objective" | "assessment" | "plan"

export type ReviewIssueType =
  | "symptom_diagnosis_mismatch"
  | "ambiguous_term"
  | "translation_uncertainty"
  | "missing_information"

export interface ReviewFlag {
  section: SOAPSection
  quoted_span: string
  issue_type: ReviewIssueType
  suggestion: string
  confidence: "low" | "medium" | "high"
}

export interface ICD10Code {
  code: string
  description: string
  description_en?: string
  diagnosis: string
  status: "suggested" | "confirmed" | "rejected"
}

interface SOAPNote {
  id: string
  consultation_id: string
  subjective: string
  objective: string
  assessment: string
  plan: string
  medical_entities: Record<string, string[]>
  review_flags: ReviewFlag[]
  icd10_codes: ICD10Code[]
  is_draft: boolean
  version: number
  created_at: string
  updated_at: string
}

interface SOAPNoteUpdate {
  subjective?: string
  objective?: string
  assessment?: string
  plan?: string
  icd10_codes?: ICD10Code[]
  is_draft?: boolean
}

export function useSOAPNote(consultationId: string) {
  return useQuery({
    queryKey: ["soap-note", consultationId],
    queryFn: () =>
      apiFetch<SOAPNote>(`/api/v1/consultations/${consultationId}/soap-note/`),
    enabled: !!consultationId,
  })
}

export function useUpdateSOAPNote(consultationId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (update: SOAPNoteUpdate) =>
      apiFetch<SOAPNote>(`/api/v1/consultations/${consultationId}/soap-note/`, {
        method: "PUT",
        body: JSON.stringify(update),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["soap-note", consultationId],
      })
    },
  })
}

export function useFinalizeSOAPNote(consultationId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch<SOAPNote>(
        `/api/v1/consultations/${consultationId}/soap-note/finalize`,
        { method: "POST" }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["soap-note", consultationId],
      })
      queryClient.invalidateQueries({
        queryKey: ["consultation-audio", consultationId],
      })
    },
  })
}

interface ConsultationAudio {
  url: string
  duration_ms: number
}

export function useConsultationAudio(consultationId: string, enabled: boolean) {
  return useQuery({
    queryKey: ["consultation-audio", consultationId],
    queryFn: () =>
      apiFetch<ConsultationAudio>(
        `/api/v1/consultations/${consultationId}/soap-note/audio`
      ),
    enabled: enabled && !!consultationId,
    staleTime: 30 * 60 * 1000,
  })
}

export interface TranscriptSegment {
  id: string
  sequence_number: number
  text: string
  language: string
  is_medically_relevant: boolean
  speaker_label: string | null
  timestamp_start_ms: number
  timestamp_end_ms: number
}

interface TranscriptResponse {
  consultation_id: string
  segments: TranscriptSegment[]
}

export function useTranscripts(consultationId: string, enabled = true) {
  return useQuery({
    queryKey: ["transcripts", consultationId],
    queryFn: () =>
      apiFetch<TranscriptResponse>(
        `/api/v1/consultations/${consultationId}/transcripts/`
      ),
    enabled: enabled && !!consultationId,
  })
}

export function useRegenerateSOAPNote(consultationId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch<SOAPNote>(
        `/api/v1/consultations/${consultationId}/soap-note/regenerate`,
        { method: "POST" }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["soap-note", consultationId],
      })
    },
  })
}

export function useResuggestICD10(consultationId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch<SOAPNote>(
        `/api/v1/consultations/${consultationId}/soap-note/suggest-icd10`,
        { method: "POST" }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["soap-note", consultationId],
      })
    },
  })
}

interface ICD10SearchResult {
  code: string
  description: string
  description_en: string
}

export function useICD10Search(query: string, lang = "en") {
  return useQuery({
    queryKey: ["icd10-search", query, lang],
    queryFn: () =>
      apiFetch<ICD10SearchResult[]>(
        `/api/v1/icd10/search?q=${encodeURIComponent(query)}&lang=${lang}&limit=10`
      ),
    enabled: query.length >= 2,
    staleTime: 5 * 60 * 1000,
  })
}
