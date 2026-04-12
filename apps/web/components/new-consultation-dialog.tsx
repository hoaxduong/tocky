"use client"

import { useState } from "react"
import { useExtracted } from "next-intl"
import { Plus } from "lucide-react"
import { Button } from "@workspace/ui/components/button"
import { Input } from "@workspace/ui/components/input"
import { Label } from "@workspace/ui/components/label"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@workspace/ui/components/dialog"
import { LanguageSelector } from "@/components/scribe/language-selector"
import { useCreateConsultation } from "@/hooks/use-consultation"
import { useRouter } from "next/navigation"
import { toast } from "sonner"

export function NewConsultationDialog() {
  const t = useExtracted()
  const router = useRouter()
  const createConsultation = useCreateConsultation()

  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState("")
  const [patientId, setPatientId] = useState("")
  const [language, setLanguage] = useState("vi")

  function resetForm() {
    setTitle("")
    setPatientId("")
    setLanguage("vi")
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    try {
      const consultation = await createConsultation.mutateAsync({
        title,
        patient_identifier: patientId || null,
        language,
      })
      toast.success(t("Consultation created"))
      setOpen(false)
      resetForm()
      router.push(`/consultations/${consultation.id}`)
    } catch {
      toast.error(t("Failed to create consultation"))
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) resetForm() }}>
      <DialogTrigger asChild>
        <Button className="gap-2">
          <Plus className="h-4 w-4" />
          {t("New Consultation")}
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{t("New Consultation")}</DialogTitle>
          <DialogDescription>
            {t("Start a new clinical consultation session.")}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="dialog-title">{t("Title")}</Label>
            <Input
              id="dialog-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={t("New Consultation")}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="dialog-patient-id">
              {t("Patient Identifier")}
              <span className="text-muted-foreground ml-1 text-xs font-normal">
                ({t("optional")})
              </span>
            </Label>
            <Input
              id="dialog-patient-id"
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
            />
          </div>
          <LanguageSelector value={language} onChange={setLanguage} />
          <DialogFooter>
            <Button
              type="submit"
              className="w-full"
              disabled={createConsultation.isPending}
            >
              {createConsultation.isPending ? t("Creating...") : t("Create")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
