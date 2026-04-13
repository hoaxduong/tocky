import { cookies } from "next/headers"
import { getRequestConfig } from "next-intl/server"
import { SUPPORTED_LOCALES, DEFAULT_LOCALE, LOCALE_COOKIE } from "./config"
import type { Locale } from "./config"

export default getRequestConfig(async () => {
  const store = await cookies()
  const raw = store.get(LOCALE_COOKIE)?.value
  const locale = SUPPORTED_LOCALES.includes(raw as Locale)
    ? (raw as Locale)
    : DEFAULT_LOCALE

  const messages = (await import(`../messages/${locale}.po`)).default

  return {
    locale,
    messages,
  }
})
