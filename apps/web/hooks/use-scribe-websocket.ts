"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { useScribeStore } from "@/lib/stores/use-scribe-store"

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000"

interface UseScribeWebSocketOptions {
  consultationId: string
  token: string
}

export function useScribeWebSocket({
  consultationId,
  token,
}: UseScribeWebSocketOptions) {
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  const { setStatus, addTranscriptSegment, updateSOAPSection, setError } =
    useScribeStore()

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const ws = new WebSocket(
      `${WS_BASE}/ws/scribe/${consultationId}?token=${token}`,
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
            timestampStartMs: 0,
            timestampEndMs: 0,
          })
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

    ws.onclose = () => {
      setIsConnected(false)
    }

    ws.onerror = () => {
      setError("WebSocket connection error")
      setIsConnected(false)
    }
  }, [
    consultationId,
    token,
    setStatus,
    addTranscriptSegment,
    updateSOAPSection,
    setError,
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
        }),
      )
    },
    [],
  )

  const sendControl = useCallback(
    (type: "start" | "pause" | "resume" | "stop") => {
      if (wsRef.current?.readyState !== WebSocket.OPEN) return
      wsRef.current.send(JSON.stringify({ type }))
    },
    [],
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
