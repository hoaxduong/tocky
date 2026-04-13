"use client"

import type { RefObject } from "react"
import { useHotkey } from "@tanstack/react-hotkeys"
import type { AudioPlayerHandle } from "@/components/audio-player"

/**
 * Registers keyboard shortcuts for audio playback.
 *
 * - Space: play / pause
 * - ArrowLeft / ArrowRight: seek ∓5 s
 * - Shift+ArrowLeft / Shift+ArrowRight: seek ∓15 s
 *
 * All shortcuts are disabled when `enabled` is false (e.g. no audio loaded).
 */
export function useAudioHotkeys(
  playerRef: RefObject<AudioPlayerHandle | null>,
  enabled: boolean,
) {
  useHotkey("Space", () => playerRef.current?.togglePlay(), { enabled })

  useHotkey("ArrowLeft", () => playerRef.current?.seekRelative(-5000), {
    enabled,
  })

  useHotkey("ArrowRight", () => playerRef.current?.seekRelative(5000), {
    enabled,
  })

  useHotkey(
    "Shift+ArrowLeft",
    () => playerRef.current?.seekRelative(-15000),
    { enabled },
  )

  useHotkey(
    "Shift+ArrowRight",
    () => playerRef.current?.seekRelative(15000),
    { enabled },
  )
}
