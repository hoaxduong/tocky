"use client"

import { useCallback, useEffect, useRef, useState } from "react"

interface UseAudioRecorderReturn {
  isRecording: boolean
  startRecording: () => Promise<void>
  stopRecording: () => void
  pauseRecording: () => void
  resumeRecording: () => void
  audioLevel: number
  error: string | null
}

export function useAudioRecorder(
  onAudioChunk: (chunk: string, sequence: number, timestampMs: number) => void
): UseAudioRecorderReturn {
  const [isRecording, setIsRecording] = useState(false)
  const [audioLevel, setAudioLevel] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const mediaStreamRef = useRef<MediaStream | null>(null)
  const workletNodeRef = useRef<AudioWorkletNode | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const sequenceRef = useRef(0)
  const startTimeRef = useRef(0)
  const bufferRef = useRef<Float32Array[]>([])

  const flushBuffer = useCallback(() => {
    if (bufferRef.current.length === 0) return

    const totalLength = bufferRef.current.reduce(
      (sum, buf) => sum + buf.length,
      0
    )
    const merged = new Float32Array(totalLength)
    let offset = 0
    for (const buf of bufferRef.current) {
      merged.set(buf, offset)
      offset += buf.length
    }
    bufferRef.current = []

    // Convert Float32 to Int16 PCM
    const int16 = new Int16Array(merged.length)
    for (let i = 0; i < merged.length; i++) {
      const s = Math.max(-1, Math.min(1, merged[i]!))
      int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff
    }

    // Base64 encode
    const bytes = new Uint8Array(int16.buffer)
    let binary = ""
    for (let i = 0; i < bytes.length; i++) {
      binary += String.fromCharCode(bytes[i]!)
    }
    const base64 = btoa(binary)

    sequenceRef.current += 1
    const timestampMs = Date.now() - startTimeRef.current

    onAudioChunk(base64, sequenceRef.current, timestampMs)
  }, [onAudioChunk])

  const startRecording = useCallback(async () => {
    try {
      setError(null)
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      })

      mediaStreamRef.current = stream
      const audioContext = new AudioContext({ sampleRate: 16000 })
      audioContextRef.current = audioContext

      await audioContext.audioWorklet.addModule("/audio-worklet-processor.js")

      const source = audioContext.createMediaStreamSource(stream)
      const workletNode = new AudioWorkletNode(audioContext, "pcm-processor")
      workletNodeRef.current = workletNode

      sequenceRef.current = 0
      startTimeRef.current = Date.now()
      bufferRef.current = []

      let sampleCount = 0
      // Flush every ~250ms worth of samples (16kHz * 0.25s = 4000 samples)
      const flushThreshold = 4000

      workletNode.port.onmessage = (event) => {
        if (event.data.type !== "audio") return

        const samples: Float32Array = event.data.samples

        // Calculate audio level (RMS)
        let sum = 0
        for (let i = 0; i < samples.length; i++) {
          sum += samples[i]! * samples[i]!
        }
        setAudioLevel(Math.sqrt(sum / samples.length))

        bufferRef.current.push(new Float32Array(samples))
        sampleCount += samples.length

        if (sampleCount >= flushThreshold) {
          flushBuffer()
          sampleCount = 0
        }
      }

      source.connect(workletNode)
      workletNode.connect(audioContext.destination)

      setIsRecording(true)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to access microphone"
      )
    }
  }, [flushBuffer])

  const stopRecording = useCallback(() => {
    flushBuffer()

    workletNodeRef.current?.disconnect()
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop())
    audioContextRef.current?.close()

    workletNodeRef.current = null
    mediaStreamRef.current = null
    audioContextRef.current = null

    setIsRecording(false)
    setAudioLevel(0)
  }, [flushBuffer])

  const pauseRecording = useCallback(() => {
    workletNodeRef.current?.port.postMessage({ type: "pause" })
  }, [])

  const resumeRecording = useCallback(() => {
    workletNodeRef.current?.port.postMessage({ type: "resume" })
  }, [])

  useEffect(() => {
    return () => {
      workletNodeRef.current?.disconnect()
      mediaStreamRef.current?.getTracks().forEach((track) => track.stop())
      audioContextRef.current?.close()
    }
  }, [])

  return {
    isRecording,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    audioLevel,
    error,
  }
}
