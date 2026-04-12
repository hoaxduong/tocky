"use client"

import { useExtracted } from "next-intl"
import { Badge } from "@workspace/ui/components/badge"
import { Button } from "@workspace/ui/components/button"
import { useScribeStore } from "@/lib/stores/use-scribe-store"
import { SOAPSection } from "./soap-section"

interface SOAPEditorProps {
  onFinalize?: () => void
  disabled?: boolean
}

export function SOAPEditor({ onFinalize, disabled }: SOAPEditorProps) {
  const t = useExtracted()
  const { soapNote, updateSOAPSection, status } = useScribeStore()

  const sections = [
    { key: "subjective" as const, label: t("Subjective") },
    { key: "objective" as const, label: t("Objective") },
    { key: "assessment" as const, label: t("Assessment") },
    { key: "plan" as const, label: t("Plan") },
  ]

  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-lg font-semibold">{t("SOAP Note")}</h3>
        <Badge variant="secondary">{t("Draft")}</Badge>
      </div>
      <div className="flex-1 space-y-4 overflow-y-auto">
        {sections.map(({ key, label }) => (
          <SOAPSection
            key={key}
            label={label}
            value={soapNote[key]}
            onChange={(value) => updateSOAPSection(key, value)}
            disabled={disabled}
          />
        ))}
      </div>
      {status === "completed" && onFinalize && (
        <Button onClick={onFinalize} className="mt-4 w-full">
          {t("Finalize Note")}
        </Button>
      )}
    </div>
  )
}
