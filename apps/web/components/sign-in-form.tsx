"use client"

import { useState } from "react"
import { useExtracted } from "next-intl"
import { Button } from "@workspace/ui/components/button"
import { Input } from "@workspace/ui/components/input"
import { Label } from "@workspace/ui/components/label"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@workspace/ui/components/card"
import { signIn } from "@/lib/auth"
import Link from "next/link"
import { toast } from "sonner"

export function SignInForm() {
  const t = useExtracted()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError("")
    setLoading(true)
    try {
      await signIn(email, password)
      window.location.href = "/dashboard"
    } catch {
      setError("Invalid credentials")
      toast.error(t("Invalid credentials"))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>{t("Sign in to Tốc ký AI")}</CardTitle>
        <CardDescription>
          {t("Don't have an account?")}{" "}
          <Link href="/sign-up" className="text-primary underline">
            {t("Sign Up")}
          </Link>
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">{t("Email")}</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">{t("Password")}</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          {error && <p className="text-destructive text-sm">{error}</p>}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? t("Loading...") : t("Sign In")}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
