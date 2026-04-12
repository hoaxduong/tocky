import { AppSidebar } from "@/components/app-sidebar"

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex min-h-screen">
      <AppSidebar variant="admin" />
      <main className="flex-1 overflow-auto p-8">{children}</main>
    </div>
  )
}
