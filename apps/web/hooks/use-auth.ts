"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  getSession,
  signOut as authSignOut,
  type SessionData,
} from "@/lib/auth"

export function useSession() {
  return useQuery<SessionData>({
    queryKey: ["session"],
    queryFn: getSession,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })
}

export function useSignOut() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: authSignOut,
    onSuccess: () => {
      queryClient.clear()
      window.location.href = "/sign-in"
    },
  })
}
