export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-muted/40 px-4">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-bold">Tocky</h1>
        <p className="text-muted-foreground text-sm">Medical Scribe</p>
      </div>
      {children}
    </div>
  )
}
