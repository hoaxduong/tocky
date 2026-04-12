"use client"

import { createAuthClient } from "better-auth/react"
import { adminClient, jwtClient } from "better-auth/client/plugins"

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const authClient: any = createAuthClient({
  plugins: [adminClient(), jwtClient()],
})

export const { signIn, signUp, useSession, signOut } = authClient as {
  signIn: typeof authClient.signIn
  signUp: typeof authClient.signUp
  useSession: typeof authClient.useSession
  signOut: typeof authClient.signOut
}
