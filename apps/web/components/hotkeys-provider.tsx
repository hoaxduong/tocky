"use client"

import { HotkeysProvider as TanStackHotkeysProvider } from "@tanstack/react-hotkeys"

export function HotkeysProvider({ children }: { children: React.ReactNode }) {
  return <TanStackHotkeysProvider>{children}</TanStackHotkeysProvider>
}
