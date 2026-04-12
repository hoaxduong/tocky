"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"

interface Consultation {
  id: string
  user_id: string
  title: string
  patient_identifier: string | null
  language: string
  status: string
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
}

export function useConsultations(token: string, offset = 0, limit = 20) {
  return useQuery({
    queryKey: ["consultations", offset, limit],
    queryFn: () =>
      apiFetch<ConsultationListResponse>(
        `/api/v1/consultations/?offset=${offset}&limit=${limit}`,
        { token },
      ),
  })
}

export function useConsultation(token: string, id: string) {
  return useQuery({
    queryKey: ["consultation", id],
    queryFn: () =>
      apiFetch<Consultation>(`/api/v1/consultations/${id}`, { token }),
    enabled: !!id,
  })
}

export function useCreateConsultation(token: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: CreateConsultationInput) =>
      apiFetch<Consultation>("/api/v1/consultations/", {
        method: "POST",
        body: JSON.stringify(input),
        token,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["consultations"] })
    },
  })
}

export function useDeleteConsultation(token: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<void>(`/api/v1/consultations/${id}`, {
        method: "DELETE",
        token,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["consultations"] })
    },
  })
}
