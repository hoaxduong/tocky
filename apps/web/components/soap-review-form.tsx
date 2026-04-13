"use client"

import { useExtracted } from "next-intl"
import { Check, RefreshCw } from "lucide-react"
import { Button } from "@workspace/ui/components/button"
import ReactMarkdown from "react-markdown"
import { Badge } from "@workspace/ui/components/badge"
import { Textarea } from "@workspace/ui/components/textarea"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@workspace/ui/components/card"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@workspace/ui/components/tabs"
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
  useRegenerateSOAPNote,
} from "@/hooks/use-soap-note"
import { toast } from "sonner"
import { SOAPFormSkeleton } from "@/components/skeletons"
import { PageHeader } from "@/components/page-header"

interface SOAPReviewFormProps {
  consultationId: string
}

export function SOAPReviewForm({ consultationId }: SOAPReviewFormProps) {
  const t = useExtracted()
  const { data: soap, isLoading } = useSOAPNote(consultationId)
  const updateSOAP = useUpdateSOAPNote(consultationId)
  const finalizeSOAP = useFinalizeSOAPNote(consultationId)
  const regenerateSOAP = useRegenerateSOAPNote(consultationId)

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
              <Button
                variant="outline"
                disabled={regenerateSOAP.isPending}
                className="gap-2"
                onClick={() =>
                  regenerateSOAP.mutate(undefined, {
                    onSuccess: () =>
                      toast.success(t("SOAP note regenerated")),
                    onError: () =>
                      toast.error(t("Failed to regenerate SOAP note")),
                  })
                }
              >
                <RefreshCw
                  className={`h-4 w-4 ${regenerateSOAP.isPending ? "animate-spin" : ""}`}
                />
                {regenerateSOAP.isPending
                  ? t("Regenerating...")
                  : t("Regenerate")}
              </Button>
            )}
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
            <Tabs defaultValue="preview">
              <TabsList>
                <TabsTrigger value="preview">{t("Preview")}</TabsTrigger>
                <TabsTrigger value="raw">{t("Raw")}</TabsTrigger>
              </TabsList>
              <TabsContent value="preview">
                {soap[key] ? (
                  <div className="prose prose-sm dark:prose-invert max-w-none">
                    <ReactMarkdown>{soap[key]}</ReactMarkdown>
                  </div>
                ) : (
                  <p className="text-muted-foreground text-sm italic">
                    {t("No content yet")}
                  </p>
                )}
              </TabsContent>
              <TabsContent value="raw">
                <Textarea
                  value={soap[key]}
                  onChange={(e) => handleSave(key, e.target.value)}
                  disabled={!soap.is_draft}
                  rows={5}
                  className="resize-none"
                />
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      ))}

      {soap.medical_entities &&
        Object.keys(soap.medical_entities).length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                {t("Medical Entities")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {Object.entries(soap.medical_entities).map(
                  ([category, entities]) =>
                    Array.isArray(entities) &&
                    entities.length > 0 && (
                      <div key={category} className="space-y-1.5">
                        <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          {category}
                        </h4>
                        <div className="flex flex-wrap gap-1.5">
                          {entities.map((entity, i) => (
                            <Badge key={i} variant="outline">
                              {entity}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    ),
                )}
              </div>
            </CardContent>
          </Card>
        )}
    </div>
  )
}
