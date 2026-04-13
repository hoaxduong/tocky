import { refreshSession } from "@/lib/auth"

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: string
  ) {
    super(`API error ${status}: ${body}`)
  }
}

let refreshPromise: Promise<unknown> | null = null

async function tryRefresh(): Promise<boolean> {
  try {
    if (!refreshPromise) {
      refreshPromise = refreshSession()
    }
    await refreshPromise
    return true
  } catch {
    return false
  } finally {
    refreshPromise = null
  }
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  })

  // On 401, try refreshing the access token once
  if (res.status === 401) {
    const refreshed = await tryRefresh()
    if (refreshed) {
      const retry = await fetch(`${API_BASE}${path}`, {
        ...options,
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...options?.headers,
        },
      })
      if (retry.ok) {
        if (retry.status === 204) return undefined as T
        return retry.json()
      }
      if (retry.status === 401) {
        window.location.href = "/sign-in"
        throw new ApiError(401, "Session expired")
      }
      throw new ApiError(retry.status, await retry.text())
    }
    window.location.href = "/sign-in"
    throw new ApiError(401, "Session expired")
  }

  if (!res.ok) {
    throw new ApiError(res.status, await res.text())
  }

  if (res.status === 204) {
    return undefined as T
  }

  return res.json()
}
