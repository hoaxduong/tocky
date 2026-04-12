"use client"

interface AudioVisualizerProps {
  level: number // 0 to 1
  isRecording: boolean
}

export function AudioVisualizer({ level, isRecording }: AudioVisualizerProps) {
  const bars = 20
  const activeCount = Math.floor(level * bars * 5) // amplify for visibility

  return (
    <div className="flex h-8 items-end gap-0.5">
      {Array.from({ length: bars }).map((_, i) => (
        <div
          key={i}
          className={`w-1 rounded-full transition-all duration-75 ${
            isRecording && i < activeCount
              ? "bg-primary"
              : "bg-muted"
          }`}
          style={{
            height: isRecording && i < activeCount
              ? `${Math.max(4, (level * 32 * (1 + Math.sin(i * 0.5))))}px`
              : "4px",
          }}
        />
      ))}
    </div>
  )
}
