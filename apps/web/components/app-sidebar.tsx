"use client"

import { useExtracted } from "next-intl"
import { useLocale } from "next-intl"
import { useRouter } from "next/navigation"
import {
  type LucideIcon,
  ChevronsUpDown,
  Globe,
  LayoutDashboard,
  LogOut,
  Moon,
  Stethoscope,
  Sun,
  Users,
} from "lucide-react"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@workspace/ui/components/sidebar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@workspace/ui/components/dropdown-menu"
import { Avatar, AvatarFallback } from "@workspace/ui/components/avatar"
import { useTheme } from "next-themes"
import { signOut, useSession } from "@/lib/auth-client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { LOCALE_COOKIE, SUPPORTED_LOCALES } from "@/i18n/config"

const LOCALE_LABELS: Record<string, string> = {
  en: "English",
  vi: "Tiếng Việt",
  ar: "العربية",
}

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

function getInitials(name?: string | null, email?: string | null): string {
  if (name) {
    return name
      .split(" ")
      .map((w) => w[0])
      .join("")
      .toUpperCase()
      .slice(0, 2)
  }
  if (email) return email.charAt(0).toUpperCase()
  return "?"
}

export function AppSidebar({ variant }: AppSidebarProps) {
  const t = useExtracted()
  const pathname = usePathname()
  const locale = useLocale()
  const router = useRouter()
  const { data: session } = useSession()
  const { theme, setTheme } = useTheme()

  const navItems = variant === "admin" ? ADMIN_NAV : APP_NAV
  const title = variant === "admin" ? "Tốc ký AI Admin" : "Tốc ký AI"
  const user = session?.user
  const initials = getInitials(user?.name, user?.email)

  function handleLocaleChange(value: string) {
    document.cookie = `${LOCALE_COOKIE}=${value};path=/;max-age=31536000`
    router.refresh()
  }

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="flex h-14 flex-row items-center border-b px-4">
        <span className="text-lg font-bold group-data-[collapsible=icon]:hidden">
          {title}
        </span>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>{t("Navigation")}</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => {
                const isActive = item.exact
                  ? pathname === item.href
                  : pathname.startsWith(item.href)
                return (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton
                      asChild
                      isActive={isActive}
                      tooltip={item.label}
                    >
                      <Link href={item.href}>
                        <item.icon />
                        <span>{item.label}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton
                  size="lg"
                  tooltip={user?.name ?? user?.email ?? t("Account")}
                >
                  <Avatar className="h-8 w-8 rounded-lg">
                    <AvatarFallback className="rounded-lg">
                      {initials}
                    </AvatarFallback>
                  </Avatar>
                  <div className="grid flex-1 text-left text-sm leading-tight">
                    <span className="truncate font-medium">
                      {user?.name ?? t("Account")}
                    </span>
                    <span className="text-muted-foreground truncate text-xs">
                      {user?.email}
                    </span>
                  </div>
                  <ChevronsUpDown className="ml-auto size-4" />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                className="w-(--radix-dropdown-menu-trigger-width) min-w-56 rounded-lg"
                side="top"
                align="end"
                sideOffset={4}
              >
                <DropdownMenuLabel className="p-0 font-normal">
                  <div className="flex items-center gap-2 px-1 py-1.5 text-left text-sm">
                    <Avatar className="h-8 w-8 rounded-lg">
                      <AvatarFallback className="rounded-lg">
                        {initials}
                      </AvatarFallback>
                    </Avatar>
                    <div className="grid flex-1 text-left text-sm leading-tight">
                      <span className="truncate font-medium">
                        {user?.name ?? t("Account")}
                      </span>
                      <span className="text-muted-foreground truncate text-xs">
                        {user?.email}
                      </span>
                    </div>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuGroup>
                  <DropdownMenuSub>
                    <DropdownMenuSubTrigger>
                      <Sun className="mr-2 size-4 dark:hidden" />
                      <Moon className="mr-2 hidden size-4 dark:block" />
                      {t("Theme")}
                    </DropdownMenuSubTrigger>
                    <DropdownMenuSubContent>
                      <DropdownMenuRadioGroup
                        value={theme}
                        onValueChange={setTheme}
                      >
                        <DropdownMenuRadioItem value="light">
                          {t("Light")}
                        </DropdownMenuRadioItem>
                        <DropdownMenuRadioItem value="dark">
                          {t("Dark")}
                        </DropdownMenuRadioItem>
                        <DropdownMenuRadioItem value="system">
                          {t("System")}
                        </DropdownMenuRadioItem>
                      </DropdownMenuRadioGroup>
                    </DropdownMenuSubContent>
                  </DropdownMenuSub>
                  <DropdownMenuSub>
                    <DropdownMenuSubTrigger>
                      <Globe className="mr-2 size-4" />
                      {t("Language")}
                    </DropdownMenuSubTrigger>
                    <DropdownMenuSubContent>
                      <DropdownMenuRadioGroup
                        value={locale}
                        onValueChange={handleLocaleChange}
                      >
                        {SUPPORTED_LOCALES.map((loc) => (
                          <DropdownMenuRadioItem key={loc} value={loc}>
                            {LOCALE_LABELS[loc]}
                          </DropdownMenuRadioItem>
                        ))}
                      </DropdownMenuRadioGroup>
                    </DropdownMenuSubContent>
                  </DropdownMenuSub>
                </DropdownMenuGroup>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => signOut()}>
                  <LogOut className="mr-2 size-4" />
                  {t("Sign Out")}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
