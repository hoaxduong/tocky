import { cookies } from "next/headers"
import { redirect } from "next/navigation"
import { AppSidebar } from "@/components/app-sidebar"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@workspace/ui/components/sidebar"

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const cookieStore = await cookies()
  const accessToken = cookieStore.get("tocky_access")?.value

  if (!accessToken) {
    redirect("/sign-in")
  }

  return (
    <SidebarProvider>
      <AppSidebar variant="app" />
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
