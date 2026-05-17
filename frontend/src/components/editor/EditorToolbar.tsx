import { useCallback, useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { Editor } from '@tiptap/react'
import { NodeSelection } from '@tiptap/pm/state'
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
  Plus,
  Trash2,
} from 'lucide-react'
import { createCalloutTemplate } from '@/api/callouts'
import { uploadMedia } from '@/api/media'
import type { CalloutAttrs } from '@/lib/tiptap/CalloutExtension'
import type { CalloutTemplate } from '@/types'
import ColorPickerField from '@/components/ui/ColorPickerField'
import { DEFAULT_ACCENT_COLOR, normalizeHexColor } from '@/lib/colors'
import { deriveCalloutColors, slugifyCalloutLabel } from '@/lib/callouts'

type PopoverKind = 'callout' | 'link' | 'table' | 'image'
type SavedSelection = { from: number; to: number; isNodeSelection: boolean }
type CalloutCreateForm = {
  label: string
  defaultTitle: string
  primaryColor: string
}

const POPOVER_WIDTH = 296
const IMAGE_WIDTH_PRESETS = [40, 60, 80, 100]
const DEFAULT_CALLOUT_FORM: CalloutCreateForm = {
  label: '',
  defaultTitle: '',
  primaryColor: DEFAULT_ACCENT_COLOR,
}

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

function parseImageWidth(value: string | number | null | undefined) {
  const numeric = typeof value === 'number' ? value : Number.parseInt(String(value ?? ''), 10)
  if (!Number.isFinite(numeric)) return 100
  return Math.max(20, Math.min(100, Math.round(numeric)))
}

export default function EditorToolbar({
  editor,
  projectId,
  articleId,
  calloutTemplates = [],
  onCalloutTemplateCreated,
  disabled = false,
}: {
  editor: Editor | null
  projectId?: string
  articleId?: string
  calloutTemplates?: CalloutTemplate[]
  onCalloutTemplateCreated?: (template: CalloutTemplate) => void
  disabled?: boolean
}) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [activePopover, setActivePopover] = useState<PopoverKind | null>(null)
  const [popoverPosition, setPopoverPosition] = useState({ top: 120, left: 120 })
  const [savedSelection, setSavedSelection] = useState<SavedSelection | null>(null)
  const [linkText, setLinkText] = useState('')
  const [linkUrl, setLinkUrl] = useState('')
  const [tableRows, setTableRows] = useState(3)
  const [tableCols, setTableCols] = useState(3)
  const [tableHeader, setTableHeader] = useState(true)
  const [imageUrl, setImageUrl] = useState('')
  const [imageAlt, setImageAlt] = useState('')
  const [imageWidth, setImageWidth] = useState('100')
  const [imageError, setImageError] = useState('')
  const [selectedCalloutId, setSelectedCalloutId] = useState('')
  const [calloutTitle, setCalloutTitle] = useState('')
  const [calloutSaving, setCalloutSaving] = useState(false)
  const [calloutError, setCalloutError] = useState('')
  const [createCalloutOpen, setCreateCalloutOpen] = useState(false)
  const [calloutForm, setCalloutForm] = useState<CalloutCreateForm>(DEFAULT_CALLOUT_FORM)
  const forceSelectionRender = useState(0)[1]
  const [imageToolbarPos, setImageToolbarPos] = useState<{ top: number; left: number } | null>(null)

  const imageToolbarTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const editorRef = useRef(editor)
  useEffect(() => { editorRef.current = editor }, [editor])
  const applyImageWidth = useCallback((width: number) => {
    const e = editorRef.current
    if (!e || !e.isActive('image')) return
    e.chain().focus().updateAttributes('image', { width }).run()
    setImageWidth(String(width))
  }, [])

  const applyImageAltCb = useCallback(() => {
    const e = editorRef.current
    if (!e || !e.isActive('image')) return
    e.chain().focus().updateAttributes('image', { alt: imageAlt.trim() || null }).run()
  }, [imageAlt])

  const replaceSelectedImage = useCallback(() => {
    fileRef.current?.click()
  }, [])

  useEffect(() => {
    if (!editor) return
    const handler = () => {
      forceSelectionRender((v) => v + 1)
      if (activePopover === 'image') {
        if (!editor.isActive('image')) {
          setImageUrl('')
          setImageAlt('')
          setImageWidth('100')
          setImageError('')
          return
        }
        const attrs = editor.getAttributes('image') as Record<string, string | number | undefined>
        setImageUrl(typeof attrs.src === 'string' ? attrs.src : '')
        setImageAlt(typeof attrs.alt === 'string' ? attrs.alt : '')
        setImageWidth(String(parseImageWidth(attrs.width)))
        setImageError('')
      }

      if (editor.isActive('image')) {
        if (imageToolbarTimer.current) clearTimeout(imageToolbarTimer.current)
        const { selection } = editor.state
        if (selection instanceof NodeSelection) {
          const node = selection.node
          if (node && node.type.name === 'image') {
            const dom = editor.view.nodeDOM(selection.from) as HTMLElement | null
            if (dom) {
              const rect = dom.getBoundingClientRect()
              setImageToolbarPos({
                top: rect.top - 46,
                left: Math.max(16, Math.min(rect.left + rect.width / 2 - 120, window.innerWidth - 270)),
              })
            }
          }
        }
      } else {
        imageToolbarTimer.current = setTimeout(() => setImageToolbarPos(null), 200)
      }
    }
    editor.on('selectionUpdate', handler)
    return () => {
      editor.off('selectionUpdate', handler)
    }
  }, [editor, activePopover, forceSelectionRender])

  useEffect(() => {
    return () => {
      if (imageToolbarTimer.current) clearTimeout(imageToolbarTimer.current)
    }
  }, [])

  if (!editor) return null
  const currentEditor = editor

  function placePopover(event: React.MouseEvent<HTMLButtonElement>, kind: PopoverKind) {
    const rect = event.currentTarget.getBoundingClientRect()
    const left = Math.min(rect.right + 28, window.innerWidth - POPOVER_WIDTH - 16)
    const estimatedHeight = kind === 'callout' ? 420 : kind === 'image' ? 480 : kind === 'table' ? 300 : 260
    const spaceBelow = window.innerHeight - rect.bottom
    const spaceAbove = rect.top
    if (spaceBelow < estimatedHeight && spaceAbove > spaceBelow) {
      setPopoverPosition({
        top: Math.max(16, rect.top - estimatedHeight),
        left: Math.max(16, left),
      })
    } else {
      setPopoverPosition({
        top: Math.min(rect.top - 8, Math.max(16, window.innerHeight - estimatedHeight)),
        left: Math.max(16, left),
      })
    }
    setActivePopover((current) => (current === kind ? null : kind))
  }

  function rememberSelection() {
    const selection = currentEditor.state.selection
    setSavedSelection({
      from: selection.from,
      to: selection.to,
      isNodeSelection: selection instanceof NodeSelection,
    })
  }

  function chainWithSavedSelection() {
    const chain = currentEditor.chain().focus()
    if (!savedSelection) return chain
    if (savedSelection.isNodeSelection) {
      return chain.setNodeSelection(savedSelection.from)
    }
    return chain.setTextSelection({ from: savedSelection.from, to: savedSelection.to })
  }

  function closePopover(kind?: PopoverKind) {
    setActivePopover((current) => {
      if (!kind || current === kind) return null
      return current
    })
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
      'data-callout-source': template?.source ?? 'manual',
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
    if (/^(https?:|mailto:|tel:|\/|#|blob:|data:)/i.test(trimmed)) return trimmed
    return `https://${trimmed}`
  }

  function resetImageForm() {
    setImageUrl('')
    setImageAlt('')
    setImageWidth('100')
    setImageError('')
    if (fileRef.current) fileRef.current.value = ''
  }

  function syncSelectedImageFields() {
    if (!currentEditor.isActive('image')) {
      resetImageForm()
      return
    }
    const attrs = currentEditor.getAttributes('image') as Record<string, string | number | undefined>
    setImageUrl(typeof attrs.src === 'string' ? attrs.src : '')
    setImageAlt(typeof attrs.alt === 'string' ? attrs.alt : '')
    setImageWidth(String(parseImageWidth(attrs.width)))
    setImageError('')
  }

  function imagePayload(src: string, alt: string) {
    return {
      src,
      alt: alt.trim() || null,
      width: parseImageWidth(imageWidth),
    }
  }

  function applyImage(attrs: { src: string; alt: string | null; width: number; 'data-media-id'?: string | null }) {
    const chain = chainWithSavedSelection()
    if (currentEditor.isActive('image') || savedSelection?.isNodeSelection) {
      return chain.updateAttributes('image', attrs).run()
    }
    return chain.insertContent({ type: 'image', attrs }).run()
  }

  async function handleImageFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    if (!projectId) {
      setImageError("Le projet n'est pas prêt pour l'upload.")
      return
    }

    setUploading(true)
    setImageError('')
    try {
      const media = await uploadMedia(projectId, file, articleId)
      const alt = imageAlt.trim() || media.alt_text || media.filename || file.name
      const inserted = applyImage({
        ...imagePayload(media.url, alt),
        'data-media-id': media.id,
      })
      if (!inserted) throw new Error("Impossible d'insérer cette image.")
      resetImageForm()
      closePopover('image')
    } catch (error) {
      setImageError(error instanceof Error ? error.message : "Impossible d'insérer cette image.")
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  function openLinkPopover(event: React.MouseEvent<HTMLButtonElement>) {
    const { from, to, empty } = currentEditor.state.selection
    const previousUrl = currentEditor.getAttributes('link').href as string | undefined
    setSavedSelection({ from, to, isNodeSelection: false })
    setLinkText(empty ? '' : currentEditor.state.doc.textBetween(from, to, ' '))
    setLinkUrl(previousUrl ?? '')
    placePopover(event, 'link')
  }

  function applyLink() {
    const url = normalizeUrl(linkUrl)
    const text = linkText.trim()
    if (!url || !savedSelection) return

    if (savedSelection.from === savedSelection.to) {
      if (!text) return
      currentEditor.chain().focus().setTextSelection(savedSelection.from).insertContent(
        `<a href="${escapeAttr(url)}">${escapeHtml(text)}</a>`,
      ).run()
    } else {
      const selectedText = currentEditor.state.doc.textBetween(savedSelection.from, savedSelection.to, ' ')
      currentEditor.chain().focus().setTextSelection({ from: savedSelection.from, to: savedSelection.to }).insertContent(
        `<a href="${escapeAttr(url)}">${escapeHtml(text || selectedText || url)}</a>`,
      ).run()
    }

    closePopover('link')
    setLinkText('')
    setLinkUrl('')
  }

  function removeLink() {
    const range = savedSelection ?? { from: currentEditor.state.selection.from, to: currentEditor.state.selection.to }
    currentEditor.chain().focus().setTextSelection(range).extendMarkRange('link').unsetLink().run()
    closePopover('link')
  }

  function openTablePopover(event: React.MouseEvent<HTMLButtonElement>) {
    rememberSelection()
    placePopover(event, 'table')
  }

  function insertTable() {
    chainWithSavedSelection().insertTable({
      rows: Math.max(1, Math.min(12, tableRows)),
      cols: Math.max(1, Math.min(8, tableCols)),
      withHeaderRow: tableHeader,
    }).run()
    closePopover('table')
  }

  function openImagePopover(event: React.MouseEvent<HTMLButtonElement>) {
    rememberSelection()
    syncSelectedImageFields()
    placePopover(event, 'image')
  }

  function resetCalloutCreateForm() {
    setCalloutForm(DEFAULT_CALLOUT_FORM)
    setCalloutError('')
  }

  function openCalloutPopover(event: React.MouseEvent<HTMLButtonElement>) {
    rememberSelection()
    const attrs = currentEditor.getAttributes('callout') as Record<string, string | undefined>
    const activeTemplateId = attrs['data-template-id']
    const fallbackTemplate = calloutTemplates[0]?.id ?? ''
    setSelectedCalloutId(activeTemplateId || fallbackTemplate)
    const matchingTemplate = calloutTemplates.find((template) => template.id === activeTemplateId) ?? calloutTemplates[0]
    setCalloutTitle(attrs['data-callout-title'] || matchingTemplate?.default_title || matchingTemplate?.label || '')
    setCreateCalloutOpen(calloutTemplates.length === 0)
    resetCalloutCreateForm()
    placePopover(event, 'callout')
  }

  async function handleCreateCallout() {
    if (!projectId) {
      setCalloutError("Le projet n'est pas disponible.")
      return
    }
    if (!calloutForm.label.trim()) {
      setCalloutError('Ajoutez un nom pour ce callout.')
      return
    }

    setCalloutSaving(true)
    setCalloutError('')
    try {
      const primaryColor = normalizeHexColor(calloutForm.primaryColor, DEFAULT_ACCENT_COLOR)
      const created = await createCalloutTemplate(projectId, {
        label: calloutForm.label.trim(),
        default_title: calloutForm.defaultTitle.trim() || null,
        style: slugifyCalloutLabel(calloutForm.label),
        source: 'manual',
        ...deriveCalloutColors(primaryColor),
      })
      onCalloutTemplateCreated?.(created)
      setSelectedCalloutId(created.id)
      setCalloutTitle(created.default_title ?? created.label)
      setCreateCalloutOpen(false)
      resetCalloutCreateForm()
    } catch (error) {
      setCalloutError(error instanceof Error ? error.message : 'Impossible de créer ce callout.')
    } finally {
      setCalloutSaving(false)
    }
  }

  function insertCallout() {
    const template = selectedCalloutTemplate()
    if (!template) return

    const attrs = attrsFromTemplate(template, calloutTitle || template.default_title || template.label)
    if (currentEditor.isActive('callout')) {
      currentEditor.chain().focus().updateAttributes('callout', attrs).run()
      closePopover('callout')
      return
    }

    const selection = savedSelection ?? {
      from: currentEditor.state.selection.from,
      to: currentEditor.state.selection.to,
      isNodeSelection: false,
    }
    const selectedText = selection.isNodeSelection
      ? ''
      : currentEditor.state.doc.textBetween(selection.from, selection.to, ' ').trim()
    const bodyHtml = selectedText ? `<p>${escapeHtml(selectedText)}</p>` : '<p>Texte du callout</p>'

    chainWithSavedSelection().insertContent(
      buildCalloutHtml(template, calloutTitle || template.default_title || template.label || '', bodyHtml),
    ).run()
    closePopover('callout')
  }

  function insertImageUrl() {
    const src = normalizeUrl(imageUrl)
    if (!src) {
      setImageError("Ajoutez une URL d'image valide.")
      return
    }
    const inserted = applyImage({
      ...imagePayload(src, imageAlt),
      'data-media-id': null,
    })
    if (!inserted) {
      setImageError("Impossible d'insérer cette image.")
      return
    }
    resetImageForm()
    closePopover('image')
  }

  function deleteSelectedImage() {
    const deleted = chainWithSavedSelection().deleteSelection().run()
    if (deleted) {
      resetImageForm()
      closePopover('image')
    }
  }

  return (
    <div className={`flex h-full flex-col items-center gap-0.5 overflow-y-auto px-1 py-2 ${disabled ? 'pointer-events-none opacity-45' : ''}`}>
      <ToolBtn onClick={() => currentEditor.chain().focus().setParagraph().run()} active={currentEditor.isActive('paragraph') && !currentEditor.isActive('heading')} title="Paragraphe">
        <Pilcrow size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => currentEditor.chain().focus().toggleHeading({ level: 1 }).run()} active={currentEditor.isActive('heading', { level: 1 })} title="Titre 1">
        <Heading1 size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => currentEditor.chain().focus().toggleHeading({ level: 2 }).run()} active={currentEditor.isActive('heading', { level: 2 })} title="Titre 2">
        <Heading2 size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => currentEditor.chain().focus().toggleHeading({ level: 3 }).run()} active={currentEditor.isActive('heading', { level: 3 })} title="Titre 3">
        <Heading3 size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => currentEditor.chain().focus().toggleHeading({ level: 4 }).run()} active={currentEditor.isActive('heading', { level: 4 })} title="Titre 4">
        <Heading4 size={15} />
      </ToolBtn>

      <Sep />

      <ToolBtn onClick={() => currentEditor.chain().focus().toggleBold().run()} active={currentEditor.isActive('bold')} title="Gras">
        <Bold size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => currentEditor.chain().focus().toggleItalic().run()} active={currentEditor.isActive('italic')} title="Italique">
        <Italic size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => currentEditor.chain().focus().toggleUnderline().run()} active={currentEditor.isActive('underline')} title="Souligne">
        <Underline size={15} />
      </ToolBtn>
      <ToolBtn onClick={openLinkPopover} active={currentEditor.isActive('link')} title="Lien">
        {currentEditor.isActive('link') ? <Unlink2 size={15} /> : <Link2 size={15} />}
      </ToolBtn>

      <Sep />

      <ToolBtn onClick={() => currentEditor.chain().focus().toggleBulletList().run()} active={currentEditor.isActive('bulletList')} title="Liste a puces">
        <List size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => currentEditor.chain().focus().toggleOrderedList().run()} active={currentEditor.isActive('orderedList')} title="Liste numerotee">
        <ListOrdered size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => currentEditor.chain().focus().toggleBlockquote().run()} active={currentEditor.isActive('blockquote')} title="Citation">
        <Quote size={15} />
      </ToolBtn>
      <ToolBtn onClick={openCalloutPopover} active={currentEditor.isActive('callout')} title="Callout">
        <StickyNote size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => currentEditor.chain().focus().toggleCodeBlock().run()} active={currentEditor.isActive('codeBlock')} title="Code block">
        <Terminal size={15} />
      </ToolBtn>
      <ToolBtn onClick={() => currentEditor.chain().focus().setHorizontalRule().run()} title="Separateur">
        <Minus size={15} />
      </ToolBtn>
      <ToolBtn onClick={openTablePopover} active={currentEditor.isActive('table')} title="Tableau">
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
          className="fixed w-[296px] max-h-[80vh] overflow-y-auto rounded-[16px] border border-border-strong bg-surface p-3 text-left shadow-[0_24px_80px_rgba(0,0,0,0.34)] ring-1 ring-black/10 dark:shadow-[0_24px_80px_rgba(0,0,0,0.6)] dark:ring-white/10"
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
                <button type="button" onClick={() => closePopover('link')} className="text-[12px] text-tertiary hover:text-secondary">Annuler</button>
                <div className="flex items-center gap-2">
                  {currentEditor.isActive('link') && (
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
              {!currentEditor.isActive('table') ? (
                <>
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
                  <label className="flex items-center gap-2 text-[12px] text-secondary">
                    <input type="checkbox" checked={tableHeader} onChange={(event) => setTableHeader(event.target.checked)} />
                    Ligne d'en-tete
                  </label>
                  <div className="flex items-center justify-end gap-2 pt-1">
                    <button type="button" onClick={() => closePopover('table')} className="text-[12px] text-tertiary hover:text-secondary">Annuler</button>
                    <button type="button" onClick={insertTable} className="rounded-[8px] bg-accent px-2.5 py-1.5 text-[12px] font-medium text-white">
                      Inserer
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <div className="grid grid-cols-2 gap-2">
                    <button type="button" onClick={() => currentEditor.chain().focus().addRowAfter().run()} className="rounded-[8px] border border-border px-2 py-1.5 text-[12px] text-secondary hover:bg-[#f5f5f7]">+ ligne</button>
                    <button type="button" onClick={() => currentEditor.chain().focus().deleteRow().run()} className="rounded-[8px] border border-border px-2 py-1.5 text-[12px] text-secondary hover:bg-[#f5f5f7]">- ligne</button>
                    <button type="button" onClick={() => currentEditor.chain().focus().addColumnAfter().run()} className="rounded-[8px] border border-border px-2 py-1.5 text-[12px] text-secondary hover:bg-[#f5f5f7]">+ colonne</button>
                    <button type="button" onClick={() => currentEditor.chain().focus().deleteColumn().run()} className="rounded-[8px] border border-border px-2 py-1.5 text-[12px] text-secondary hover:bg-[#f5f5f7]">- colonne</button>
                  </div>
                  <button type="button" onClick={() => { currentEditor.chain().focus().deleteTable().run(); closePopover('table') }} className="mt-1 rounded-[8px] px-2 py-1.5 text-[12px] font-medium text-danger hover:bg-danger/5">
                    Supprimer le tableau
                  </button>
                </>
              )}
            </div>
          )}

          {activePopover === 'callout' && (
            <div className="relative flex flex-col gap-2">
              <div className="flex items-center justify-between gap-2">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">Callout</p>
                <button
                  type="button"
                  onClick={() => {
                    setCreateCalloutOpen((open) => !open)
                    setCalloutError('')
                  }}
                  className="inline-flex items-center gap-1 rounded-[8px] border border-border px-2 py-1 text-[11px] font-medium text-secondary hover:bg-[#f5f5f7]"
                >
                  <Plus size={12} />
                  Créer
                </button>
              </div>

              {createCalloutOpen && (
                <div className="rounded-[12px] border border-border bg-[#f9f9fb] p-3">
                  <div className="flex flex-col gap-3">
                    <label className="flex flex-col gap-1 text-[11px] text-secondary">
                      Nom
                      <input
                        value={calloutForm.label}
                        onChange={(event) => setCalloutForm((prev) => ({ ...prev, label: event.target.value }))}
                        placeholder="Information"
                        className="h-8 rounded-[8px] border border-border bg-white px-2 text-[12px] text-primary outline-none focus:border-accent/60 focus:ring-1 focus:ring-accent/30"
                      />
                    </label>
                    <label className="flex flex-col gap-1 text-[11px] text-secondary">
                      Titre par defaut
                      <input
                        value={calloutForm.defaultTitle}
                        onChange={(event) => setCalloutForm((prev) => ({ ...prev, defaultTitle: event.target.value }))}
                        placeholder="A retenir"
                        className="h-8 rounded-[8px] border border-border bg-white px-2 text-[12px] text-primary outline-none focus:border-accent/60 focus:ring-1 focus:ring-accent/30"
                      />
                    </label>
                    <ColorPickerField
                      label="Couleur principale"
                      value={calloutForm.primaryColor}
                      onChange={(value) => setCalloutForm((prev) => ({ ...prev, primaryColor: value }))}
                    />
                    {calloutError && <p className="text-[11px] text-danger">{calloutError}</p>}
                    <div className="flex items-center justify-end gap-2">
                      <button type="button" onClick={() => { setCreateCalloutOpen(false); resetCalloutCreateForm() }} className="text-[12px] text-tertiary hover:text-secondary">Annuler</button>
                      <button type="button" onClick={handleCreateCallout} disabled={calloutSaving} className="rounded-[8px] bg-accent px-2.5 py-1.5 text-[12px] font-medium text-white disabled:opacity-40">
                        {calloutSaving ? 'Création...' : 'Créer le callout'}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {calloutTemplates.length === 0 ? (
                <p className="text-[12px] leading-snug text-secondary">
                  Aucun template disponible pour ce projet. Créez-en un ici ou importez-les depuis les paramètres.
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
                      </button>
                    ))}
                  </div>
                </>
              )}
              <div className="flex items-center justify-end gap-2 pt-1">
                {currentEditor.isActive('callout') && (
                  <button
                    type="button"
                    onClick={() => { currentEditor.chain().focus().unsetCallout().run(); closePopover('callout') }}
                    className="rounded-[8px] px-2 py-1 text-[12px] font-medium text-danger hover:bg-danger/5"
                  >
                    Retirer
                  </button>
                )}
                <button type="button" onClick={() => closePopover('callout')} className="text-[12px] text-tertiary hover:text-secondary">Annuler</button>
                <button type="button" onClick={insertCallout} disabled={calloutTemplates.length === 0} className="rounded-[8px] bg-accent px-2.5 py-1.5 text-[12px] font-medium text-white disabled:opacity-40">
                  {currentEditor.isActive('callout') ? 'Mettre a jour' : 'Inserer'}
                </button>
              </div>
            </div>
          )}

          {activePopover === 'image' && (
            <div className="relative flex flex-col gap-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">Image</p>
              {currentEditor.isActive('image') && (
                <div className="rounded-[10px] border border-accent/15 bg-accent/5 px-2.5 py-2 text-[11px] text-secondary">
                  Image sélectionnée. Vous pouvez la remplacer, modifier son alt ou ajuster sa largeur.
                </div>
              )}
              {imageError && (
                <div className="rounded-[10px] border border-danger/20 bg-danger/5 px-2.5 py-2 text-[11px] text-danger">
                  {imageError}
                </div>
              )}
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                disabled={uploading}
                className="rounded-[9px] border border-border px-2.5 py-2 text-[12px] font-medium text-secondary hover:bg-[#f5f5f7] disabled:opacity-50"
              >
                {uploading ? 'Upload en cours...' : currentEditor.isActive('image') ? "Remplacer avec un fichier" : 'Choisir un fichier'}
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
              <div className="flex flex-col gap-1 text-[11px] text-secondary">
                <span>Largeur</span>
                <div className="grid grid-cols-4 gap-1">
                  {IMAGE_WIDTH_PRESETS.map((preset) => (
                    <button
                      key={preset}
                      type="button"
                      onClick={() => setImageWidth(String(preset))}
                      className={`rounded-[8px] px-2 py-1 text-[11px] font-medium ${
                        Number(imageWidth) === preset ? 'bg-accent text-white' : 'border border-border text-secondary hover:bg-[#f5f5f7]'
                      }`}
                    >
                      {preset}%
                    </button>
                  ))}
                </div>
                <input
                  type="range"
                  min={20}
                  max={100}
                  step={5}
                  value={parseImageWidth(imageWidth)}
                  onChange={(event) => setImageWidth(event.target.value)}
                  className="w-full"
                />
              </div>
              <div className="flex items-center justify-between gap-2 pt-1">
                {currentEditor.isActive('image') ? (
                  <button
                    type="button"
                    onClick={deleteSelectedImage}
                    className="rounded-[8px] px-2 py-1 text-[12px] font-medium text-danger hover:bg-danger/5"
                  >
                    Supprimer
                  </button>
                ) : (
                  <span />
                )}
                <div className="flex items-center gap-2">
                  <button type="button" onClick={() => closePopover('image')} className="text-[12px] text-tertiary hover:text-secondary">Annuler</button>
                  <button type="button" onClick={insertImageUrl} className="rounded-[8px] bg-accent px-2.5 py-1.5 text-[12px] font-medium text-white">
                    {currentEditor.isActive('image') ? 'Mettre a jour' : "Insérer l'URL"}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      ), document.body)}

      {imageToolbarPos && !activePopover && createPortal((
        <div
          style={{ top: imageToolbarPos.top, left: imageToolbarPos.left, zIndex: 2147483647 }}
          className="fixed flex items-center gap-1 rounded-[12px] border border-border-strong bg-surface px-2 py-1.5 shadow-[0_12px_40px_rgba(0,0,0,0.2)]"
          onMouseDown={(e) => e.preventDefault()}
        >
          {IMAGE_WIDTH_PRESETS.map((preset) => (
            <button
              key={preset}
              type="button"
              onClick={() => applyImageWidth(preset)}
              className={`rounded-[6px] px-2 py-1 text-[11px] font-medium transition-colors ${
                parseImageWidth(imageWidth) === preset
                  ? 'bg-accent text-white'
                  : 'text-secondary hover:bg-[#e5e5e7]'
              }`}
            >
              {preset}%
            </button>
          ))}
          <div className="mx-1 h-5 w-px bg-border" />
          <button
            type="button"
            onClick={replaceSelectedImage}
            className="rounded-[6px] px-2 py-1 text-[11px] font-medium text-secondary hover:bg-[#e5e5e7] transition-colors"
            title="Remplacer"
          >
            <Image size={12} />
          </button>
          <button
            type="button"
            onClick={() => {
              const e = editorRef.current
              if (!e) return
              e.chain().focus().deleteSelection().run()
              setImageToolbarPos(null)
            }}
            className="rounded-[6px] px-2 py-1 text-[11px] font-medium text-danger hover:bg-danger/5 transition-colors"
            title="Supprimer"
          >
            <Trash2 size={12} />
          </button>
        </div>
      ), document.body)}

      {imageToolbarPos && !activePopover && createPortal((
        <div
          style={{
            top: imageToolbarPos.top + 40,
            left: imageToolbarPos.left,
            zIndex: 2147483646,
          }}
          className="fixed w-[220px] rounded-[10px] border border-border bg-surface p-2 shadow-lg"
          onMouseDown={(e) => e.preventDefault()}
        >
          <label className="flex flex-col gap-0.5 text-[10px] text-secondary">
            Texte alternatif
            <div className="flex gap-1">
              <input
                value={imageAlt}
                onChange={(e) => setImageAlt(e.target.value)}
                placeholder="Description"
                className="flex-1 h-7 rounded-[6px] border border-border px-2 text-[11px] text-primary outline-none focus:border-accent/60"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') { e.preventDefault(); applyImageAltCb() }
                }}
              />
              <button
                type="button"
                onClick={applyImageAltCb}
                className="rounded-[6px] bg-accent px-2 text-[10px] font-medium text-white"
              >
                OK
              </button>
            </div>
          </label>
        </div>
      ), document.body)}
    </div>
  )
}
