"use client"

import { useEffect, useRef, useState } from "react"
import { useExtracted, useLocale } from "next-intl"
import { Check, Plus, RefreshCw, Search, X } from "lucide-react"
import { Badge } from "@workspace/ui/components/badge"
import { Button } from "@workspace/ui/components/button"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@workspace/ui/components/card"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@workspace/ui/components/popover"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@workspace/ui/components/command"
import { type ICD10Code, useICD10Search } from "@/hooks/use-soap-note"

interface ICD10CodeCardProps {
  codes: ICD10Code[]
  isDraft: boolean
  onUpdate: (codes: ICD10Code[]) => void
  onResuggest: () => void
  isResuggesting: boolean
}

export function ICD10CodeCard({
  codes,
  isDraft,
  onUpdate,
  onResuggest,
  isResuggesting,
}: ICD10CodeCardProps) {
  const t = useExtracted()
  const locale = useLocale()
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const { data: searchResults, isLoading: isSearching } = useICD10Search(
    searchQuery,
    locale
  )

  const activeCodes = codes.filter((c) => c.status !== "rejected")

  function updateStatus(index: number, status: ICD10Code["status"]) {
    const updated = codes.map((c, i) =>
      i === index ? { ...c, status } : c
    )
    onUpdate(updated)
  }

  function addCode(code: string, description: string) {
    if (codes.some((c) => c.code === code)) return
    onUpdate([
      ...codes,
      { code, description, diagnosis: "", status: "confirmed" },
    ])
    setSearchOpen(false)
    setSearchQuery("")
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            {t("ICD-10 Codes")}
            {activeCodes.length > 0 && (
              <Badge variant="outline">{activeCodes.length}</Badge>
            )}
          </CardTitle>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              disabled={isResuggesting}
              onClick={onResuggest}
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${isResuggesting ? "animate-spin" : ""}`}
              />
              {isResuggesting ? t("Suggesting...") : t("Re-suggest")}
            </Button>
            {isDraft && (
              <Popover open={searchOpen} onOpenChange={setSearchOpen}>
                <PopoverTrigger asChild>
                  <Button variant="outline" size="sm" className="gap-1.5">
                    <Plus className="h-3.5 w-3.5" />
                    {t("Add Code")}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-80 p-0" align="end">
                  <ICD10SearchCommand
                    query={searchQuery}
                    onQueryChange={setSearchQuery}
                    results={searchResults ?? []}
                    isSearching={isSearching}
                    existingCodes={codes.map((c) => c.code)}
                    onSelect={addCode}
                    t={t}
                  />
                </PopoverContent>
              </Popover>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {codes.length === 0 ? (
          <p className="text-sm text-muted-foreground italic">
            {t("No ICD-10 codes suggested yet")}
          </p>
        ) : (
          <div className="space-y-2">
            {codes.map((entry, i) => (
              <div
                key={entry.code}
                className={`flex items-start gap-3 rounded-md border p-3 ${
                  entry.status === "rejected"
                    ? "border-dashed opacity-40"
                    : entry.status === "confirmed"
                      ? "border-green-500/30 bg-green-500/5"
                      : "border-amber-500/30 bg-amber-500/5"
                }`}
              >
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge
                      variant="secondary"
                      className="font-mono text-xs"
                    >
                      {entry.code}
                    </Badge>
                    <Badge
                      variant="outline"
                      className={
                        entry.status === "confirmed"
                          ? "border-green-500 text-green-700"
                          : entry.status === "rejected"
                            ? "border-red-500 text-red-700 line-through"
                            : "border-amber-500 text-amber-700"
                      }
                    >
                      {entry.status === "confirmed"
                        ? t("confirmed")
                        : entry.status === "rejected"
                          ? t("rejected")
                          : t("suggested")}
                    </Badge>
                  </div>
                  <p className="text-sm">{entry.description}</p>
                  {entry.description_en &&
                    entry.description_en !== entry.description && (
                      <p className="text-xs text-muted-foreground italic">
                        {entry.description_en}
                      </p>
                    )}
                  {entry.diagnosis && (
                    <p className="text-xs text-muted-foreground">
                      {t("From")}: {entry.diagnosis}
                    </p>
                  )}
                </div>
                {isDraft && (
                  <div className="flex gap-1">
                    {entry.status !== "confirmed" && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-green-600 hover:text-green-700"
                        onClick={() => updateStatus(i, "confirmed")}
                        title={t("Confirm")}
                      >
                        <Check className="h-4 w-4" />
                      </Button>
                    )}
                    {entry.status !== "rejected" && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-red-600 hover:text-red-700"
                        onClick={() => updateStatus(i, "rejected")}
                        title={t("Reject")}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

interface ICD10SearchCommandProps {
  query: string
  onQueryChange: (q: string) => void
  results: { code: string; description: string; description_en: string }[]
  isSearching: boolean
  existingCodes: string[]
  onSelect: (code: string, description: string) => void
  t: (s: string) => string
}

function ICD10SearchCommand({
  query,
  onQueryChange,
  results,
  isSearching,
  existingCodes,
  onSelect,
  t,
}: ICD10SearchCommandProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  return (
    <Command shouldFilter={false}>
      <CommandInput
        ref={inputRef}
        placeholder={t("Search ICD-10 codes...")}
        value={query}
        onValueChange={onQueryChange}
      />
      <CommandList>
        {query.length < 2 ? (
          <div className="px-4 py-6 text-center text-xs text-muted-foreground">
            {t("Type at least 2 characters to search")}
          </div>
        ) : isSearching ? (
          <div className="flex items-center justify-center gap-2 py-6 text-xs text-muted-foreground">
            <Search className="h-3.5 w-3.5 animate-pulse" />
            {t("Searching...")}
          </div>
        ) : (
          <>
            <CommandEmpty>{t("No codes found")}</CommandEmpty>
            <CommandGroup>
              {results.map((result) => {
                const alreadyAdded = existingCodes.includes(result.code)
                return (
                  <CommandItem
                    key={result.code}
                    value={result.code}
                    disabled={alreadyAdded}
                    onSelect={() =>
                      onSelect(result.code, result.description)
                    }
                  >
                    <div className="flex flex-1 flex-col gap-0.5 overflow-hidden">
                      <div className="flex items-center gap-1.5">
                        <Badge
                          variant="secondary"
                          className="font-mono text-xs"
                        >
                          {result.code}
                        </Badge>
                        <span className="truncate text-xs">
                          {result.description}
                        </span>
                      </div>
                      {result.description_en &&
                        result.description_en !== result.description && (
                          <span className="truncate text-[10px] text-muted-foreground">
                            {result.description_en}
                          </span>
                        )}
                    </div>
                    {alreadyAdded && (
                      <Check className="h-3 w-3 shrink-0 text-muted-foreground" />
                    )}
                  </CommandItem>
                )
              })}
            </CommandGroup>
          </>
        )}
      </CommandList>
    </Command>
  )
}
