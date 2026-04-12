"use client"

import { Textarea } from "@workspace/ui/components/textarea"

interface SOAPSectionProps {
  label: string
  value: string
  onChange: (value: string) => void
  disabled?: boolean
}

export function SOAPSection({
  label,
  value,
  onChange,
  disabled,
}: SOAPSectionProps) {
  return (
    <div className="space-y-1">
      <label className="text-sm font-semibold">{label}</label>
      <Textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        rows={4}
        className="resize-none"
      />
    </div>
  )
}
