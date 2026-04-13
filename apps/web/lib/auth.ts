const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

interface UserData {
  id: string
  name: string
  email: string
  role: string
  banned: boolean
  ban_reason: string | null
  created_at: string
}

interface SessionData {
  user: UserData
}

async function authFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  })
  if (!res.ok) {
    const body = await res.text().catch(() => "")
    throw new Error(body || `Auth error ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export async function signIn(
  email: string,
  password: string
): Promise<SessionData> {
  return authFetch<SessionData>("/api/v1/auth/sign-in", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  })
}

export async function signUp(
  name: string,
  email: string,
  password: string
): Promise<SessionData> {
  return authFetch<SessionData>("/api/v1/auth/sign-up", {
    method: "POST",
    body: JSON.stringify({ name, email, password }),
  })
}

export async function signOut(): Promise<void> {
  return authFetch<void>("/api/v1/auth/sign-out", {
    method: "POST",
  })
}

export async function refreshSession(): Promise<SessionData> {
  return authFetch<SessionData>("/api/v1/auth/refresh", {
    method: "POST",
  })
}

export async function getSession(): Promise<SessionData> {
  return authFetch<SessionData>("/api/v1/auth/session")
}

export type { UserData, SessionData }
