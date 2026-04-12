"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"

interface User {
  id: string
  name: string
  email: string
  role: string
  banned: boolean
  ban_reason: string | null
  created_at: string
}

interface UserListResponse {
  items: User[]
  total: number
  offset: number
  limit: number
}

interface CreateUserInput {
  name: string
  email: string
  password: string
  role?: string
}

export function useUsers(offset = 0, limit = 20, search?: string) {
  const params = new URLSearchParams({
    offset: String(offset),
    limit: String(limit),
  })
  if (search) params.set("search", search)

  return useQuery({
    queryKey: ["admin-users", offset, limit, search],
    queryFn: () =>
      apiFetch<UserListResponse>(`/api/v1/admin/users?${params}`),
  })
}

export function useCreateUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: CreateUserInput) =>
      apiFetch<User>("/api/v1/admin/users", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] })
    },
  })
}

export function useUpdateUserRole() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      apiFetch<User>(`/api/v1/admin/users/${userId}/role`, {
        method: "PATCH",
        body: JSON.stringify({ role }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] })
    },
  })
}

export function useBanUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      userId,
      banReason,
    }: {
      userId: string
      banReason?: string
    }) =>
      apiFetch<User>(`/api/v1/admin/users/${userId}/ban`, {
        method: "POST",
        body: JSON.stringify({ ban_reason: banReason }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] })
    },
  })
}

export function useUnbanUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (userId: string) =>
      apiFetch<User>(`/api/v1/admin/users/${userId}/unban`, {
        method: "POST",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] })
    },
  })
}

export function useDeleteUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (userId: string) =>
      apiFetch<void>(`/api/v1/admin/users/${userId}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] })
    },
  })
}
