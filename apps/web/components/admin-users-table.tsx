"use client"

import { useState } from "react"
import { useExtracted } from "next-intl"
import { type ColumnDef } from "@tanstack/react-table"
import {
  MoreHorizontal,
  Plus,
  Shield,
  ShieldOff,
  Ban,
  Undo2,
  Trash2,
} from "lucide-react"
import { DataTable } from "@workspace/ui/components/data-table"
import { Button } from "@workspace/ui/components/button"
import { Input } from "@workspace/ui/components/input"
import { Label } from "@workspace/ui/components/label"
import { Badge } from "@workspace/ui/components/badge"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@workspace/ui/components/dialog"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@workspace/ui/components/alert-dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@workspace/ui/components/dropdown-menu"
import {
  useUsers,
  useCreateUser,
  useUpdateUserRole,
  useBanUser,
  useUnbanUser,
  useDeleteUser,
} from "@/hooks/use-users"
import { toast } from "sonner"

interface User {
  id: string
  name: string
  email: string
  role: string
  banned: boolean
  ban_reason: string | null
  created_at: string
}

function UserActions({ user }: { user: User }) {
  const t = useExtracted()
  const updateRole = useUpdateUserRole()
  const banUser = useBanUser()
  const unbanUser = useUnbanUser()
  const deleteUser = useDeleteUser()

  return (
    <AlertDialog>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="h-8 w-8 p-0">
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {user.role === "admin" ? (
            <DropdownMenuItem
              onClick={() =>
                updateRole.mutate(
                  { userId: user.id, role: "doctor" },
                  {
                    onSuccess: () => toast.success(t("Role updated to doctor")),
                  }
                )
              }
            >
              <ShieldOff className="mr-2 h-4 w-4" />
              {t("Set as Doctor")}
            </DropdownMenuItem>
          ) : (
            <DropdownMenuItem
              onClick={() =>
                updateRole.mutate(
                  { userId: user.id, role: "admin" },
                  {
                    onSuccess: () => toast.success(t("Role updated to admin")),
                  }
                )
              }
            >
              <Shield className="mr-2 h-4 w-4" />
              {t("Set as Admin")}
            </DropdownMenuItem>
          )}
          <DropdownMenuSeparator />
          {user.banned ? (
            <DropdownMenuItem
              onClick={() =>
                unbanUser.mutate(user.id, {
                  onSuccess: () => toast.success(t("User unbanned")),
                })
              }
            >
              <Undo2 className="mr-2 h-4 w-4" />
              {t("Unban")}
            </DropdownMenuItem>
          ) : (
            <DropdownMenuItem
              onClick={() =>
                banUser.mutate(
                  { userId: user.id },
                  {
                    onSuccess: () => toast.success(t("User banned")),
                  }
                )
              }
            >
              <Ban className="mr-2 h-4 w-4" />
              {t("Ban")}
            </DropdownMenuItem>
          )}
          <DropdownMenuSeparator />
          <AlertDialogTrigger asChild>
            <DropdownMenuItem className="text-destructive">
              <Trash2 className="mr-2 h-4 w-4" />
              {t("Delete")}
            </DropdownMenuItem>
          </AlertDialogTrigger>
        </DropdownMenuContent>
      </DropdownMenu>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{t("Delete User")}</AlertDialogTitle>
          <AlertDialogDescription>
            {t(
              "Are you sure you want to delete this user? This action cannot be undone."
            )}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>{t("Cancel")}</AlertDialogCancel>
          <AlertDialogAction
            onClick={() =>
              deleteUser.mutate(user.id, {
                onSuccess: () => toast.success(t("User deleted")),
              })
            }
          >
            {t("Delete")}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}

function CreateUserDialog() {
  const t = useExtracted()
  const createUser = useCreateUser()
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [role, setRole] = useState("doctor")

  function resetForm() {
    setName("")
    setEmail("")
    setPassword("")
    setRole("doctor")
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    try {
      await createUser.mutateAsync({ name, email, password, role })
      toast.success(t("User created"))
      setOpen(false)
      resetForm()
    } catch {
      toast.error(t("Failed to create user"))
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        setOpen(v)
        if (!v) resetForm()
      }}
    >
      <DialogTrigger asChild>
        <Button className="gap-2">
          <Plus className="h-4 w-4" />
          {t("Add User")}
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{t("Add User")}</DialogTitle>
          <DialogDescription>
            {t("Create a new user account.")}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="create-name">{t("Name")}</Label>
            <Input
              id="create-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="create-email">{t("Email")}</Label>
            <Input
              id="create-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="create-password">{t("Password")}</Label>
            <Input
              id="create-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="create-role">{t("Role")}</Label>
            <select
              id="create-role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
            >
              <option value="doctor">{t("Doctor")}</option>
              <option value="admin">{t("Admin")}</option>
            </select>
          </div>
          <DialogFooter>
            <Button
              type="submit"
              className="w-full"
              disabled={createUser.isPending}
            >
              {createUser.isPending ? t("Creating...") : t("Create")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export function AdminUsersTable() {
  const t = useExtracted()
  const [search, setSearch] = useState("")
  const { data, isLoading } = useUsers(0, 100, search || undefined)

  const columns: ColumnDef<User>[] = [
    {
      accessorKey: "name",
      header: t("Name"),
    },
    {
      accessorKey: "email",
      header: t("Email"),
    },
    {
      accessorKey: "role",
      header: t("Role"),
      cell: ({ row }) => (
        <Badge
          variant={row.original.role === "admin" ? "default" : "secondary"}
        >
          {row.original.role}
        </Badge>
      ),
    },
    {
      accessorKey: "banned",
      header: t("Status"),
      cell: ({ row }) =>
        row.original.banned ? (
          <Badge variant="destructive">{t("Banned")}</Badge>
        ) : (
          <Badge variant="outline">{t("Active")}</Badge>
        ),
    },
    {
      accessorKey: "created_at",
      header: t("Created"),
      cell: ({ row }) => new Date(row.original.created_at).toLocaleDateString(),
    },
    {
      id: "actions",
      cell: ({ row }) => <UserActions user={row.original} />,
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <Input
          placeholder={t("Search users...")}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm"
        />
        <CreateUserDialog />
      </div>
      {isLoading ? (
        <div className="py-8 text-center text-muted-foreground">
          {t("Loading...")}
        </div>
      ) : (
        <DataTable columns={columns} data={data?.items ?? []} />
      )}
    </div>
  )
}
