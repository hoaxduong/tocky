"use client"

import { useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { useExtracted } from "next-intl"
import {
  Archive,
  LayoutGrid,
  List,
  MoreHorizontal,
  Search,
  SearchX,
  Stethoscope,
  Trash2,
} from "lucide-react"
import { Input } from "@workspace/ui/components/input"
import { Button } from "@workspace/ui/components/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@workspace/ui/components/select"
import { Tabs, TabsList, TabsTrigger } from "@workspace/ui/components/tabs"
import { Badge } from "@workspace/ui/components/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@workspace/ui/components/table"
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
import {
  type Consultation,
  useArchiveConsultation,
  useConsultations,
  useDeleteConsultation,
} from "@/hooks/use-consultation"
import { ConsultationCard } from "@/components/scribe/consultation-card"
import {
  ConsultationGridSkeleton,
  ConsultationToolbarSkeleton,
} from "@/components/skeletons"
import { PageHeader } from "@/components/page-header"
import { NewConsultationDialog } from "@/components/new-consultation-dialog"
import { EmptyState } from "@/components/empty-state"
import { StatusBadge } from "@/components/status-badge"
import { toast } from "sonner"

const PAGE_SIZE = 12

type SortOption = "newest" | "oldest" | "title" | "updated"
type ViewMode = "grid" | "table"

function formatRelativeTime(dateStr: string): string {
  const now = Date.now()
  const date = new Date(dateStr).getTime()
  const diffMs = now - date
  const diffSec = Math.floor(diffMs / 1000)
  const diffMin = Math.floor(diffSec / 60)
  const diffHr = Math.floor(diffMin / 60)
  const diffDay = Math.floor(diffHr / 24)

  const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" })

  if (diffDay > 30) return new Date(dateStr).toLocaleDateString()
  if (diffDay >= 1) return rtf.format(-diffDay, "day")
  if (diffHr >= 1) return rtf.format(-diffHr, "hour")
  if (diffMin >= 1) return rtf.format(-diffMin, "minute")
  return rtf.format(0, "second")
}

function sortItems(items: Consultation[], sort: SortOption): Consultation[] {
  return [...items].sort((a, b) => {
    switch (sort) {
      case "oldest":
        return (
          new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        )
      case "title":
        return (a.title || "").localeCompare(b.title || "")
      case "updated":
        return (
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        )
      case "newest":
      default:
        return (
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        )
    }
  })
}

export function ConsultationsList() {
  const t = useExtracted()
  const router = useRouter()
  const [tab, setTab] = useState<"active" | "archived">("active")
  const [search, setSearch] = useState("")
  const [sort, setSort] = useState<SortOption>("newest")
  const [language, setLanguage] = useState("all")
  const [view, setView] = useState<ViewMode>("grid")
  const [page, setPage] = useState(0)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)

  const { data, isLoading } = useConsultations(
    0,
    100,
    tab === "archived" ? "archived" : undefined
  )

  const archiveConsultation = useArchiveConsultation()
  const deleteConsultation = useDeleteConsultation()

  const items = useMemo(() => data?.items ?? [], [data?.items])

  const languages = useMemo(() => {
    const set = new Set(items.map((c) => c.language))
    return Array.from(set).sort()
  }, [items])

  const filtered = useMemo(() => {
    let result = items

    if (search) {
      const q = search.toLowerCase()
      result = result.filter(
        (c) =>
          c.title.toLowerCase().includes(q) ||
          c.patient_identifier?.toLowerCase().includes(q)
      )
    }

    if (language !== "all") {
      result = result.filter((c) => c.language === language)
    }

    return sortItems(result, sort)
  }, [items, search, sort, language])

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE)
  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  function resetFilters() {
    setSearch("")
    setSort("newest")
    setLanguage("all")
    setPage(0)
  }

  function handleTabChange(v: string) {
    setTab(v as "active" | "archived")
    resetFilters()
  }

  function handleArchive(e: React.MouseEvent, id: string) {
    e.stopPropagation()
    archiveConsultation.mutate(id, {
      onSuccess: () => toast.success(t("Consultation archived")),
      onError: () => toast.error(t("Failed to archive consultation")),
    })
  }

  function handleDelete() {
    if (!deleteTarget) return
    deleteConsultation.mutate(deleteTarget, {
      onSuccess: () => toast.success(t("Consultation deleted")),
      onError: () => toast.error(t("Failed to delete consultation")),
    })
    setDeleteTarget(null)
  }

  const hasFilters = search !== "" || language !== "all" || sort !== "newest"

  return (
    <div className="space-y-4">
      <PageHeader
        title={t("Consultations")}
        breadcrumbs={[
          { label: t("Dashboard"), href: "/dashboard" },
          { label: t("Consultations") },
        ]}
        actions={<NewConsultationDialog />}
      />

      <Tabs value={tab} onValueChange={handleTabChange}>
        <TabsList>
          <TabsTrigger value="active">{t("Active")}</TabsTrigger>
          <TabsTrigger value="archived">{t("Archived")}</TabsTrigger>
        </TabsList>
      </Tabs>

      {isLoading ? (
        <>
          <ConsultationToolbarSkeleton />
          <ConsultationGridSkeleton />
        </>
      ) : (
        <>
          {/* Toolbar */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative sm:max-w-xs sm:flex-1">
              <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder={t("Search consultations...")}
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value)
                  setPage(0)
                }}
                className="pl-9"
              />
            </div>
            <div className="flex items-center gap-2">
              {languages.length > 1 && (
                <Select
                  value={language}
                  onValueChange={(v) => {
                    setLanguage(v)
                    setPage(0)
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={t("Language")} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">{t("All Languages")}</SelectItem>
                    {languages.map((lang) => (
                      <SelectItem key={lang} value={lang}>
                        {lang}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
              <Select
                value={sort}
                onValueChange={(v) => {
                  setSort(v as SortOption)
                  setPage(0)
                }}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="newest">{t("Newest")}</SelectItem>
                  <SelectItem value="oldest">{t("Oldest")}</SelectItem>
                  <SelectItem value="title">{t("Title A-Z")}</SelectItem>
                  <SelectItem value="updated">
                    {t("Recently Updated")}
                  </SelectItem>
                </SelectContent>
              </Select>
              <div className="flex items-center rounded-md border">
                <Button
                  variant={view === "grid" ? "secondary" : "ghost"}
                  size="icon"
                  className="h-7 w-7 rounded-r-none"
                  onClick={() => setView("grid")}
                >
                  <LayoutGrid className="h-4 w-4" />
                </Button>
                <Button
                  variant={view === "table" ? "secondary" : "ghost"}
                  size="icon"
                  className="h-7 w-7 rounded-l-none"
                  onClick={() => setView("table")}
                >
                  <List className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>

          {/* Results count */}
          {filtered.length > 0 && (
            <p className="text-sm text-muted-foreground">
              {t("Showing {start}-{end} of {total} consultations", {
                start: String(page * PAGE_SIZE + 1),
                end: String(
                  Math.min((page + 1) * PAGE_SIZE, filtered.length)
                ),
                total: String(filtered.length),
              })}
            </p>
          )}

          {/* Content */}
          {filtered.length === 0 ? (
            hasFilters ? (
              <EmptyState
                icon={SearchX}
                title={t("No matching consultations")}
                description={t(
                  "Try adjusting your search or filters to find what you're looking for."
                )}
                action={
                  <Button variant="outline" onClick={resetFilters}>
                    {t("Clear Filters")}
                  </Button>
                }
              />
            ) : tab === "archived" ? (
              <EmptyState
                icon={Archive}
                title={t("No archived consultations")}
                description={t(
                  "Consultations you archive will appear here."
                )}
              />
            ) : (
              <EmptyState
                icon={Stethoscope}
                title={t("No consultations yet")}
                description={t(
                  "Start your first consultation to begin documenting patient encounters."
                )}
                action={<NewConsultationDialog />}
              />
            )
          ) : view === "grid" ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {paged.map((c) => (
                <ConsultationCard
                  key={c.id}
                  id={c.id}
                  title={c.title}
                  language={c.language}
                  status={c.status}
                  createdAt={c.created_at}
                  patientIdentifier={c.patient_identifier}
                  mode={c.mode}
                  processingProgress={c.processing_progress}
                  processingStep={c.processing_step}
                  errorMessage={c.error_message}
                />
              ))}
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("Title")}</TableHead>
                    <TableHead>{t("Patient")}</TableHead>
                    <TableHead>{t("Language")}</TableHead>
                    <TableHead>{t("Status")}</TableHead>
                    <TableHead>{t("Created")}</TableHead>
                    <TableHead className="w-10" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paged.map((c) => (
                    <TableRow
                      key={c.id}
                      className="cursor-pointer"
                      onClick={() => router.push(`/consultations/${c.id}`)}
                    >
                      <TableCell className="max-w-[200px] truncate font-medium">
                        {c.title || t("New Consultation")}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {c.patient_identifier || "-"}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{c.language}</Badge>
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={c.status} />
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatRelativeTime(c.created_at)}
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            {c.status !== "archived" && (
                              <DropdownMenuItem
                                onClick={(e) => handleArchive(e, c.id)}
                              >
                                <Archive className="mr-2 h-4 w-4" />
                                {t("Archive")}
                              </DropdownMenuItem>
                            )}
                            {c.status === "archived" && (
                              <DropdownMenuItem
                                className="text-destructive focus:text-destructive"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  setDeleteTarget(c.id)
                                }}
                              >
                                <Trash2 className="mr-2 h-4 w-4" />
                                {t("Delete")}
                              </DropdownMenuItem>
                            )}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                {t("Page {current} of {total}", {
                  current: String(page + 1),
                  total: String(totalPages),
                })}
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page === 0}
                  onClick={() => setPage((p) => p - 1)}
                >
                  {t("Previous")}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages - 1}
                  onClick={() => setPage((p) => p + 1)}
                >
                  {t("Next")}
                </Button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Delete confirmation */}
      <AlertDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
      >
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
    </div>
  )
}
