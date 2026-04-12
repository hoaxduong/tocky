import { cookies } from "next/headers"
import { redirect } from "next/navigation"
import { jwtVerify, importSPKI } from "jose"
import { AppSidebar } from "@/components/app-sidebar"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@workspace/ui/components/sidebar"

async function getTokenPayload(token: string) {
  const pem = process.env.NEXT_PUBLIC_JWT_PUBLIC_KEY ?? ""
  if (!pem) return null
  try {
    const key = await importSPKI(pem, "ES256")
    const { payload } = await jwtVerify(token, key, {
      issuer: "tocky",
      algorithms: ["ES256"],
    })
    return payload as { sub: string; role: string }
  } catch {
    return null
  }
}

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const cookieStore = await cookies()
  const accessToken = cookieStore.get("tocky_access")?.value

  if (!accessToken) {
    redirect("/sign-in")
  }

  const payload = await getTokenPayload(accessToken)
  if (!payload || payload.role !== "admin") {
    redirect("/dashboard")
  }

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
