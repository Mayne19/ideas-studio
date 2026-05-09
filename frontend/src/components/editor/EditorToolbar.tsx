import { useRef, useState } from 'react'
import type { Editor } from '@tiptap/react'
import {
  Bold,
  Italic,
  Underline,
  Heading1,
  Heading2,
  Heading3,
  Heading4,
  Pilcrow,
  List,
  ListOrdered,
  CheckSquare,
  Quote,
  Terminal,
  Minus,
  Link,
  Image,
  Save,
  Loader2,
} from 'lucide-react'
import { uploadMedia } from '@/api/media'

function ToolBtn({
  onClick,
  active,
  disabled,
  title,
  children,
}: {
  onClick: () => void
  active?: boolean
  disabled?: boolean
  title: string
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-[8px] transition-colors ${
        active
          ? 'bg-accent text-white'
          : 'text-secondary hover:bg-[#e5e5e7] hover:text-primary'
      } disabled:cursor-not-allowed disabled:opacity-40`}
    >
      {children}
    </button>
  )
}

function Sep() {
  return <div className="my-1 h-px w-6 shrink-0 bg-border" />
}

export default function EditorToolbar({
  editor,
  onSave,
  projectId,
  disabled = false,
}: {
  editor: Editor | null
  onSave?: () => void
  projectId?: string
  disabled?: boolean
}) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)

  if (!editor) return null

  function handleLink() {
    const prev = editor!.getAttributes('link').href as string | undefined
    const url = window.prompt('URL du lien', prev ?? 'https://')
    if (url === null) return
    if (url === '') {
      editor!.chain().focus().extendMarkRange('link').unsetLink().run()
    } else {
      editor!.chain().focus().extendMarkRange('link').setLink({ href: url }).run()
    }
  }

  async function handleImageFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file || !projectId) return

    setUploading(true)
    try {
      const media = await uploadMedia(projectId, file)
      editor!.chain().focus().setImage({ src: media.url, alt: media.alt_text ?? media.filename ?? '' }).run()
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  return (
    <div className={`flex h-full flex-col items-center gap-0.5 overflow-y-auto px-1 py-2 ${disabled ? 'pointer-events-none opacity-45' : ''}`}>
      {onSave && (
        <>
          <ToolBtn onClick={onSave} title="Sauvegarder">
            <Save size={15} />
          </ToolBtn>
          <Sep />
        </>
      )}

      <ToolBtn onClick={() => editor.chain().focus().setParagraph().run()} active={editor.isActive('paragraph') && !editor.isActive('heading')} title="Paragraphe">
        <Pilcrow size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()} active={editor.isActive('heading', { level: 1 })} title="H1">
        <Heading1 size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} active={editor.isActive('heading', { level: 2 })} title="H2">
        <Heading2 size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()} active={editor.isActive('heading', { level: 3 })} title="H3">
        <Heading3 size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleHeading({ level: 4 }).run()} active={editor.isActive('heading', { level: 4 })} title="H4">
        <Heading4 size={15} />
      </ToolBtn>

      <Sep />

      <ToolBtn onClick={() => editor.chain().focus().toggleBold().run()} active={editor.isActive('bold')} title="Gras">
        <Bold size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleItalic().run()} active={editor.isActive('italic')} title="Italique">
        <Italic size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleUnderline().run()} active={editor.isActive('underline')} title="Souligne">
        <Underline size={15} />
      </ToolBtn>

      <Sep />

      <ToolBtn onClick={() => editor.chain().focus().toggleBulletList().run()} active={editor.isActive('bulletList')} title="Liste a puces">
        <List size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleOrderedList().run()} active={editor.isActive('orderedList')} title="Liste numerotee">
        <ListOrdered size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleTaskList().run()} active={editor.isActive('taskList')} title="Checklist">
        <CheckSquare size={15} />
      </ToolBtn>

      <Sep />

      <ToolBtn onClick={() => editor.chain().focus().toggleBlockquote().run()} active={editor.isActive('blockquote')} title="Citation">
        <Quote size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleCodeBlock().run()} active={editor.isActive('codeBlock')} title="Code block">
        <Terminal size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().setHorizontalRule().run()} title="Separateur">
        <Minus size={15} />
      </ToolBtn>

      <Sep />

      <ToolBtn onClick={handleLink} active={editor.isActive('link')} title="Lien">
        <Link size={15} />
      </ToolBtn>
      <ToolBtn
        onClick={() => fileRef.current?.click()}
        disabled={!projectId || uploading}
        title={projectId ? 'Image' : 'Image indisponible'}
      >
        {uploading ? <Loader2 size={15} className="animate-spin" /> : <Image size={15} />}
      </ToolBtn>
      <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleImageFile} />
    </div>
  )
}
