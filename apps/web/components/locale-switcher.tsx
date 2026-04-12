"use client"

import { useRouter } from "next/navigation"
import { useLocale } from "next-intl"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@workspace/ui/components/select"
import { LOCALE_COOKIE, SUPPORTED_LOCALES } from "@/i18n/config"

const LOCALE_LABELS: Record<string, string> = {
  en: "English",
  vi: "Tiếng Việt",
  ar: "العربية",
}

export function LocaleSwitcher() {
  const locale = useLocale()
  const router = useRouter()

  function handleChange(value: string) {
    document.cookie = `${LOCALE_COOKIE}=${value};path=/;max-age=31536000`
    router.refresh()
  }

  return (
    <Select value={locale} onValueChange={handleChange}>
      <SelectTrigger className="w-[130px]">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {SUPPORTED_LOCALES.map((loc) => (
          <SelectItem key={loc} value={loc}>
            {LOCALE_LABELS[loc]}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
