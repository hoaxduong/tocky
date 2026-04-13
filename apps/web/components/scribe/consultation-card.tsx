"use client"

import { useState } from "react"
import { useExtracted } from "next-intl"
import { Archive, ChevronRight, MoreHorizontal, Trash2 } from "lucide-react"
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
}

export function ConsultationCard({
  id,
  title,
  language,
  status,
  createdAt,
}: ConsultationCardProps) {
  const t = useExtracted()
  const [deleteOpen, setDeleteOpen] = useState(false)
  const archiveConsultation = useArchiveConsultation()
  const deleteConsultation = useDeleteConsultation()

  const isArchived = status === "archived"

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
        <Card className="group cursor-pointer transition-all hover:border-primary/30 hover:shadow-sm">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">
                {title || t("New Consultation")}
              </CardTitle>
              <div className="flex items-center gap-1">
                <StatusBadge status={status} />
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-muted-foreground h-7 w-7 opacity-0 group-hover:opacity-100"
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
                <ChevronRight className="text-muted-foreground h-4 w-4 opacity-0 transition-opacity group-hover:opacity-100" />
              </div>
            </div>
            <CardDescription>
              {new Date(createdAt).toLocaleDateString()}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Badge variant="outline">{language}</Badge>
          </CardContent>
        </Card>
      </Link>

      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t("Delete Consultation?")}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t(
                "This will permanently delete this consultation and all its data. This action cannot be undone.",
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("Cancel")}</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {t("Delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
