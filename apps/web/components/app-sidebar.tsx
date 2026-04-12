"use client"

import { useExtracted } from "next-intl"
import {
  type LucideIcon,
  LayoutDashboard,
  LogOut,
  Stethoscope,
  Users,
} from "lucide-react"
import { Button } from "@workspace/ui/components/button"
import { Separator } from "@workspace/ui/components/separator"
import { signOut, useSession } from "@/lib/auth-client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { LocaleSwitcher } from "@/components/locale-switcher"

interface NavItem {
  href: string
  icon: LucideIcon
  label: string
  exact?: boolean
}

const APP_NAV: NavItem[] = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/consultations", icon: Stethoscope, label: "Consultations" },
]

const ADMIN_NAV: NavItem[] = [
  { href: "/admin", icon: LayoutDashboard, label: "Dashboard", exact: true },
  { href: "/admin/users", icon: Users, label: "Users" },
  { href: "/admin/consultations", icon: Stethoscope, label: "Consultations" },
]

interface AppSidebarProps {
  variant: "app" | "admin"
}

export function AppSidebar({ variant }: AppSidebarProps) {
  const t = useExtracted()
  const pathname = usePathname()
  const { data: session } = useSession()

  const navItems = variant === "admin" ? ADMIN_NAV : APP_NAV
  const title = variant === "admin" ? "Tocky Admin" : "Tocky"

  return (
    <aside className="bg-card flex w-64 flex-col border-r">
      <div className="p-6">
        <h2 className="text-xl font-bold">{title}</h2>
      </div>
      <Separator />
      <nav className="flex-1 space-y-1 p-4">
        {navItems.map((item) => {
          const isActive = item.exact
            ? pathname === item.href
            : pathname.startsWith(item.href)
          return (
            <Link key={item.href} href={item.href}>
              <Button
                variant={isActive ? "secondary" : "ghost"}
                className="w-full justify-start gap-2"
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </Button>
            </Link>
          )
        })}
      </nav>
      <Separator />
      <div className="space-y-3 p-4">
        <LocaleSwitcher />
        <p className="text-muted-foreground truncate text-sm">
          {session?.user?.email}
        </p>
        <Button
          variant="ghost"
          className="w-full justify-start gap-2"
          onClick={() => signOut()}
        >
          <LogOut className="h-4 w-4" />
          {t("Sign Out")}
        </Button>
      </div>
    </aside>
  )
}
