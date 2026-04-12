import { AppSidebar } from "@/components/app-sidebar"

export default function AppLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex min-h-screen">
      <AppSidebar variant="app" />
      <main className="flex-1 overflow-auto p-8">{children}</main>
    </div>
  )
}
