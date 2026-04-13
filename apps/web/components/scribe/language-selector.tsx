"use client"

import { useExtracted } from "next-intl"
import { Label } from "@workspace/ui/components/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@workspace/ui/components/select"

const LANGUAGES = [
  { value: "vi", label: "Tiếng Việt" },
  { value: "ar-eg", label: "العربية (مصري)" },
  { value: "ar-gulf", label: "العربية (خليجي)" },
  { value: "en", label: "English" },
]

interface LanguageSelectorProps {
  value: string
  onChange: (value: string) => void
  disabled?: boolean
}

export function LanguageSelector({
  value,
  onChange,
  disabled,
}: LanguageSelectorProps) {
  const t = useExtracted()

  return (
    <div className="space-y-1">
      <Label className="text-xs">{t("Language")}</Label>
      <Select value={value} onValueChange={onChange} disabled={disabled}>
        <SelectTrigger className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {LANGUAGES.map((lang) => (
            <SelectItem key={lang.value} value={lang.value}>
              {lang.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
