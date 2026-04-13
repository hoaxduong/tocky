"use client"

import { useRef, useState, useLayoutEffect } from "react"
import type { ElfieVitals } from "@/hooks/use-elfie"
import { useExtracted } from "next-intl"

// ---------------------------------------------------------------------------
// Smooth monotone cubic spline (Fritsch–Carlson)
// ---------------------------------------------------------------------------
function monotoneCubicPath(
  pts: { x: number; y: number }[]
): string {
  if (pts.length < 2) return ""
  if (pts.length === 2)
    return `M${pts[0]!.x},${pts[0]!.y}L${pts[1]!.x},${pts[1]!.y}`

  const n = pts.length
  const dx: number[] = new Array(n - 1)
  const dy: number[] = new Array(n - 1)
  const slopes: number[] = new Array(n - 1)

  for (let i = 0; i < n - 1; i++) {
    dx[i] = pts[i + 1]!.x - pts[i]!.x
    dy[i] = pts[i + 1]!.y - pts[i]!.y
    slopes[i] = dy[i]! / dx[i]!
  }

  const tangents: number[] = new Array(n)
  tangents[0] = slopes[0]!
  tangents[n - 1] = slopes[n - 2]!
  for (let i = 1; i < n - 1; i++) {
    if (slopes[i - 1]! * slopes[i]! <= 0) {
      tangents[i] = 0
    } else {
      tangents[i] =
        (3 * (dx[i - 1]! + dx[i]!)) /
        ((2 * dx[i]! + dx[i - 1]!) / slopes[i - 1]! +
          (dx[i]! + 2 * dx[i - 1]!) / slopes[i]!)
    }
  }

  let d = `M${pts[0]!.x},${pts[0]!.y}`
  for (let i = 0; i < n - 1; i++) {
    const seg = dx[i]! / 3
    const cp1x = pts[i]!.x + seg
    const cp1y = pts[i]!.y + tangents[i]! * seg
    const cp2x = pts[i + 1]!.x - seg
    const cp2y = pts[i + 1]!.y - tangents[i + 1]! * seg
    d += `C${cp1x},${cp1y},${cp2x},${cp2y},${pts[i + 1]!.x},${pts[i + 1]!.y}`
  }
  return d
}

// ---------------------------------------------------------------------------
// Chart component
// ---------------------------------------------------------------------------
interface ChartProps {
  values: number[]
  color: string
  thresholdValue?: number
  thresholdLabel?: string
}

function Chart({
  values,
  color,
  thresholdValue,
  thresholdLabel,
}: ChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(0)

  useLayoutEffect(() => {
    const el = containerRef.current
    if (!el) return
    const obs = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (entry) setWidth(Math.round(entry.contentRect.width))
    })
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  if (values.length < 2) return <div ref={containerRef} />

  const height = 64
  const padX = 2
  const padTop = 6
  const padBottom = 14

  const dataMin = Math.min(...values)
  const dataMax = Math.max(...values)
  // Include threshold in range so it's always visible
  const rangeMin =
    thresholdValue !== undefined ? Math.min(dataMin, thresholdValue) : dataMin
  const rangeMax =
    thresholdValue !== undefined ? Math.max(dataMax, thresholdValue) : dataMax
  const range = rangeMax - rangeMin || 1
  // Add 10% vertical padding so points don't touch edges
  const yMin = rangeMin - range * 0.1
  const yMax = rangeMax + range * 0.1
  const yRange = yMax - yMin

  const toX = (i: number) =>
    padX + (i / (values.length - 1)) * (width - padX * 2)
  const toY = (v: number) =>
    padTop + (1 - (v - yMin) / yRange) * (height - padTop - padBottom)

  const pts = values.map((v, i) => ({ x: toX(i), y: toY(v) }))
  const linePath = monotoneCubicPath(pts)

  // Area path: line path + close along bottom
  const firstPt = pts[0]!
  const lastPt = pts[pts.length - 1]!

  const areaPath =
    linePath +
    `L${lastPt.x},${height - padBottom}L${firstPt.x},${height - padBottom}Z`

  const thresholdY =
    thresholdValue !== undefined ? toY(thresholdValue) : undefined

  const gradientId = `grad-${color.replace(/[^a-zA-Z0-9]/g, "")}`

  return (
    <div ref={containerRef} className="w-full">
      {width > 0 && (
        <svg width={width} height={height} className="overflow-visible">
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.2} />
              <stop offset="100%" stopColor={color} stopOpacity={0.02} />
            </linearGradient>
          </defs>

          {/* Area fill */}
          <path d={areaPath} fill={`url(#${gradientId})`} />

          {/* Threshold dashed line */}
          {thresholdY !== undefined && (
            <>
              <line
                x1={padX}
                y1={thresholdY}
                x2={width - padX}
                y2={thresholdY}
                stroke="currentColor"
                className="text-muted-foreground/30"
                strokeWidth={1}
                strokeDasharray="4 3"
              />
              {thresholdLabel && (
                <text
                  x={width - padX}
                  y={thresholdY - 3}
                  textAnchor="end"
                  className="fill-muted-foreground text-[9px]"
                >
                  {thresholdLabel}
                </text>
              )}
            </>
          )}

          {/* Line */}
          <path
            d={linePath}
            fill="none"
            stroke={color}
            strokeWidth={1.5}
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Data point dots */}
          {pts.map((p, i) => (
            <circle
              key={i}
              cx={p.x}
              cy={p.y}
              r={i === pts.length - 1 ? 3 : 1.5}
              fill={i === pts.length - 1 ? color : "white"}
              stroke={color}
              strokeWidth={i === pts.length - 1 ? 0 : 1}
            />
          ))}

          {/* Latest value label */}
          <text
            x={lastPt.x}
            y={lastPt.y - 6}
            textAnchor="end"
            className="text-[10px] font-medium"
            fill={color}
          >
            {values[values.length - 1]}
          </text>
        </svg>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Vitals tab
// ---------------------------------------------------------------------------
interface ElfieVitalsTabProps {
  vitals: ElfieVitals
}

export function ElfieVitalsTab({ vitals }: ElfieVitalsTabProps) {
  const t = useExtracted()

  const latestBP = vitals.blood_pressure[vitals.blood_pressure.length - 1]

  return (
    <div className="space-y-4">
      {/* Glucose + BP side by side */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5 rounded-md border p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium">{t("Fasting Glucose")}</span>
            <span className="text-[10px] text-muted-foreground">mg/dL</span>
          </div>
          <Chart
            values={vitals.glucose.map((r) => r.value)}
            color="var(--color-amber-500)"
            thresholdValue={100}
            thresholdLabel={t("normal")}
          />
        </div>

        <div className="space-y-1.5 rounded-md border p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium">{t("Blood Pressure")}</span>
            <span className="text-[10px] text-muted-foreground">
              {latestBP?.systolic}/{latestBP?.diastolic} mmHg
            </span>
          </div>
          <Chart
            values={vitals.blood_pressure.map((r) => r.systolic)}
            color="var(--color-orange-500)"
            thresholdValue={120}
            thresholdLabel={t("normal")}
          />
        </div>
      </div>

      {/* Weight — full width, shorter */}
      <div className="space-y-1.5 rounded-md border p-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium">{t("Weight")}</span>
          <span className="text-[10px] text-muted-foreground">
            {vitals.weight.length} {t("readings")} · kg
          </span>
        </div>
        <Chart
          values={vitals.weight.map((r) => r.value)}
          color="var(--color-blue-500)"
        />
      </div>
    </div>
  )
}
