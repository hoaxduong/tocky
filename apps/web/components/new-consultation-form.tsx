"use client"

import { useState } from "react"
import { useExtracted } from "next-intl"
import { Button } from "@workspace/ui/components/button"
import { Input } from "@workspace/ui/components/input"
import { Label } from "@workspace/ui/components/label"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@workspace/ui/components/card"
import { LanguageSelector } from "@/components/scribe/language-selector"
import { useCreateConsultation } from "@/hooks/use-consultation"
import { useRouter } from "next/navigation"
import { toast } from "sonner"

export function NewConsultationForm() {
  const t = useExtracted()
  const router = useRouter()
  const token = "" // TODO: get JWT token from session
  const createConsultation = useCreateConsultation(token)

  const [title, setTitle] = useState("")
  const [patientId, setPatientId] = useState("")
  const [language, setLanguage] = useState("vi")

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    try {
      const consultation = await createConsultation.mutateAsync({
        title,
        patient_identifier: patientId || null,
        language,
      })
      toast.success(t("Consultation created"))
      router.push(`/consultations/${consultation.id}`)
    } catch {
      toast.error(t("Failed to create consultation"))
    }
  }

  return (
    <div className="mx-auto max-w-lg">
      <Card>
        <CardHeader>
          <CardTitle>{t("New Consultation")}</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="title">{t("Title")}</Label>
              <Input
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder={t("New Consultation")}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="patient-id">{t("Patient Identifier")}</Label>
              <Input
                id="patient-id"
                value={patientId}
                onChange={(e) => setPatientId(e.target.value)}
              />
            </div>
            <LanguageSelector value={language} onChange={setLanguage} />
            <Button
              type="submit"
              className="w-full"
              disabled={createConsultation.isPending}
            >
              {createConsultation.isPending
                ? t("Loading...")
                : t("Create")}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
