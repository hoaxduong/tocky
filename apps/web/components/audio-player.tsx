"use client"

import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react"
import { Pause, Play } from "lucide-react"
import { Button } from "@workspace/ui/components/button"
import { Slider } from "@workspace/ui/components/slider"
import { Card, CardContent } from "@workspace/ui/components/card"
import { cn } from "@workspace/ui/lib/utils"

export interface AudioPlayerHandle {
  seekTo: (ms: number) => void
}

interface AudioPlayerProps {
  src: string
  durationMs: number
  className?: string
  onTimeUpdate?: (timeMs: number) => void
}

function formatTime(seconds: number) {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, "0")}`
}

export const AudioPlayer = forwardRef<AudioPlayerHandle, AudioPlayerProps>(
  function AudioPlayer({ src, durationMs, className, onTimeUpdate }, ref) {
    const audioRef = useRef<HTMLAudioElement>(null)
    const [isPlaying, setIsPlaying] = useState(false)
    const [currentTime, setCurrentTime] = useState(0)
    const [duration, setDuration] = useState(durationMs / 1000)
    const [isSeeking, setIsSeeking] = useState(false)

    useImperativeHandle(ref, () => ({
      seekTo(ms: number) {
        const el = audioRef.current
        if (!el) return
        el.currentTime = ms / 1000
        void el.play().catch(() => {})
      },
    }))

    const handleTimeUpdate = useCallback(() => {
      if (!isSeeking && audioRef.current) {
        const t = audioRef.current.currentTime
        setCurrentTime(t)
        onTimeUpdate?.(t * 1000)
      }
    }, [isSeeking, onTimeUpdate])

    const handleLoadedMetadata = useCallback(() => {
      if (audioRef.current && isFinite(audioRef.current.duration)) {
        setDuration(audioRef.current.duration)
      }
    }, [])

    const handleEnded = useCallback(() => {
      setIsPlaying(false)
      setCurrentTime(0)
    }, [])

    useEffect(() => {
      const el = audioRef.current
      if (!el) return
      el.addEventListener("timeupdate", handleTimeUpdate)
      el.addEventListener("loadedmetadata", handleLoadedMetadata)
      el.addEventListener("ended", handleEnded)
      return () => {
        el.removeEventListener("timeupdate", handleTimeUpdate)
        el.removeEventListener("loadedmetadata", handleLoadedMetadata)
        el.removeEventListener("ended", handleEnded)
      }
    }, [handleTimeUpdate, handleLoadedMetadata, handleEnded])

    function togglePlay() {
      const el = audioRef.current
      if (!el) return
      if (isPlaying) {
        el.pause()
        setIsPlaying(false)
      } else {
        void el.play().catch(() => {})
        setIsPlaying(true)
      }
    }

    function handleSeek(value: number[]) {
      const time = value[0] ?? 0
      setCurrentTime(time)
      if (audioRef.current) {
        audioRef.current.currentTime = time
      }
    }

    return (
      <Card className={cn("py-0", className)}>
        <CardContent className="flex items-center gap-3 px-4 py-3">
          <audio ref={audioRef} src={src} preload="metadata" />

          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0"
            onClick={togglePlay}
          >
            {isPlaying ? (
              <Pause className="h-4 w-4" />
            ) : (
              <Play className="h-4 w-4" />
            )}
          </Button>

          <span className="w-10 text-xs text-muted-foreground tabular-nums">
            {formatTime(currentTime)}
          </span>

          <Slider
            className="flex-1"
            min={0}
            max={duration}
            step={0.1}
            value={[currentTime]}
            onValueChange={handleSeek}
            onPointerDown={() => setIsSeeking(true)}
            onPointerUp={() => setIsSeeking(false)}
          />

          <span className="w-10 text-xs text-muted-foreground tabular-nums">
            {formatTime(duration)}
          </span>
        </CardContent>
      </Card>
    )
  },
)
