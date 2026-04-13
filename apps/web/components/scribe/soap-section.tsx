"use client"

import { useExtracted } from "next-intl"
import { MarkdownPreview } from "@/components/markdown-preview"
import { Textarea } from "@workspace/ui/components/textarea"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@workspace/ui/components/tabs"

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
  const t = useExtracted()

  return (
    <div className="space-y-1">
      <label className="text-sm font-semibold">{label}</label>
      <Tabs defaultValue="preview">
        <TabsList>
          <TabsTrigger value="preview">{t("Preview")}</TabsTrigger>
          <TabsTrigger value="raw">{t("Raw")}</TabsTrigger>
        </TabsList>
        <TabsContent value="preview">
          {value ? (
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <MarkdownPreview>{value}</MarkdownPreview>
            </div>
          ) : (
            <p className="text-muted-foreground text-sm italic">
              {t("No content yet")}
            </p>
          )}
        </TabsContent>
        <TabsContent value="raw">
          <Textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
            rows={4}
            className="resize-none"
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}
