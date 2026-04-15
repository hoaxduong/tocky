"use client"

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react"
import { useEditor, EditorContent } from "@tiptap/react"
import StarterKit from "@tiptap/starter-kit"
import Placeholder from "@tiptap/extension-placeholder"
import TurndownService from "turndown"
import { marked } from "marked"
import { useExtracted } from "next-intl"
import { Bold, Italic, List, ListOrdered } from "lucide-react"
import { cn } from "@workspace/ui/lib/utils"

interface SOAPSectionEditorProps {
  value: string
  onSave: (value: string) => void
  disabled?: boolean
  placeholder?: string
}

// Singleton turndown instance — configured once
const turndown = new TurndownService({
  headingStyle: "atx",
  bulletListMarker: "-",
})

function htmlToMarkdown(html: string): string {
  return turndown.turndown(html).trim()
}

function markdownToHtml(md: string): string {
  if (!md) return ""
  // marked.parse returns string synchronously with {async: false}
  return marked.parse(md, { async: false, breaks: true }) as string
}

export function SOAPSectionEditor({
  value,
  onSave,
  disabled,
  placeholder,
}: SOAPSectionEditorProps) {
  const t = useExtracted()
  const [isFocused, setIsFocused] = useState(false)
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const onSaveRef = useRef(onSave)
  const lastSavedRef = useRef(value)

  useLayoutEffect(() => {
    onSaveRef.current = onSave
  }, [onSave])

  const editor = useEditor({
    immediatelyRender: false,
    extensions: [
      StarterKit.configure({
        heading: false,
        codeBlock: false,
        code: false,
        blockquote: false,
        horizontalRule: false,
      }),
      Placeholder.configure({
        placeholder: placeholder || t("Start typing..."),
      }),
    ],
    content: markdownToHtml(value),
    editable: !disabled,
    editorProps: {
      attributes: {
        class: cn(
          "prose prose-sm max-w-none dark:prose-invert",
          "min-h-[40px] outline-none",
          "focus:outline-none",
          "[&_p]:my-1 [&_ul]:my-1 [&_ol]:my-1"
        ),
      },
    },
    onFocus: () => setIsFocused(true),
    onBlur: ({ editor: ed }) => {
      setIsFocused(false)
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
      const md = htmlToMarkdown(ed.getHTML())
      if (md !== lastSavedRef.current) {
        lastSavedRef.current = md
        onSaveRef.current(md)
      }
    },
    onUpdate: ({ editor: ed }) => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
      saveTimerRef.current = setTimeout(() => {
        const md = htmlToMarkdown(ed.getHTML())
        if (md !== lastSavedRef.current) {
          lastSavedRef.current = md
          onSaveRef.current(md)
        }
      }, 1500)
    },
  })

  const syncContent = useCallback(
    (newValue: string) => {
      if (!editor) return
      const currentMd = htmlToMarkdown(editor.getHTML())
      if (currentMd !== newValue && !editor.isFocused) {
        editor.commands.setContent(markdownToHtml(newValue))
        lastSavedRef.current = newValue
      }
    },
    [editor]
  )

  useEffect(() => {
    syncContent(value)
  }, [value, syncContent])

  useEffect(() => {
    if (editor) editor.setEditable(!disabled)
  }, [editor, disabled])

  useEffect(() => {
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
    }
  }, [])

  if (!editor) return null

  return (
    <div
      className={cn(
        "group relative rounded-md transition-colors",
        isFocused
          ? "bg-accent/30 ring-1 ring-primary/20"
          : "hover:bg-accent/20",
        disabled && "opacity-60"
      )}
    >
      {!disabled && isFocused && (
        <div className="absolute -top-8 left-0 z-10 flex items-center gap-0.5 rounded-lg border bg-background px-1 py-0.5 shadow-md">
          <InlineButton
            onClick={() => editor.chain().focus().toggleBold().run()}
            isActive={editor.isActive("bold")}
            title={t("Bold")}
          >
            <Bold className="h-3 w-3" />
          </InlineButton>
          <InlineButton
            onClick={() => editor.chain().focus().toggleItalic().run()}
            isActive={editor.isActive("italic")}
            title={t("Italic")}
          >
            <Italic className="h-3 w-3" />
          </InlineButton>
          <div className="mx-0.5 h-3.5 w-px bg-border" />
          <InlineButton
            onClick={() => editor.chain().focus().toggleBulletList().run()}
            isActive={editor.isActive("bulletList")}
            title={t("Bullet List")}
          >
            <List className="h-3 w-3" />
          </InlineButton>
          <InlineButton
            onClick={() => editor.chain().focus().toggleOrderedList().run()}
            isActive={editor.isActive("orderedList")}
            title={t("Numbered List")}
          >
            <ListOrdered className="h-3 w-3" />
          </InlineButton>
        </div>
      )}

      <div className="px-3 py-2">
        <EditorContent editor={editor} />
      </div>
    </div>
  )
}

function InlineButton({
  onClick,
  isActive,
  children,
  title,
}: {
  onClick: () => void
  isActive?: boolean
  children: React.ReactNode
  title: string
}) {
  return (
    <button
      type="button"
      onMouseDown={(e) => e.preventDefault()}
      onClick={onClick}
      title={title}
      className={cn(
        "flex h-6 w-6 items-center justify-center rounded transition-colors",
        isActive
          ? "bg-primary text-primary-foreground"
          : "text-muted-foreground hover:bg-accent hover:text-foreground"
      )}
    >
      {children}
    </button>
  )
}
