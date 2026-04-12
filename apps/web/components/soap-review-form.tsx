"use client"

import { useExtracted } from "next-intl"
import { Check } from "lucide-react"
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
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@workspace/ui/components/alert-dialog"
import {
  useSOAPNote,
  useUpdateSOAPNote,
  useFinalizeSOAPNote,
} from "@/hooks/use-soap-note"
import { toast } from "sonner"
import { SOAPFormSkeleton } from "@/components/skeletons"
import { PageHeader } from "@/components/page-header"

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
    return <SOAPFormSkeleton />
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
    updateSOAP.mutate({ [section]: value }, {
      onError: () => toast.error(t("Failed to save changes")),
    })
  }

  function handleFinalize() {
    finalizeSOAP.mutate(undefined, {
      onSuccess: () => toast.success(t("SOAP note finalized")),
      onError: () => toast.error(t("Failed to finalize note")),
    })
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader
        title={t("SOAP Note")}
        backHref={`/consultations/${consultationId}`}
        breadcrumbs={[
          { label: t("Consultations"), href: "/consultations" },
          { label: t("SOAP Note") },
        ]}
        actions={
          <>
            <Badge variant={soap.is_draft ? "secondary" : "default"}>
              {soap.is_draft ? t("Draft") : t("Completed")}
            </Badge>
            {soap.is_draft && (
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button disabled={finalizeSOAP.isPending} className="gap-2">
                    <Check className="h-4 w-4" />
                    {t("Finalize Note")}
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>
                      {t("Finalize SOAP Note?")}
                    </AlertDialogTitle>
                    <AlertDialogDescription>
                      {t(
                        "This action cannot be undone. The note will be locked for editing.",
                      )}
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>{t("Cancel")}</AlertDialogCancel>
                    <AlertDialogAction onClick={handleFinalize}>
                      {t("Finalize")}
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            )}
          </>
        }
      />

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
