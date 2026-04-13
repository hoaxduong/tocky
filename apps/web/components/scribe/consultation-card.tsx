"use client"

import { useState } from "react"
import { useExtracted } from "next-intl"
import {
  AlertTriangle,
  Archive,
  ChevronRight,
  Mic,
  MoreHorizontal,
  Trash2,
  Upload,
  User,
} from "lucide-react"
import { Badge } from "@workspace/ui/components/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@workspace/ui/components/card"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@workspace/ui/components/dropdown-menu"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@workspace/ui/components/alert-dialog"
import { Button } from "@workspace/ui/components/button"
import { Progress } from "@workspace/ui/components/progress"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@workspace/ui/components/tooltip"
import { StatusBadge } from "@/components/status-badge"
import {
  useArchiveConsultation,
  useDeleteConsultation,
} from "@/hooks/use-consultation"
import { toast } from "sonner"
import Link from "next/link"

interface ConsultationCardProps {
  id: string
  title: string
  language: string
  status: string
  createdAt: string
  patientIdentifier?: string | null
  mode?: string
  processingProgress?: number
  processingStep?: string | null
  errorMessage?: string | null
}

function formatRelativeTime(dateStr: string): string {
  const now = Date.now()
  const date = new Date(dateStr).getTime()
  const diffMs = now - date
  const diffSec = Math.floor(diffMs / 1000)
  const diffMin = Math.floor(diffSec / 60)
  const diffHr = Math.floor(diffMin / 60)
  const diffDay = Math.floor(diffHr / 24)

  const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" })

  if (diffDay > 30) {
    return new Date(dateStr).toLocaleDateString()
  }
  if (diffDay >= 1) return rtf.format(-diffDay, "day")
  if (diffHr >= 1) return rtf.format(-diffHr, "hour")
  if (diffMin >= 1) return rtf.format(-diffMin, "minute")
  return rtf.format(0, "second")
}

export function ConsultationCard({
  id,
  title,
  language,
  status,
  createdAt,
  patientIdentifier,
  mode,
  processingProgress,
  processingStep,
  errorMessage,
}: ConsultationCardProps) {
  const t = useExtracted()
  const [deleteOpen, setDeleteOpen] = useState(false)
  const archiveConsultation = useArchiveConsultation()
  const deleteConsultation = useDeleteConsultation()

  const isArchived = status === "archived"
  const isProcessing = status === "processing"
  const hasError = status === "failed" || status === "completed_with_errors"

  function handleArchive(e: React.MouseEvent) {
    e.preventDefault()
    archiveConsultation.mutate(id, {
      onSuccess: () => toast.success(t("Consultation archived")),
      onError: () => toast.error(t("Failed to archive consultation")),
    })
  }

  function handleDelete() {
    deleteConsultation.mutate(id, {
      onSuccess: () => toast.success(t("Consultation deleted")),
      onError: () => toast.error(t("Failed to delete consultation")),
    })
  }

  return (
    <>
      <Link href={`/consultations/${id}`}>
        <Card className="group h-full cursor-pointer transition-all hover:border-primary/30 hover:shadow-sm">
          <CardHeader className="pb-2">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <CardTitle className="truncate text-base">
                  {title || t("New Consultation")}
                </CardTitle>
                {patientIdentifier && (
                  <div className="mt-1 flex items-center gap-1 text-sm text-muted-foreground">
                    <User className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate">{patientIdentifier}</span>
                  </div>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-1">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-muted-foreground opacity-0 group-hover:opacity-100"
                      onClick={(e) => e.preventDefault()}
                    >
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    {!isArchived && (
                      <DropdownMenuItem onClick={handleArchive}>
                        <Archive className="mr-2 h-4 w-4" />
                        {t("Archive")}
                      </DropdownMenuItem>
                    )}
                    {isArchived && (
                      <DropdownMenuItem
                        className="text-destructive focus:text-destructive"
                        onClick={(e) => {
                          e.preventDefault()
                          setDeleteOpen(true)
                        }}
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        {t("Delete")}
                      </DropdownMenuItem>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>
                <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <StatusBadge status={status} />
              <span className="text-sm text-muted-foreground">
                {formatRelativeTime(createdAt)}
              </span>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-center gap-1.5">
              <Badge variant="outline">{language}</Badge>
              {mode && (
                <Badge variant="outline" className="gap-1">
                  {mode === "upload" ? (
                    <Upload className="h-3 w-3" />
                  ) : (
                    <Mic className="h-3 w-3" />
                  )}
                  {mode === "upload" ? t("Upload") : t("Live")}
                </Badge>
              )}
              {hasError && errorMessage && (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span
                        className="inline-flex"
                        onClick={(e) => e.preventDefault()}
                      >
                        <AlertTriangle className="h-4 w-4 text-destructive" />
                      </span>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>{errorMessage}</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
            </div>
            {isProcessing && (
              <div className="space-y-1">
                <Progress value={processingProgress ?? 0} />
                {processingStep && (
                  <p className="text-xs capitalize text-muted-foreground">
                    {processingStep}
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </Link>

      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("Delete Consultation?")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t(
                "This will permanently delete this consultation and all its data. This action cannot be undone."
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("Cancel")}</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="text-destructive-foreground bg-destructive hover:bg-destructive/90"
            >
              {t("Delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
