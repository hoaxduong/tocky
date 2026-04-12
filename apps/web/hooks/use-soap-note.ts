"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"

interface SOAPNote {
  id: string
  consultation_id: string
  subjective: string
  objective: string
  assessment: string
  plan: string
  medical_entities: Record<string, string[]>
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
  is_draft?: boolean
}

export function useSOAPNote(consultationId: string) {
  return useQuery({
    queryKey: ["soap-note", consultationId],
    queryFn: () =>
      apiFetch<SOAPNote>(
        `/api/v1/consultations/${consultationId}/soap-note/`,
      ),
    enabled: !!consultationId,
  })
}

export function useUpdateSOAPNote(consultationId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (update: SOAPNoteUpdate) =>
      apiFetch<SOAPNote>(
        `/api/v1/consultations/${consultationId}/soap-note/`,
        {
          method: "PUT",
          body: JSON.stringify(update),
        },
      ),
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
        { method: "POST" },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["soap-note", consultationId],
      })
    },
  })
}
