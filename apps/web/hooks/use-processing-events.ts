"use client"

import { useEffect, useReducer, useRef, useCallback } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { fetchEventSource } from "@microsoft/fetch-event-source"

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface StreamedSegment {
  sequence: number
  text: string
  status:
    | "transcribed"
    | "classified"
    | "failed_transcription"
    | "failed_classification"
  isMedicallyRelevant: boolean
  errorMessage: string | null
  timestampStartMs: number
  timestampEndMs: number
  emotion: string | null
}

export interface ProcessingProgress {
  step: string
  progress: number
}

interface State {
  segments: Map<number, StreamedSegment>
  progress: ProcessingProgress
  terminalStatus: string | null
}

// ---------------------------------------------------------------------------
// Reducer — keeps all state updates batched and predictable
// ---------------------------------------------------------------------------

type Action =
  | { type: "transcript_segment"; data: Record<string, unknown> }
  | { type: "segment_classified"; data: Record<string, unknown> }
  | { type: "segment_failed"; data: Record<string, unknown> }
  | { type: "progress"; data: Record<string, unknown> }
  | { type: "status"; data: Record<string, unknown> }
  | { type: "reset" }

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "transcript_segment": {
      const d = action.data
      const next = new Map(state.segments)
      next.set(d.sequence as number, {
        sequence: d.sequence as number,
        text: d.text as string,
        status: "transcribed",
        isMedicallyRelevant: false,
        errorMessage: null,
        timestampStartMs: d.timestamp_start_ms as number,
        timestampEndMs: d.timestamp_end_ms as number,
        emotion: (d.emotion as string) ?? null,
      })
      return { ...state, segments: next }
    }
    case "segment_classified": {
      const d = action.data
      const next = new Map(state.segments)
      const seg = next.get(d.sequence as number)
      if (seg) {
        next.set(d.sequence as number, {
          ...seg,
          status: "classified",
          isMedicallyRelevant: d.is_medically_relevant as boolean,
        })
      }
      return { ...state, segments: next }
    }
    case "segment_failed": {
      const d = action.data
      const next = new Map(state.segments)
      const existing = next.get(d.sequence as number)
      next.set(d.sequence as number, {
        sequence: d.sequence as number,
        text: existing?.text ?? "",
        isMedicallyRelevant: existing?.isMedicallyRelevant ?? false,
        timestampStartMs: existing?.timestampStartMs ?? 0,
        timestampEndMs: existing?.timestampEndMs ?? 0,
        emotion: existing?.emotion ?? null,
        status:
          d.step === "transcription"
            ? "failed_transcription"
            : "failed_classification",
        errorMessage: d.error_message as string,
      })
      return { ...state, segments: next }
    }
    case "progress": {
      const d = action.data
      return {
        ...state,
        progress: {
          step: d.step as string,
          progress: d.progress as number,
        },
      }
    }
    case "status": {
      return { ...state, terminalStatus: action.data.status as string }
    }
    case "reset":
      return initialState()
    default:
      return state
  }
}

function initialState(): State {
  return {
    segments: new Map(),
    progress: { step: "", progress: 0 },
    terminalStatus: null,
  }
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useProcessingEvents(
  consultationId: string,
  enabled: boolean,
) {
  const [state, dispatch] = useReducer(reducer, undefined, initialState)
  const queryClient = useQueryClient()
  const ctrlRef = useRef<AbortController | null>(null)

  const reset = useCallback(() => dispatch({ type: "reset" }), [])

  useEffect(() => {
    if (!enabled || !consultationId) return

    const ctrl = new AbortController()
    ctrlRef.current = ctrl

    fetchEventSource(
      `${API_BASE}/api/v1/consultations/${consultationId}/events/`,
      {
        credentials: "include",
        signal: ctrl.signal,
        // Keep connection alive even when tab is hidden
        openWhenHidden: true,

        async onopen(response) {
          if (!response.ok) {
            // Non-retriable — stop retrying
            throw new Error(`SSE connection failed: ${response.status}`)
          }
        },

        onmessage(ev) {
          if (!ev.data) return
          try {
            const data = JSON.parse(ev.data) as Record<string, unknown>
            // ev.event is the SSE "event:" field; defaults to "" if absent
            const eventType = ev.event || "message"
            dispatch({ type: eventType as Action["type"], data })

            if (eventType === "status") {
              queryClient.invalidateQueries({
                queryKey: ["consultation", consultationId],
              })
              queryClient.invalidateQueries({
                queryKey: ["transcripts", consultationId],
              })
              queryClient.invalidateQueries({
                queryKey: ["soap-note", consultationId],
              })
            }
          } catch {
            // Ignore malformed events
          }
        },

        onerror(err) {
          // Log for debugging; returning nothing lets it retry
          console.warn("[SSE]", err)
        },
      },
    )

    return () => {
      ctrl.abort()
      ctrlRef.current = null
    }
  }, [consultationId, enabled, queryClient])

  return {
    segments: Array.from(state.segments.values()).sort(
      (a, b) => a.sequence - b.sequence,
    ),
    progress: state.progress,
    terminalStatus: state.terminalStatus,
    isConnected: enabled && !state.terminalStatus,
    reset,
  }
}
