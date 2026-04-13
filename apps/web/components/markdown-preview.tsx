import ReactMarkdown from "react-markdown"
import remarkBreaks from "remark-breaks"

interface MarkdownPreviewProps {
  children: string
}

export function MarkdownPreview({ children }: MarkdownPreviewProps) {
  return <ReactMarkdown remarkPlugins={[remarkBreaks]}>{children}</ReactMarkdown>
}
