"use client"

import { useExtracted } from "next-intl"
import { ArrowLeft, Check } from "lucide-react"
import { Button } from "@workspace/ui/components/button"
import { Badge } from "@workspace/ui/components/badge"
import { Textarea } from "@workspace/ui/components/textarea"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@workspace/ui/components/card"
import {
  useSOAPNote,
  useUpdateSOAPNote,
  useFinalizeSOAPNote,
} from "@/hooks/use-soap-note"
import Link from "next/link"

interface SOAPReviewFormProps {
  consultationId: string
}

export function SOAPReviewForm({ consultationId }: SOAPReviewFormProps) {
  const t = useExtracted()
  const token = "" // TODO: get JWT token from session

  const { data: soap, isLoading } = useSOAPNote(token, consultationId)
  const updateSOAP = useUpdateSOAPNote(token, consultationId)
  const finalizeSOAP = useFinalizeSOAPNote(token, consultationId)

  if (isLoading) {
    return <p className="text-muted-foreground">{t("Loading...")}</p>
  }

  if (!soap) {
    return <p className="text-muted-foreground">SOAP note not found</p>
  }

  const sections = [
    { key: "subjective", label: t("Subjective") },
    { key: "objective", label: t("Objective") },
    { key: "assessment", label: t("Assessment") },
    { key: "plan", label: t("Plan") },
  ] as const

  function handleSave(section: string, value: string) {
    updateSOAP.mutate({ [section]: value })
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href={`/consultations/${consultationId}`}>
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <h1 className="text-2xl font-bold">{t("SOAP Note")}</h1>
          <Badge variant={soap.is_draft ? "secondary" : "default"}>
            {soap.is_draft ? t("Draft") : t("Completed")}
          </Badge>
        </div>
        {soap.is_draft && (
          <Button
            onClick={() => finalizeSOAP.mutate()}
            disabled={finalizeSOAP.isPending}
            className="gap-2"
          >
            <Check className="h-4 w-4" />
            {t("Finalize Note")}
          </Button>
        )}
      </div>

      {sections.map(({ key, label }) => (
        <Card key={key}>
          <CardHeader>
            <CardTitle className="text-base">{label}</CardTitle>
          </CardHeader>
          <CardContent>
            <Textarea
              value={soap[key]}
              onChange={(e) => handleSave(key, e.target.value)}
              disabled={!soap.is_draft}
              rows={5}
              className="resize-none"
            />
          </CardContent>
        </Card>
      ))}

      {soap.medical_entities &&
        Object.keys(soap.medical_entities).length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Medical Entities</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {Object.entries(soap.medical_entities).map(
                  ([category, entities]) =>
                    Array.isArray(entities) &&
                    entities.map((entity, i) => (
                      <Badge key={`${category}-${i}`} variant="outline">
                        {category}: {entity}
                      </Badge>
                    )),
                )}
              </div>
            </CardContent>
          </Card>
        )}
    </div>
  )
}
