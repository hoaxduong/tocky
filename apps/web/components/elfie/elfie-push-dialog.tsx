"use client"

import { useState } from "react"
import { useExtracted } from "next-intl"
import { Send, Check, X } from "lucide-react"
import { Button } from "@workspace/ui/components/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@workspace/ui/components/dialog"
import { Badge } from "@workspace/ui/components/badge"
import { toast } from "sonner"
import { usePushToElfie, type ElfieCarePlanItem } from "@/hooks/use-elfie"

interface ElfiePushDialogProps {
  consultationId: string
  patientIdentifier: string
  planText: string
}

const CATEGORY_COLORS: Record<string, string> = {
  medication: "border-violet-500 text-violet-700 dark:text-violet-400",
  dietary: "border-emerald-500 text-emerald-700 dark:text-emerald-400",
  activity: "border-blue-500 text-blue-700 dark:text-blue-400",
  monitoring: "border-amber-500 text-amber-700 dark:text-amber-400",
  education: "border-cyan-500 text-cyan-700 dark:text-cyan-400",
  "follow-up": "border-orange-500 text-orange-700 dark:text-orange-400",
}

function parsePlanItems(planText: string): ElfieCarePlanItem[] {
  const items: ElfieCarePlanItem[] = []
  const sections = planText.split(/\n\d+\.\s+\*\*/).filter(Boolean)

  for (const section of sections) {
    const headerMatch = section.match(/^([^*]+)\*\*/)
    const header = headerMatch?.[1]?.replace(/[*:]/g, "").trim().toLowerCase() ?? ""

    let category = "other"
    if (header.includes("pharmac") || header.includes("medic"))
      category = "medication"
    else if (header.includes("diet")) category = "dietary"
    else if (header.includes("physical") || header.includes("activit"))
      category = "activity"
    else if (header.includes("monitor")) category = "monitoring"
    else if (header.includes("education")) category = "education"
    else if (header.includes("follow")) category = "follow-up"

    const bullets = section.match(/- .+/g) ?? []
    for (const bullet of bullets) {
      const text = bullet.replace(/^- /, "").replace(/\*\*/g, "").trim()
      if (text.length > 5) {
        items.push({
          category,
          action: header || category,
          details: text,
        })
      }
    }
  }

  return items
}

export function ElfiePushDialog({
  consultationId,
  patientIdentifier,
  planText,
}: ElfiePushDialogProps) {
  const t = useExtracted()
  const pushToElfie = usePushToElfie()
  const [open, setOpen] = useState(false)

  const allItems = parsePlanItems(planText)
  const [excluded, setExcluded] = useState<Set<number>>(new Set())

  function toggleItem(index: number) {
    setExcluded((prev) => {
      const next = new Set(prev)
      if (next.has(index)) next.delete(index)
      else next.add(index)
      return next
    })
  }

  function handleSend() {
    const items = allItems.filter((_, i) => !excluded.has(i))
    pushToElfie.mutate(
      { consultation_id: consultationId, patient_identifier: patientIdentifier, items },
      {
        onSuccess: (result) => {
          toast.success(result.message)
          setOpen(false)
        },
        onError: () => toast.error(t("Failed to push care plan to Elfie")),
      }
    )
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className="gap-2">
          <Send className="h-4 w-4" />
          {t("Push to Elfie")}
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{t("Push Care Plan to Elfie")}</DialogTitle>
          <DialogDescription>
            {t(
              "The following items will be sent to the patient's Elfie app. Toggle items to include or exclude them."
            )}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          {allItems.length === 0 && (
            <p className="text-sm text-muted-foreground italic py-4">
              {t("No care plan items could be extracted from the SOAP plan.")}
            </p>
          )}
          {allItems.map((item, i) => (
            <button
              key={i}
              type="button"
              onClick={() => toggleItem(i)}
              className={`flex w-full items-start gap-2 rounded-md border p-2.5 text-left transition-colors ${
                excluded.has(i)
                  ? "opacity-40 bg-muted/30"
                  : "bg-background hover:bg-accent/50"
              }`}
            >
              <div className="mt-0.5 shrink-0">
                {excluded.has(i) ? (
                  <X className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <Check className="h-4 w-4 text-emerald-600" />
                )}
              </div>
              <div className="min-w-0 space-y-1">
                <Badge
                  variant="outline"
                  className={`text-[10px] capitalize ${CATEGORY_COLORS[item.category] ?? ""}`}
                >
                  {item.category}
                </Badge>
                <p className="text-sm">{item.details}</p>
              </div>
            </button>
          ))}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            {t("Cancel")}
          </Button>
          <Button
            onClick={handleSend}
            disabled={
              pushToElfie.isPending ||
              allItems.length === 0 ||
              excluded.size === allItems.length
            }
            className="gap-2"
          >
            <Send className="h-4 w-4" />
            {pushToElfie.isPending
              ? t("Sending...")
              : t("Send to Elfie")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
