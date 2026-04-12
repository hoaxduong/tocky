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
  onAudioChunk: (chunk: string, sequence: number, timestampMs: number) => void,
): UseAudioRecorderReturn {
  const [isRecording, setIsRecording] = useState(false)
  const [audioLevel, setAudioLevel] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const mediaStreamRef = useRef<MediaStream | null>(null)
  const processorRef = useRef<ScriptProcessorNode | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const sequenceRef = useRef(0)
  const startTimeRef = useRef(0)
  const bufferRef = useRef<Float32Array[]>([])
  const isPausedRef = useRef(false)

  const flushBuffer = useCallback(() => {
    if (bufferRef.current.length === 0) return

    const totalLength = bufferRef.current.reduce(
      (sum, buf) => sum + buf.length,
      0,
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

      const source = audioContext.createMediaStreamSource(stream)
      // Use ScriptProcessor for broad compatibility
      const processor = audioContext.createScriptProcessor(4096, 1, 1)
      processorRef.current = processor

      sequenceRef.current = 0
      startTimeRef.current = Date.now()
      bufferRef.current = []

      let chunkCount = 0

      processor.onaudioprocess = (event) => {
        if (isPausedRef.current) return

        const inputData = event.inputBuffer.getChannelData(0)

        // Calculate audio level (RMS)
        let sum = 0
        for (let i = 0; i < inputData.length; i++) {
          sum += inputData[i]! * inputData[i]!
        }
        setAudioLevel(Math.sqrt(sum / inputData.length))

        bufferRef.current.push(new Float32Array(inputData))
        chunkCount++

        // Flush every ~250ms (4096 samples at 16kHz ≈ 256ms)
        if (chunkCount >= 1) {
          flushBuffer()
          chunkCount = 0
        }
      }

      source.connect(processor)
      processor.connect(audioContext.destination)

      setIsRecording(true)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to access microphone",
      )
    }
  }, [flushBuffer])

  const stopRecording = useCallback(() => {
    flushBuffer()

    processorRef.current?.disconnect()
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop())
    audioContextRef.current?.close()

    processorRef.current = null
    mediaStreamRef.current = null
    audioContextRef.current = null
    isPausedRef.current = false

    setIsRecording(false)
    setAudioLevel(0)
  }, [flushBuffer])

  const pauseRecording = useCallback(() => {
    isPausedRef.current = true
  }, [])

  const resumeRecording = useCallback(() => {
    isPausedRef.current = false
  }, [])

  useEffect(() => {
    return () => {
      processorRef.current?.disconnect()
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
