import { useRef, useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
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
  Quote,
  Terminal,
  Image,
  Loader2,
  Link2,
  Minus,
  Table2,
  Unlink2,
  StickyNote,
} from 'lucide-react'
import { uploadMedia } from '@/api/media'
import type { CalloutAttrs } from '@/lib/tiptap/CalloutExtension'
import type { CalloutTemplate } from '@/types'

type PopoverKind = 'callout' | 'link' | 'table' | 'image'
type SavedRange = { from: number; to: number }

const POPOVER_WIDTH = 296

function ToolBtn({
  onClick,
  active,
  disabled,
  title,
  children,
}: {
  onClick: (event: React.MouseEvent<HTMLButtonElement>) => void
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
  projectId,
  articleId,
  calloutTemplates = [],
  disabled = false,
}: {
  editor: Editor | null
  projectId?: string
  articleId?: string
  calloutTemplates?: CalloutTemplate[]
  disabled?: boolean
}) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [activePopover, setActivePopover] = useState<PopoverKind | null>(null)
  const [popoverPosition, setPopoverPosition] = useState({ top: 120, left: 120 })
  const [savedRange, setSavedRange] = useState<SavedRange | null>(null)
  const [linkText, setLinkText] = useState('')
  const [linkUrl, setLinkUrl] = useState('')
  const [tableRows, setTableRows] = useState(3)
  const [tableCols, setTableCols] = useState(3)
  const [tableHeader, setTableHeader] = useState(true)
  const [imageUrl, setImageUrl] = useState('')
  const [imageAlt, setImageAlt] = useState('')
  const [selectedCalloutId, setSelectedCalloutId] = useState('')
  const [calloutTitle, setCalloutTitle] = useState('')
  const [selVersion, setSelVersion] = useState(0)

  useEffect(() => {
    if (!editor) return
    const handler = () => setSelVersion((v) => v + 1)
    editor.on('selectionUpdate', handler)
    return () => { editor.off('selectionUpdate', handler) }
  }, [editor])

  if (!editor) return null

  function placePopover(event: React.MouseEvent<HTMLButtonElement>, kind: PopoverKind) {
    const rect = event.currentTarget.getBoundingClientRect()
    const left = Math.min(rect.right + 28, window.innerWidth - POPOVER_WIDTH - 16)
    setPopoverPosition({
      top: Math.max(16, Math.min(rect.top - 8, window.innerHeight - 300)),
      left: Math.max(16, left),
    })
    setActivePopover((current) => (current === kind ? null : kind))
  }

  function escapeHtml(value: string): string {
    return value
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
  }

  function escapeAttr(value: string): string {
    return escapeHtml(value).replace(/'/g, '&#39;')
  }

  function selectedCalloutTemplate() {
    return calloutTemplates.find((template) => template.id === selectedCalloutId) ?? calloutTemplates[0] ?? null
  }

  function attrsFromTemplate(template: CalloutTemplate | null, title: string): CalloutAttrs {
    const style = template?.style ?? template?.slug ?? 'info'
    return {
      'data-block-type': 'callout',
      'data-callout-style': style,
      'data-callout-type': style,
      'data-template-id': template?.id ?? '',
      'data-template-key': template?.slug ?? '',
      'data-callout-label': template?.label ?? '',
      'data-callout-title': title.trim(),
      'data-callout-icon': template?.icon ?? '',
      'data-callout-class-name': template?.class_name ?? '',
      'data-color-background': template?.color_background ?? '',
      'data-color-border': template?.color_border ?? '',
      'data-color-text': template?.color_text ?? '',
    }
  }

  function buildCalloutHtml(template: CalloutTemplate, title: string, bodyHtml: string) {
    const attrs = attrsFromTemplate(template, title)
    const serializedAttrs = Object.entries(attrs)
      .filter(([, value]) => value !== undefined && value !== null && value !== '')
      .map(([key, value]) => ` ${key}="${escapeAttr(String(value))}"`)
      .join('')
    return [
      `<div${serializedAttrs}>`,
      title.trim() ? `<div class="callout-title" contenteditable="false">${escapeHtml(title.trim())}</div>` : '',
      `<div class="callout-body">${bodyHtml}</div>`,
      '</div>',
    ].join('')
  }

  function normalizeUrl(value: string): string {
    const trimmed = value.trim()
    if (!trimmed) return ''
    if (/^(https?:|mailto:|tel:|\/|#)/i.test(trimmed)) return trimmed
    return `https://${trimmed}`
  }

  async function handleImageFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file || !projectId) return

    setUploading(true)
    try {
      const media = await uploadMedia(projectId, file, articleId)
      editor!.chain().focus().setImage({ src: media.url, alt: media.alt_text ?? media.filename ?? '' }).run()
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  function openLinkPopover(event: React.MouseEvent<HTMLButtonElement>) {
    const { from, to, empty } = editor!.state.selection
    const previousUrl = editor!.getAttributes('link').href as string | undefined
    setSavedRange({ from, to })
    setLinkText(empty ? '' : editor!.state.doc.textBetween(from, to, ' '))
    setLinkUrl(previousUrl ?? '')
    placePopover(event, 'link')
  }

  function applyLink() {
    const url = normalizeUrl(linkUrl)
    const text = linkText.trim()
    if (!url || !savedRange) return

    if (savedRange.from === savedRange.to) {
      if (!text) return
      editor!.chain().focus().setTextSelection(savedRange.from).insertContent(
        `<a href="${escapeAttr(url)}">${escapeHtml(text)}</a>`
      ).run()
    } else {
      const selectedText = editor!.state.doc.textBetween(savedRange.from, savedRange.to, ' ')
      editor!.chain().focus().setTextSelection(savedRange).insertContent(
        `<a href="${escapeAttr(url)}">${escapeHtml(text || selectedText || url)}</a>`
      ).run()
    }

    setActivePopover(null)
    setLinkText('')
    setLinkUrl('')
  }

  function removeLink() {
    const range = savedRange ?? editor!.state.selection
    editor!.chain().focus().setTextSelection(range).extendMarkRange('link').unsetLink().run()
    setActivePopover(null)
  }

  function openTablePopover(event: React.MouseEvent<HTMLButtonElement>) {
    placePopover(event, 'table')
  }

  function insertTable() {
    editor!.chain().focus().insertTable({
      rows: Math.max(1, Math.min(12, tableRows)),
      cols: Math.max(1, Math.min(8, tableCols)),
      withHeaderRow: tableHeader,
    }).run()
    setActivePopover(null)
  }

  function openImagePopover(event: React.MouseEvent<HTMLButtonElement>) {
    setImageUrl('')
    setImageAlt('')
    placePopover(event, 'image')
  }

  function openCalloutPopover(event: React.MouseEvent<HTMLButtonElement>) {
    const attrs = editor!.getAttributes('callout') as Record<string, string | undefined>
    const activeTemplateId = attrs['data-template-id']
    const fallbackTemplate = calloutTemplates[0]?.id ?? ''
    setSelectedCalloutId(activeTemplateId || fallbackTemplate)
    const matchingTemplate = calloutTemplates.find((template) => template.id === activeTemplateId) ?? calloutTemplates[0]
    setCalloutTitle(attrs['data-callout-title'] || matchingTemplate?.default_title || matchingTemplate?.label || '')
    placePopover(event, 'callout')
  }

  function insertCallout() {
    const template = selectedCalloutTemplate()
    if (!template) return
    const attrs = attrsFromTemplate(template, calloutTitle || template.default_title || template.label)
    if (editor!.isActive('callout')) {
      editor!.chain().focus().updateAttributes('callout', attrs).run()
      setActivePopover(null)
      return
    }

    const { from, to, empty } = editor!.state.selection
    const selectedText = empty ? '' : editor!.state.doc.textBetween(from, to, ' ').trim()
    const bodyHtml = selectedText ? `<p>${escapeHtml(selectedText)}</p>` : '<p>Texte du callout</p>'
    editor!.chain().focus().insertContent(buildCalloutHtml(template, calloutTitle || template.default_title || template.label || '', bodyHtml)).run()
    setActivePopover(null)
  }

  function insertImageUrl() {
    const src = normalizeUrl(imageUrl)
    if (!src) return
    editor!.chain().focus().setImage({ src, alt: imageAlt.trim() }).run()
    setActivePopover(null)
  }

  function deleteSelectedImage() {
    editor!.chain().focus().deleteSelection().run()
    setActivePopover(null)
  }

  return (
    <div className={`flex h-full flex-col items-center gap-0.5 overflow-y-auto px-1 py-2 ${disabled ? 'pointer-events-none opacity-45' : ''}`}>
      <ToolBtn onClick={() => editor.chain().focus().setParagraph().run()} active={editor.isActive('paragraph') && !editor.isActive('heading')} title="Paragraphe">
        <Pilcrow size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()} active={editor.isActive('heading', { level: 1 })} title="Titre 1">
        <Heading1 size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} active={editor.isActive('heading', { level: 2 })} title="Titre 2">
        <Heading2 size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()} active={editor.isActive('heading', { level: 3 })} title="Titre 3">
        <Heading3 size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleHeading({ level: 4 }).run()} active={editor.isActive('heading', { level: 4 })} title="Titre 4">
        <Heading4 size={15} />
      </ToolBtn>
      {selVersion >= 0 && null}

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
      <ToolBtn onClick={openLinkPopover} active={editor.isActive('link')} title="Lien">
        {editor.isActive('link') ? <Unlink2 size={15} /> : <Link2 size={15} />}
      </ToolBtn>

      <Sep />

      <ToolBtn onClick={() => editor.chain().focus().toggleBulletList().run()} active={editor.isActive('bulletList')} title="Liste a puces">
        <List size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleOrderedList().run()} active={editor.isActive('orderedList')} title="Liste numerotee">
        <ListOrdered size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleBlockquote().run()} active={editor.isActive('blockquote')} title="Citation">
        <Quote size={15} />
      </ToolBtn>
      <ToolBtn onClick={openCalloutPopover} active={editor.isActive('callout')} disabled={calloutTemplates.length === 0} title={calloutTemplates.length === 0 ? 'Aucun callout configure' : 'Callout'}>
        <StickyNote size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleCodeBlock().run()} active={editor.isActive('codeBlock')} title="Code block">
        <Terminal size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().setHorizontalRule().run()} title="Separateur">
        <Minus size={15} />
      </ToolBtn>
      <ToolBtn onClick={openTablePopover} active={editor.isActive('table')} title="Tableau">
        <Table2 size={15} />
      </ToolBtn>

      <Sep />

      <ToolBtn
        onClick={openImagePopover}
        disabled={!projectId || uploading}
        title={projectId ? 'Image' : 'Image indisponible'}
      >
        {uploading ? <Loader2 size={15} className="animate-spin" /> : <Image size={15} />}
      </ToolBtn>
      <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleImageFile} />

      {activePopover && createPortal((
        <div
          style={{
            top: popoverPosition.top,
            left: popoverPosition.left,
            zIndex: 2147483647,
          }}
          className="fixed w-[296px] rounded-[16px] border border-border-strong bg-surface p-3 text-left shadow-[0_24px_80px_rgba(0,0,0,0.34)] ring-1 ring-black/10 dark:shadow-[0_24px_80px_rgba(0,0,0,0.6)] dark:ring-white/10"
        >
          <span className="absolute left-[-7px] top-6 h-3.5 w-3.5 rotate-45 border-b border-l border-border-strong bg-surface" />
          {activePopover === 'link' && (
            <div className="relative flex flex-col gap-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">Lien</p>
              <label className="flex flex-col gap-1 text-[11px] text-secondary">
                Texte
                <input
                  value={linkText}
                  onChange={(event) => setLinkText(event.target.value)}
                  placeholder="Texte du lien"
                  className="h-8 rounded-[8px] border border-border px-2 text-[12px] text-primary outline-none focus:border-accent/60 focus:ring-1 focus:ring-accent/30"
                />
              </label>
              <label className="flex flex-col gap-1 text-[11px] text-secondary">
                URL
                <input
                  value={linkUrl}
                  onChange={(event) => setLinkUrl(event.target.value)}
                  placeholder="https://exemple.com"
                  className="h-8 rounded-[8px] border border-border px-2 text-[12px] text-primary outline-none focus:border-accent/60 focus:ring-1 focus:ring-accent/30"
                />
              </label>
              <div className="flex items-center justify-between gap-2 pt-1">
                <button type="button" onClick={() => setActivePopover(null)} className="text-[12px] text-tertiary hover:text-secondary">Annuler</button>
                <div className="flex items-center gap-2">
                  {editor.isActive('link') && (
                    <button type="button" onClick={removeLink} className="rounded-[8px] px-2 py-1 text-[12px] font-medium text-danger hover:bg-danger/5">
                      Retirer
                    </button>
                  )}
                  <button type="button" onClick={applyLink} className="rounded-[8px] bg-accent px-2.5 py-1.5 text-[12px] font-medium text-white">
                    Appliquer
                  </button>
                </div>
              </div>
            </div>
          )}

          {activePopover === 'table' && (
            <div className="relative flex flex-col gap-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">Tableau</p>
              {!editor.isActive('table') ? (
                <>
                  <div className="grid grid-cols-2 gap-2">
                    <label className="flex flex-col gap-1 text-[11px] text-secondary">
                      Lignes
                      <input
                        type="number"
                        min={1}
                        max={12}
                        value={tableRows}
                        onChange={(event) => setTableRows(Number(event.target.value))}
                        className="h-8 rounded-[8px] border border-border px-2 text-[12px] text-primary outline-none focus:border-accent/60 focus:ring-1 focus:ring-accent/30"
                      />
                    </label>
                    <label className="flex flex-col gap-1 text-[11px] text-secondary">
                      Colonnes
                      <input
                        type="number"
                        min={1}
                        max={8}
                        value={tableCols}
                        onChange={(event) => setTableCols(Number(event.target.value))}
                        className="h-8 rounded-[8px] border border-border px-2 text-[12px] text-primary outline-none focus:border-accent/60 focus:ring-1 focus:ring-accent/30"
                      />
                    </label>
                  </div>
                  <label className="flex items-center gap-2 text-[12px] text-secondary">
                    <input
                      type="checkbox"
                      checked={tableHeader}
                      onChange={(event) => setTableHeader(event.target.checked)}
                    />
                    Ligne d'en-tête
                  </label>
                  <div className="flex items-center justify-end gap-2 pt-1">
                    <button type="button" onClick={() => setActivePopover(null)} className="text-[12px] text-tertiary hover:text-secondary">Annuler</button>
                    <button type="button" onClick={insertTable} className="rounded-[8px] bg-accent px-2.5 py-1.5 text-[12px] font-medium text-white">
                      Insérer
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <div className="grid grid-cols-2 gap-1.5">
                    <button type="button" onClick={() => editor.chain().focus().addRowAfter().run()} className="rounded-[8px] border border-border px-2 py-1.5 text-[12px] text-secondary hover:bg-[#f5f5f7]">+ ligne</button>
                    <button type="button" onClick={() => editor.chain().focus().deleteRow().run()} className="rounded-[8px] border border-border px-2 py-1.5 text-[12px] text-secondary hover:bg-[#f5f5f7]">- ligne</button>
                    <button type="button" onClick={() => editor.chain().focus().addColumnAfter().run()} className="rounded-[8px] border border-border px-2 py-1.5 text-[12px] text-secondary hover:bg-[#f5f5f7]">+ colonne</button>
                    <button type="button" onClick={() => editor.chain().focus().deleteColumn().run()} className="rounded-[8px] border border-border px-2 py-1.5 text-[12px] text-secondary hover:bg-[#f5f5f7]">- colonne</button>
                  </div>
                  <button type="button" onClick={() => { editor.chain().focus().deleteTable().run(); setActivePopover(null) }} className="mt-1 rounded-[8px] px-2 py-1.5 text-[12px] font-medium text-danger hover:bg-danger/5">
                    Supprimer le tableau
                  </button>
                </>
              )}
            </div>
          )}

          {activePopover === 'callout' && (
            <div className="relative flex flex-col gap-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">Callout</p>
              {calloutTemplates.length === 0 ? (
                <p className="text-[12px] leading-snug text-secondary">
                  Aucun template disponible. Creez ou importez des callouts dans les parametres du projet.
                </p>
              ) : (
                <>
                  <label className="flex flex-col gap-1 text-[11px] text-secondary">
                    Titre
                    <input
                      value={calloutTitle}
                      onChange={(event) => setCalloutTitle(event.target.value)}
                      placeholder="Titre du callout"
                      className="h-8 rounded-[8px] border border-border px-2 text-[12px] text-primary outline-none focus:border-accent/60 focus:ring-1 focus:ring-accent/30"
                    />
                  </label>
                  <div className="flex flex-col gap-1">
                    {calloutTemplates.map((template) => (
                  <button
                    key={template.id}
                    type="button"
                    onClick={() => {
                      setSelectedCalloutId(template.id)
                      setCalloutTitle((current) => current || template.default_title || template.label)
                    }}
                    className={`flex items-center gap-2 rounded-[8px] px-2.5 py-1.5 text-[12px] transition-colors ${
                      selectedCalloutId === template.id
                        ? 'bg-accent/8 text-accent font-medium'
                        : 'text-secondary hover:bg-[#f5f5f7]'
                    }`}
                  >
                    <span
                      className="h-2.5 w-2.5 rounded-full shrink-0"
                      style={{ backgroundColor: template.color_border ?? '#3b82f6' }}
                    />
                    <span className="flex-1 text-left">{template.label}</span>
                    <span className="text-[10px] uppercase tracking-wide opacity-70">{template.style ?? template.slug}</span>
                  </button>
                    ))}
                  </div>
                </>
              )}
              <div className="flex items-center justify-end gap-2 pt-1">
                {editor.isActive('callout') && (
                  <button
                    type="button"
                    onClick={() => { editor.chain().focus().unsetCallout().run(); setActivePopover(null) }}
                    className="rounded-[8px] px-2 py-1 text-[12px] font-medium text-danger hover:bg-danger/5"
                  >
                    Retirer
                  </button>
                )}
                <button type="button" onClick={() => setActivePopover(null)} className="text-[12px] text-tertiary hover:text-secondary">Annuler</button>
                <button type="button" onClick={insertCallout} disabled={calloutTemplates.length === 0} className="rounded-[8px] bg-accent px-2.5 py-1.5 text-[12px] font-medium text-white disabled:opacity-40">
                  {editor.isActive('callout') ? 'Mettre a jour' : 'Inserer'}
                </button>
              </div>
            </div>
          )}

          {activePopover === 'image' && (
            <div className="relative flex flex-col gap-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">Image</p>
              {editor.isActive('image') && (
                <button
                  type="button"
                  onClick={deleteSelectedImage}
                  className="rounded-[9px] border border-danger/20 bg-danger/5 px-2.5 py-2 text-[12px] font-medium text-danger hover:bg-danger/10"
                >
                  Supprimer l'image sélectionnée
                </button>
              )}
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                disabled={uploading}
                className="rounded-[9px] border border-border px-2.5 py-2 text-[12px] font-medium text-secondary hover:bg-[#f5f5f7] disabled:opacity-50"
              >
                {uploading ? 'Upload en cours...' : 'Choisir un fichier'}
              </button>
              <label className="flex flex-col gap-1 text-[11px] text-secondary">
                URL de l'image
                <input
                  value={imageUrl}
                  onChange={(event) => setImageUrl(event.target.value)}
                  placeholder="https://exemple.com/image.jpg"
                  className="h-8 rounded-[8px] border border-border px-2 text-[12px] text-primary outline-none focus:border-accent/60 focus:ring-1 focus:ring-accent/30"
                />
              </label>
              <label className="flex flex-col gap-1 text-[11px] text-secondary">
                Texte alternatif
                <input
                  value={imageAlt}
                  onChange={(event) => setImageAlt(event.target.value)}
                  placeholder="Description courte"
                  className="h-8 rounded-[8px] border border-border px-2 text-[12px] text-primary outline-none focus:border-accent/60 focus:ring-1 focus:ring-accent/30"
                />
              </label>
              <div className="flex items-center justify-end gap-2 pt-1">
                <button type="button" onClick={() => setActivePopover(null)} className="text-[12px] text-tertiary hover:text-secondary">Annuler</button>
                <button type="button" onClick={insertImageUrl} className="rounded-[8px] bg-accent px-2.5 py-1.5 text-[12px] font-medium text-white">
                  Insérer l'URL
                </button>
              </div>
            </div>
          )}
        </div>
      ), document.body)}
    </div>
  )
}
