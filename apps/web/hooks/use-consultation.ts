"use client"

import { useEffect, useState } from "react"
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
  chunks_total: number
  chunks_completed: number
  soap_generated: boolean
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

export function useConsultations(
  offset = 0,
  limit = 20,
  statusFilter?: string
) {
  const params = new URLSearchParams({
    offset: String(offset),
    limit: String(limit),
  })
  if (statusFilter) params.set("status_filter", statusFilter)
  return useQuery({
    queryKey: ["consultations", offset, limit, statusFilter],
    queryFn: () =>
      apiFetch<ConsultationListResponse>(
        `/api/v1/consultations/?${params.toString()}`
      ),
  })
}

export function useConsultation(
  id: string,
  options?: {
    refetchInterval?:
      | number
      | false
      | ((query: {
          state: { data: Consultation | undefined }
        }) => number | false)
  }
) {
  return useQuery({
    queryKey: ["consultation", id],
    queryFn: () => apiFetch<Consultation>(`/api/v1/consultations/${id}`),
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

interface UpdateConsultationInput {
  title?: string
  patient_identifier?: string | null
  language?: string
}

export function useUpdateConsultation(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: UpdateConsultationInput) =>
      apiFetch<Consultation>(`/api/v1/consultations/${id}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["consultation", id] })
      queryClient.invalidateQueries({ queryKey: ["consultations"] })
    },
  })
}

export function useArchiveConsultation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<Consultation>(`/api/v1/consultations/${id}/archive`, {
        method: "POST",
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

export function useResumeProcessing() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (consultationId: string) =>
      apiFetch<Consultation>(`/api/v1/consultations/${consultationId}/resume`, {
        method: "POST",
      }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["consultation", data.id] })
      queryClient.invalidateQueries({ queryKey: ["consultations"] })
    },
  })
}

export type ConsultationEvent =
  | {
      type: "snapshot"
      status: string
      step: string | null
      progress: number
      chunks_total: number
      chunks_completed: number
      error: string | null
    }
  | {
      type: "progress"
      step?: string
      progress?: number
      chunks_completed?: number
      chunks_total?: number
      latest_sequence?: number
    }
  | {
      type: "status"
      status: string
      step?: string | null
      progress?: number
      error?: string | null
    }

/**
 * Subscribe to the server-sent events stream for a consultation's batch
 * processing run. Lifecycle is tied to the provided ``enabled`` flag; when it
 * flips false or the component unmounts the EventSource is closed cleanly.
 *
 * On progress/status events we invalidate the cached consultation so any
 * component using ``useConsultation`` re-renders with fresh fields.
 */
export function useConsultationStream(
  consultationId: string,
  enabled: boolean
) {
  const queryClient = useQueryClient()
  const [lastEvent, setLastEvent] = useState<ConsultationEvent | null>(null)

  useEffect(() => {
    if (!enabled || !consultationId) return

    const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
    const url = `${API_BASE}/api/v1/consultations/${consultationId}/events`
    const source = new EventSource(url, { withCredentials: true })

    source.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data) as ConsultationEvent
        setLastEvent(event)

        // Refresh cached consultation whenever server-side state advances.
        if (
          event.type === "progress" ||
          event.type === "status" ||
          event.type === "snapshot"
        ) {
          queryClient.invalidateQueries({
            queryKey: ["consultation", consultationId],
          })
        }
        // When processing finishes, refresh transcripts + SOAP cache.
        if (event.type === "status" && event.status === "completed") {
          queryClient.invalidateQueries({
            queryKey: ["transcripts", consultationId],
          })
          queryClient.invalidateQueries({
            queryKey: ["soap-note", consultationId],
          })
          source.close()
        }
        if (event.type === "status" && event.status === "failed") {
          source.close()
        }
      } catch {
        // Ignore malformed events; stream may contain heartbeats later.
      }
    }

    source.onerror = () => {
      // Browser auto-reconnects; nothing to do beyond logging.
    }

    return () => {
      source.close()
    }
  }, [consultationId, enabled, queryClient])

  return { lastEvent }
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
        }
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
