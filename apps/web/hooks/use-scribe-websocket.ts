"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { useScribeStore } from "@/lib/stores/use-scribe-store"

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000"

interface UseScribeWebSocketOptions {
  consultationId: string
}

export function useScribeWebSocket({
  consultationId,
}: UseScribeWebSocketOptions) {
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  const {
    setStatus,
    addTranscriptSegment,
    updateSOAPSection,
    setError,
    updateMetadata,
  } = useScribeStore()

  const connect = useCallback(async () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    // Fetch a short-lived token via the same-origin rewrite (cookies are sent),
    // then pass it as a query param to the cross-origin WebSocket.
    let tokenParam = ""
    try {
      const res = await fetch("/api/v1/auth/ws-ticket", {
        method: "POST",
        credentials: "include",
      })
      if (res.ok) {
        const { token } = await res.json()
        tokenParam = `?token=${encodeURIComponent(token)}`
      }
    } catch {
      // Fall back to connecting without token (will rely on cookie if same-origin)
    }

    const ws = new WebSocket(
      `${WS_BASE}/ws/scribe/${consultationId}${tokenParam}`
    )
    wsRef.current = ws

    ws.onopen = () => {
      setIsConnected(true)
      setStatus("ready")
    }

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)

      switch (msg.type) {
        case "transcript":
          addTranscriptSegment({
            text: msg.text,
            isMedicallyRelevant: msg.is_medically_relevant,
            speakerLabel: msg.speaker_label,
            sequence: msg.sequence,
            timestampStartMs: msg.timestamp_start_ms ?? 0,
            timestampEndMs: msg.timestamp_end_ms ?? 0,
            emotion: msg.emotion ?? null,
          })
          break

        case "metadata_update":
          updateMetadata(
            msg.title,
            msg.patient_identifier ?? null,
            msg.language ?? null,
          )
          break

        case "soap_update":
          updateSOAPSection(msg.section, msg.content)
          break

        case "status":
          setStatus(msg.status)
          break

        case "error":
          setError(msg.message)
          break
      }
    }

    ws.onclose = (event) => {
      setIsConnected(false)
      const currentStatus = useScribeStore.getState().status
      // If WebSocket closes while processing, the server has already
      // persisted data — transition to completed so the UI isn't stuck.
      if (currentStatus === "processing") {
        setStatus("completed")
      } else if (
        !event.wasClean &&
        currentStatus === "recording"
      ) {
        setError("Connection lost. Your data has been saved.")
        setStatus("completed")
      }
    }

    ws.onerror = () => {
      setError("WebSocket connection error")
      setIsConnected(false)
    }
  }, [
    consultationId,
    setStatus,
    addTranscriptSegment,
    updateSOAPSection,
    setError,
    updateMetadata,
  ])

  const disconnect = useCallback(() => {
    wsRef.current?.close()
    wsRef.current = null
    setIsConnected(false)
  }, [])

  const sendAudioChunk = useCallback(
    (data: string, sequence: number, timestampMs: number) => {
      if (wsRef.current?.readyState !== WebSocket.OPEN) return
      wsRef.current.send(
        JSON.stringify({
          type: "audio_chunk",
          data,
          sequence,
          timestamp_ms: timestampMs,
        })
      )
    },
    []
  )

  const sendControl = useCallback(
    (type: "start" | "pause" | "resume" | "stop") => {
      if (wsRef.current?.readyState !== WebSocket.OPEN) return
      wsRef.current.send(JSON.stringify({ type }))
    },
    []
  )

  useEffect(() => {
    return () => {
      wsRef.current?.close()
    }
  }, [])

  return {
    isConnected,
    connect,
    disconnect,
    sendAudioChunk,
    sendControl,
  }
}
