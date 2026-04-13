"use client"

import { useRef, useState } from "react"
import { useExtracted } from "next-intl"
import { ArrowLeft, Mic, Plus, Upload, X } from "lucide-react"
import { Button } from "@workspace/ui/components/button"
import { Badge } from "@workspace/ui/components/badge"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@workspace/ui/components/dialog"
import { useCreateConsultation, useUploadAudio } from "@/hooks/use-consultation"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { cn } from "@workspace/ui/lib/utils"

type DialogStep = "mode-select" | "upload-form"

const MAX_FILE_SIZE_MB = 100
const ACCEPTED_TYPES = "audio/*,.mp3,.wav,.m4a,.ogg,.flac,.webm,.aac"

export function NewConsultationDialog() {
  const t = useExtracted()
  const router = useRouter()
  const createConsultation = useCreateConsultation()
  const uploadAudio = useUploadAudio()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [open, setOpen] = useState(false)
  const [step, setStep] = useState<DialogStep>("mode-select")
  const [file, setFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)

  const isSubmitting = createConsultation.isPending || uploadAudio.isPending

  function resetForm() {
    setStep("mode-select")
    setFile(null)
  }

  function handleFileSelect(selected: File | null) {
    if (!selected) return
    if (selected.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
      toast.error(t("File too large. Maximum size is 100 MB."))
      return
    }
    setFile(selected)
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setIsDragging(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped) handleFileSelect(dropped)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!file) return

    try {
      const consultation = await createConsultation.mutateAsync({
        mode: "upload",
      })

      await uploadAudio.mutateAsync({
        consultationId: consultation.id,
        file,
      })

      toast.success(t("Audio uploaded. Processing started."))
      setOpen(false)
      resetForm()
      router.push(`/consultations/${consultation.id}`)
    } catch {
      toast.error(t("Failed to upload audio"))
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        setOpen(v)
        if (!v) resetForm()
      }}
    >
      <DialogTrigger asChild>
        <Button className="gap-2">
          <Plus className="h-4 w-4" />
          {t("New Consultation")}
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        {step === "mode-select" && (
          <>
            <DialogHeader>
              <DialogTitle>{t("New Consultation")}</DialogTitle>
              <DialogDescription>
                {t("Choose how to start your consultation.")}
              </DialogDescription>
            </DialogHeader>
            <div className="grid grid-cols-2 gap-3 py-4">
              <button
                disabled
                className="border-muted bg-muted/50 text-muted-foreground relative flex flex-col items-center gap-3 rounded-lg border p-6 opacity-60"
              >
                <Badge
                  variant="secondary"
                  className="absolute top-2 right-2 text-[10px]"
                >
                  {t("Coming soon")}
                </Badge>
                <Mic className="h-8 w-8" />
                <span className="text-sm font-medium">
                  {t("Record Live")}
                </span>
              </button>
              <button
                onClick={() => setStep("upload-form")}
                className="border-border hover:border-primary hover:bg-accent flex flex-col items-center gap-3 rounded-lg border p-6 transition-colors"
              >
                <Upload className="h-8 w-8" />
                <span className="text-sm font-medium">
                  {t("Upload Audio")}
                </span>
              </button>
            </div>
          </>
        )}

        {step === "upload-form" && (
          <>
            <DialogHeader>
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={() => {
                    setStep("mode-select")
                    setFile(null)
                  }}
                >
                  <ArrowLeft className="h-4 w-4" />
                </Button>
                <DialogTitle>{t("Upload Audio")}</DialogTitle>
              </div>
              <DialogDescription>
                {t(
                  "Upload a recorded consultation. Language, title, and patient info will be auto-detected.",
                )}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* File drop zone */}
              {!file ? (
                <div
                  onDragOver={(e) => {
                    e.preventDefault()
                    setIsDragging(true)
                  }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={cn(
                    "flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition-colors",
                    isDragging
                      ? "border-primary bg-primary/5"
                      : "border-muted-foreground/25 hover:border-primary/50",
                  )}
                >
                  <Upload className="text-muted-foreground h-8 w-8" />
                  <p className="text-muted-foreground text-sm">
                    {t("Drag and drop or click to browse")}
                  </p>
                  <p className="text-muted-foreground text-xs">
                    MP3, WAV, M4A, OGG, FLAC, WebM, AAC ({MAX_FILE_SIZE_MB}
                    MB max)
                  </p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept={ACCEPTED_TYPES}
                    className="hidden"
                    onChange={(e) =>
                      handleFileSelect(e.target.files?.[0] ?? null)
                    }
                  />
                </div>
              ) : (
                <div className="bg-muted/50 flex items-center gap-3 rounded-lg border p-3">
                  <Upload className="text-muted-foreground h-5 w-5 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{file.name}</p>
                    <p className="text-muted-foreground text-xs">
                      {(file.size / 1024 / 1024).toFixed(1)} MB
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 shrink-0"
                    onClick={() => setFile(null)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              )}

              <DialogFooter>
                <Button
                  type="submit"
                  className="w-full"
                  disabled={!file || isSubmitting}
                >
                  {isSubmitting
                    ? t("Uploading...")
                    : t("Upload & Process")}
                </Button>
              </DialogFooter>
            </form>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
