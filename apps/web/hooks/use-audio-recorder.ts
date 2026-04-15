"use client"

import { useCallback, useEffect, useRef, useState } from "react"

type AudioWarningType = "clipping" | "low_volume" | "silence" | null

interface UseAudioRecorderReturn {
  isRecording: boolean
  startRecording: () => Promise<void>
  stopRecording: () => void
  pauseRecording: () => void
  resumeRecording: () => void
  audioLevel: number
  audioWarning: AudioWarningType
  error: string | null
}

// Audio quality thresholds
const CLIPPING_THRESHOLD = 0.95
const LOW_VOLUME_THRESHOLD = 0.02
const SILENCE_THRESHOLD = 0.01
// ~10 seconds of silence at 250ms per frame
const SILENCE_FRAME_LIMIT = 40
// Debounce: require N consecutive frames before showing/clearing a warning
const WARNING_ONSET_FRAMES = 8 // ~2s to show warning
const WARNING_CLEAR_FRAMES = 12 // ~3s of normal audio to clear

export function useAudioRecorder(
  onAudioChunk: (chunk: string, sequence: number, timestampMs: number) => void
): UseAudioRecorderReturn {
  const [isRecording, setIsRecording] = useState(false)
  const [audioLevel, setAudioLevel] = useState(0)
  const [audioWarning, setAudioWarning] = useState<AudioWarningType>(null)
  const [error, setError] = useState<string | null>(null)

  const mediaStreamRef = useRef<MediaStream | null>(null)
  const workletNodeRef = useRef<AudioWorkletNode | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const sequenceRef = useRef(0)
  const startTimeRef = useRef(0)
  const bufferRef = useRef<Float32Array[]>([])
  const silenceFrameCountRef = useRef(0)
  const pendingWarningRef = useRef<AudioWarningType>(null)
  const pendingWarningCountRef = useRef(0)
  const clearCountRef = useRef(0)

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
      setAudioWarning(null)
      silenceFrameCountRef.current = 0
      pendingWarningRef.current = null
      pendingWarningCountRef.current = 0
      clearCountRef.current = 0

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
        const rms = Math.sqrt(sum / samples.length)
        setAudioLevel(rms)

        // Audio quality checks
        // Clipping detection: any sample near max amplitude
        let hasClipping = false
        for (let i = 0; i < samples.length; i++) {
          if (Math.abs(samples[i]!) > CLIPPING_THRESHOLD) {
            hasClipping = true
            break
          }
        }

        // Determine what warning this frame would produce
        let frameWarning: AudioWarningType = null
        if (hasClipping) {
          frameWarning = "clipping"
          silenceFrameCountRef.current = 0
        } else if (rms < SILENCE_THRESHOLD) {
          silenceFrameCountRef.current += 1
          if (silenceFrameCountRef.current >= SILENCE_FRAME_LIMIT) {
            frameWarning = "silence"
          }
        } else if (rms < LOW_VOLUME_THRESHOLD) {
          frameWarning = "low_volume"
          silenceFrameCountRef.current = 0
        } else {
          silenceFrameCountRef.current = 0
        }

        // Debounce: only update the displayed warning after consistent frames
        if (frameWarning !== null) {
          clearCountRef.current = 0
          if (frameWarning === pendingWarningRef.current) {
            pendingWarningCountRef.current += 1
          } else {
            pendingWarningRef.current = frameWarning
            pendingWarningCountRef.current = 1
          }
          if (pendingWarningCountRef.current >= WARNING_ONSET_FRAMES) {
            setAudioWarning(frameWarning)
          }
        } else {
          pendingWarningRef.current = null
          pendingWarningCountRef.current = 0
          clearCountRef.current += 1
          if (clearCountRef.current >= WARNING_CLEAR_FRAMES) {
            setAudioWarning(null)
          }
        }

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
    setAudioWarning(null)
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
    audioWarning,
    error,
  }
}
