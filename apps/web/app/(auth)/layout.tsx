export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-muted/40 px-4">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-bold">Tốc ký AI</h1>
        <p className="text-sm text-muted-foreground">AI Medical Scribe</p>
      </div>
      {children}
    </div>
  )
}
