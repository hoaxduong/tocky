"use client"

interface ScribeLayoutProps {
  children: React.ReactNode
}

export function ScribeLayout({ children }: ScribeLayoutProps) {
  return (
    <div className="grid h-[calc(100vh-12rem)] grid-cols-1 gap-6 lg:grid-cols-2">
      {children}
    </div>
  )
}

function ScribeLayoutLeft({ children }: { children: React.ReactNode }) {
  return <div className="flex flex-col gap-4 overflow-hidden">{children}</div>
}

function ScribeLayoutRight({ children }: { children: React.ReactNode }) {
  return <div className="flex flex-col overflow-hidden">{children}</div>
}

ScribeLayout.Left = ScribeLayoutLeft
ScribeLayout.Right = ScribeLayoutRight
