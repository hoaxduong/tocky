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
  CardAction,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@workspace/ui/components/card"
import { Separator } from "@workspace/ui/components/separator"
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
          {/* Zone 1: Identity */}
          <CardHeader>
            <CardTitle className="line-clamp-2 min-h-[2lh]">
              {title || t("New Consultation")}
            </CardTitle>
            <CardDescription>
              {patientIdentifier ? (
                <span className="inline-flex items-center gap-1">
                  <User className="size-3 shrink-0" />
                  <span className="truncate">{patientIdentifier}</span>
                </span>
              ) : (
                <span className="text-muted-foreground/50">
                  {t("No patient")}
                </span>
              )}
            </CardDescription>
            <CardAction>
              <div className="flex items-center gap-1">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-7 text-muted-foreground opacity-0 group-hover:opacity-100"
                      onClick={(e) => e.preventDefault()}
                    >
                      <MoreHorizontal className="size-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    {!isArchived && (
                      <DropdownMenuItem onClick={handleArchive}>
                        <Archive className="mr-2 size-4" />
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
                        <Trash2 className="mr-2 size-4" />
                        {t("Delete")}
                      </DropdownMenuItem>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>
                <ChevronRight className="size-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
              </div>
            </CardAction>
          </CardHeader>

          <Separator />

          {/* Zone 2: Status + metadata */}
          <CardFooter className="gap-2">
            <StatusBadge status={status} />
            {hasError && errorMessage && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span
                      className="inline-flex"
                      onClick={(e) => e.preventDefault()}
                    >
                      <AlertTriangle className="size-3.5 text-destructive" />
                    </span>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{errorMessage}</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
            <Badge variant="outline">{language}</Badge>
            {mode && (
              <Badge variant="outline" className="gap-1">
                {mode === "upload" ? (
                  <Upload className="size-3" />
                ) : (
                  <Mic className="size-3" />
                )}
                {mode === "upload" ? t("Upload") : t("Live")}
              </Badge>
            )}
            <span className="ml-auto text-xs text-muted-foreground/70">
              {formatRelativeTime(createdAt)}
            </span>
          </CardFooter>

          {/* Zone 3: Processing progress (conditional) */}
          {isProcessing && (
            <div className="border-t px-4 pb-3 pt-2">
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  {processingStep && (
                    <span className="capitalize">{processingStep}</span>
                  )}
                  <span className="tabular-nums">
                    {processingProgress ?? 0}%
                  </span>
                </div>
                <Progress value={processingProgress ?? 0} />
              </div>
            </div>
          )}
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
