"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"

export interface Consultation {
  id: string
  user_id: string
  title: string
  patient_identifier: string | null
  language: string
  mode: string
  status: string
  processing_step: string | null
  processing_progress: number
  error_message: string | null
  started_at: string
  ended_at: string | null
  created_at: string
  updated_at: string
}

interface ConsultationListResponse {
  items: Consultation[]
  total: number
  offset: number
  limit: number
}

interface CreateConsultationInput {
  title?: string
  patient_identifier?: string | null
  language?: string
  mode?: string
}

export function useConsultations(offset = 0, limit = 20) {
  return useQuery({
    queryKey: ["consultations", offset, limit],
    queryFn: () =>
      apiFetch<ConsultationListResponse>(
        `/api/v1/consultations/?offset=${offset}&limit=${limit}`,
      ),
  })
}

export function useConsultation(
  id: string,
  options?: {
    refetchInterval?:
      | number
      | false
      | ((query: { state: { data: Consultation | undefined } }) => number | false)
  },
) {
  return useQuery({
    queryKey: ["consultation", id],
    queryFn: () =>
      apiFetch<Consultation>(`/api/v1/consultations/${id}`),
    enabled: !!id,
    refetchInterval: options?.refetchInterval,
  })
}

export function useCreateConsultation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: CreateConsultationInput) =>
      apiFetch<Consultation>("/api/v1/consultations/", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["consultations"] })
    },
  })
}

export function useDeleteConsultation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<void>(`/api/v1/consultations/${id}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["consultations"] })
    },
  })
}

export function useUploadAudio() {
  const queryClient = useQueryClient()
  const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
  return useMutation({
    mutationFn: async ({
      consultationId,
      file,
    }: {
      consultationId: string
      file: File
    }) => {
      const formData = new FormData()
      formData.append("file", file)

      const res = await fetch(
        `${API_BASE}/api/v1/consultations/${consultationId}/upload-audio`,
        {
          method: "POST",
          credentials: "include",
          body: formData,
        },
      )
      if (!res.ok) {
        throw new Error(await res.text())
      }
      return res.json() as Promise<Consultation>
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["consultations"] })
    },
  })
}
