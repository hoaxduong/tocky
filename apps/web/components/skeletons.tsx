import { Skeleton } from "@workspace/ui/components/skeleton"
import { Card, CardContent, CardHeader } from "@workspace/ui/components/card"

export function ConsultationCardSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-5 w-16 rounded-full" />
        </div>
        <Skeleton className="mt-1 h-3.5 w-20" />
        <Skeleton className="mt-1 h-4 w-24" />
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-1.5">
          <Skeleton className="h-5 w-14 rounded-full" />
          <Skeleton className="h-5 w-16 rounded-full" />
        </div>
      </CardContent>
    </Card>
  )
}

export function ConsultationGridSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <ConsultationCardSkeleton key={i} />
      ))}
    </div>
  )
}

export function StatsCardSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-5 w-5 rounded" />
        </div>
      </CardHeader>
      <CardContent>
        <Skeleton className="h-8 w-12" />
      </CardContent>
    </Card>
  )
}

export function StatsGridSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <StatsCardSkeleton key={i} />
      ))}
    </div>
  )
}

export function ConsultationToolbarSkeleton() {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <Skeleton className="h-9 w-full sm:max-w-xs" />
      <div className="flex items-center gap-2">
        <Skeleton className="h-9 w-32" />
        <Skeleton className="h-9 w-32" />
        <Skeleton className="h-9 w-9" />
        <Skeleton className="h-9 w-9" />
      </div>
    </div>
  )
}

export function ScribePageSkeleton() {
  return (
    <div className="flex h-[calc(100dvh-theme(spacing.14)-theme(spacing.12))] flex-col gap-6">
      {/* Context bar */}
      <div className="space-y-2">
        <Skeleton className="h-4 w-48" />
        <div className="flex items-center gap-3">
          <Skeleton className="h-8 w-8 rounded-md" />
          <Skeleton className="h-7 w-48" />
          <Skeleton className="h-5 w-20 rounded-full" />
        </div>
        <div className="flex gap-3">
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-5 w-10 rounded-full" />
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-4 w-24" />
        </div>
      </div>

      {/* Recording controls */}
      <div className="flex items-center gap-4">
        <Skeleton className="h-10 w-28 rounded-md" />
        <Skeleton className="h-6 flex-1 rounded-full" />
      </div>

      {/* Two-column layout */}
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Transcript panel */}
        <div className="flex min-h-0 flex-col gap-3">
          <Skeleton className="h-5 w-24" />
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="space-y-1.5 rounded-md border p-3">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
              </div>
            ))}
          </div>
        </div>
        {/* SOAP editor panel */}
        <div className="flex min-h-0 flex-col gap-3">
          <Skeleton className="h-5 w-28" />
          <div className="space-y-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i}>
                <CardHeader className="pb-2">
                  <Skeleton className="h-5 w-20" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-16 w-full" />
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export function UploadProcessingSkeleton() {
  return (
    <div className="flex h-[calc(100dvh-theme(spacing.14)-theme(spacing.12))] flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b pb-4">
        <div className="flex items-center gap-3">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-5 w-10 rounded-full" />
          <Skeleton className="h-5 w-20 rounded-full" />
        </div>
        <Skeleton className="h-6 w-12" />
      </div>

      {/* Progress bar */}
      <Skeleton className="h-2 w-full rounded-full" />

      {/* Two-column layout */}
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="flex min-h-0 flex-col gap-3">
          <Skeleton className="h-6 w-28" />
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="space-y-1.5 rounded-md border p-3">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-2/3" />
              </div>
            ))}
          </div>
        </div>
        <div className="flex min-h-0 flex-col gap-3">
          <Skeleton className="h-6 w-24" />
          <div className="space-y-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="flex items-center gap-2.5">
                <Skeleton className="h-4 w-4 shrink-0 rounded-full" />
                <Skeleton className="h-4 w-40" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export function SOAPFormSkeleton() {
  return (
    <div className="space-y-6">
      {/* Context bar */}
      <div className="space-y-2">
        <Skeleton className="h-4 w-64" />
        <div className="flex items-center gap-3">
          <Skeleton className="h-8 w-8 rounded-md" />
          <Skeleton className="h-7 w-40" />
          <Skeleton className="h-5 w-16 rounded-full" />
        </div>
        <div className="flex gap-3">
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-5 w-10 rounded-full" />
          <Skeleton className="h-4 w-24" />
        </div>
      </div>
      {/* Summary stats */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-lg border p-3">
            <Skeleton className="h-8 w-12" />
            <Skeleton className="mt-1 h-3 w-16" />
          </div>
        ))}
      </div>
      {/* SOAP sections */}
      {Array.from({ length: 4 }).map((_, i) => (
        <Card key={i}>
          <CardHeader>
            <Skeleton className="h-5 w-24" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-24 w-full" />
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
