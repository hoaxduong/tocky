"use client"

interface ScribeLayoutProps {
  children: React.ReactNode
}

export function ScribeLayout({ children }: ScribeLayoutProps) {
  return (
    <div className="grid min-h-0 flex-1 grid-cols-1 gap-6 lg:grid-cols-2">
      {children}
    </div>
  )
}

function ScribeLayoutLeft({ children }: { children: React.ReactNode }) {
  return <div className="flex min-h-0 flex-col">{children}</div>
}

function ScribeLayoutRight({ children }: { children: React.ReactNode }) {
  return <div className="flex min-h-0 flex-col">{children}</div>
}

ScribeLayout.Left = ScribeLayoutLeft
ScribeLayout.Right = ScribeLayoutRight
