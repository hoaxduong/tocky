"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { zodResolver } from "@hookform/resolvers/zod"
import { useExtracted } from "next-intl"
import { Button } from "@workspace/ui/components/button"
import { Input } from "@workspace/ui/components/input"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@workspace/ui/components/card"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@workspace/ui/components/form"
import { signIn } from "@/lib/auth"
import Link from "next/link"
import { toast } from "sonner"

const signInSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
})

type SignInValues = z.infer<typeof signInSchema>

const demoUsers = [
  { label: "Doctor", email: "doctor@tocky.ai", password: "doctor123" },
  { label: "Admin", email: "admin@tocky.ai", password: "admin123" },
]

export function SignInForm() {
  const t = useExtracted()
  const [error, setError] = useState("")
  const form = useForm<SignInValues>({
    resolver: zodResolver(signInSchema),
    defaultValues: { email: "", password: "" },
  })

  async function onSubmit(values: SignInValues) {
    setError("")
    try {
      await signIn(values.email, values.password)
      window.location.href = "/dashboard"
    } catch {
      setError(t("Invalid email or password"))
      toast.error(t("Invalid email or password"))
    }
  }

  return (
    <div className="flex w-full max-w-md flex-col gap-4">
      <Card>
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
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("Email")}</FormLabel>
                    <FormControl>
                      <Input type="email" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("Password")}</FormLabel>
                    <FormControl>
                      <Input type="password" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button
                type="submit"
                className="w-full"
                disabled={form.formState.isSubmitting}
              >
                {form.formState.isSubmitting
                  ? t("Loading...")
                  : t("Sign In")}
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>

      <div className="text-center text-sm text-muted-foreground">
        <p>{t("Demo Accounts")}</p>
        {demoUsers.map((user) => (
          <p key={user.email}>
            {user.label}: {user.email} / {user.password}
          </p>
        ))}
      </div>
    </div>
  )
}
