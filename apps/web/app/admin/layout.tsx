import { AppSidebar } from "@/components/app-sidebar"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@workspace/ui/components/sidebar"

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <SidebarProvider>
      <AppSidebar variant="admin" />
      <SidebarInset>
        <header className="flex h-14 items-center gap-2 border-b px-4 lg:px-6">
          <SidebarTrigger />
        </header>
        <main className="flex-1 overflow-auto px-4 py-6 lg:px-6">
          {children}
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}
