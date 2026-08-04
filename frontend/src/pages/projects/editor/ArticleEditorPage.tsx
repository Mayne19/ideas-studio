import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams, useBlocker } from 'react-router-dom'
import { useEditor, EditorContent } from '@tiptap/react'
import { Mark, mergeAttributes } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import UnderlineExtension from '@tiptap/extension-underline'
import LinkExtension from '@tiptap/extension-link'
import Placeholder from '@tiptap/extension-placeholder'
import TaskList from '@tiptap/extension-task-list'
import TaskItem from '@tiptap/extension-task-item'
import { Table } from '@tiptap/extension-table'
import { TableRow } from '@tiptap/extension-table-row'
import { TableHeader } from '@tiptap/extension-table-header'
import { TableCell } from '@tiptap/extension-table-cell'
import { CalloutExtension } from '@/lib/tiptap/CalloutExtension'
import { EditorImageExtension } from '@/lib/tiptap/EditorImageExtension'
import {
  Eye, BarChart2, Settings, History, Loader2, RefreshCw,
  AlertCircle, MessageCircle, ChevronDown, ChevronUp, Plus, Trash2,
  BookOpen, Type, Check, Send, Undo2, Redo2, PencilLine,
} from '@/components/ui/hugeIcons'
import { getEditorArticle, autosaveArticle } from '@/api/editor'
import { listCategories } from '@/api/categories'
import { listCalloutTemplates } from '@/api/callouts'
import { listMembers } from '@/api/members'
import {
  createComment,
  deleteComment,
  listComments,
  resolveComment,
  type ArticleComment,
} from '@/api/comments'
import {
  publishArticle, promoteArticle, unpublishArticle, markReadyArticle, archiveArticle, unarchiveArticle, scheduleArticle, unscheduleArticle,
  type PromoteResponse,
} from '@/api/articles'
import { ApiError } from '@/api/client'
import type { EditorArticle, Category, ProjectMember, SeoAnalysis, ReadyCheck, CalloutTemplate } from '@/types'
import { ArticleStatus, type ArticleStatusCode } from '@/lib/status'
import EditorToolbar from '@/components/editor/EditorToolbar'
import AutosaveIndicator from '@/components/editor/AutosaveIndicator'
import AnalysePanel from '@/components/editor/AnalysePanel'
import VersionsPanel from '@/components/editor/VersionsPanel'
import CommentsPanel from '@/components/editor/CommentsPanel'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'
import StatusBadge from '@/components/ui/StatusBadge'
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/Popover'
import Button from '@/components/ui/Button'
import { useAuth } from '@/context/AuthContext'
import { formatDate } from '@/utils/format'

// ─── Types ────────────────────────────────────────────────────────────────────

export type MetaFields = {
  title: string
  slug: string
  excerpt: string
  meta_title: string
  meta_description: string
  keyword: string
  category_id: string
  sub_niche: string
}

type FaqItem = { question: string; answer: string }
type ViewMode = 'read' | 'edit' | 'comment'
type RightTab = 'publish' | 'analyse' | 'versions'
type CommentAnchor = { text: string; top: number; left: number; from: number; to: number }
type ArticleSchedule = { scheduled_for: string | null; published_at: string | null }

const GENERATING_STATUSES: ArticleStatusCode[] = [ArticleStatus.WRITING_REQUESTED, ArticleStatus.WRITING_IN_PROGRESS]

const RIGHT_TABS: { key: RightTab; label: string; icon: React.ReactNode }[] = [
  { key: 'publish',  label: 'Publication', icon: <Settings size={13} /> },
  { key: 'analyse',  label: 'Analyse',     icon: <BarChart2 size={13} /> },
  { key: 'versions', label: 'Versions',    icon: <History size={13} /> },
]

type AutosaveStatus = 'idle' | 'saving' | 'saved' | 'error'

const EMPTY_META: MetaFields = {
  title: '', slug: '', excerpt: '', meta_title: '', meta_description: '', keyword: '', category_id: '', sub_niche: '',
}

const CommentMark = Mark.create({
  name: 'commentMark',
  addAttributes() {
    return {
      id: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-comment-id'),
        renderHTML: (attributes) => ({ 'data-comment-id': attributes.id }),
      },
    }
  },
  parseHTML() {
    return [{ tag: 'span[data-comment-id]' }]
  },
  renderHTML({ HTMLAttributes }) {
    return ['span', mergeAttributes(HTMLAttributes, { class: 'comment-mark' }), 0]
  },
})

// ─── Small helpers ─────────────────────────────────────────────────────────────

function Field({
  label, children, hint,
}: { label: string; children: React.ReactNode; hint?: string }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-[12px] font-medium text-secondary">{label}</label>
      {children}
      {hint && <p className="text-[10px] text-tertiary">{hint}</p>}
    </div>
  )
}

const INPUT = 'w-full rounded-[8px] border border-border bg-surface px-2.5 py-1.5 text-[12px] text-primary placeholder:text-tertiary focus:outline-none focus:ring-1 focus:ring-accent/50 focus:border-accent/60 transition-colors'

function translateError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 409) return "Action impossible dans l'état actuel."
    if (err.status === 403) return 'Permission insuffisante.'
    return err.message || `Erreur ${err.status}`
  }
  return 'Une erreur inattendue est survenue.'
}

function parseFaqItems(value: unknown): FaqItem[] {
  if (Array.isArray(value)) {
    return value.filter((item): item is FaqItem =>
      item !== null &&
      typeof item === 'object' &&
      typeof (item as FaqItem).question === 'string' &&
      typeof (item as FaqItem).answer === 'string'
    )
  }
  return []
}

function serializeFaqItems(items: FaqItem[]): FaqItem[] {
  return items.filter((item) => item.question.trim() || item.answer.trim())
}

function normalizeOptionalText(value: string | null | undefined): string | null {
  const trimmed = value?.trim() ?? ''
  return trimmed ? trimmed : null
}

function normalizeReadingTime(value: number | null | undefined): number | null {
  return typeof value === 'number' && Number.isFinite(value) && value >= 1
    ? Math.round(value)
    : null
}

function isEffectivelyEmptyHtml(value: string | null | undefined): boolean {
  const html = value ?? ''
  const text = html
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/\u00a0/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  return text === ''
}

// ─── Main component ────────────────────────────────────────────────────────────

export default function ArticleEditorPage() {
  const { projectId, articleId } = useParams<{ projectId: string; articleId: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()

  // Load state
  const [article, setArticle] = useState<EditorArticle | null>(null)
  const [loadStatus, setLoadStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [isGenerating, setIsGenerating] = useState(false)
  const [generationTimedOut, setGenerationTimedOut] = useState(false)

  // Editor UI state
  const [viewMode, setViewMode] = useState<ViewMode>('edit')
  const [rightTab, setRightTab] = useState<RightTab>('publish')
  const [autosaveStatus, setAutosaveStatus] = useState<AutosaveStatus>('idle')
  const [latestSeoAnalysis, setLatestSeoAnalysis] = useState<SeoAnalysis | null>(null)
  const [latestReadyCheck, setLatestReadyCheck] = useState<ReadyCheck | null>(null)

  // Content fields
  const [metaFields, setMetaFields] = useState<MetaFields>(EMPTY_META)
  const [categories, setCategories] = useState<Category[]>([])
  const [calloutTemplates, setCalloutTemplates] = useState<CalloutTemplate[]>([])
  const [members, setMembers] = useState<ProjectMember[]>([])
  const [manualAuthorName, setManualAuthorName] = useState('')
  const [manualReadingTime, setManualReadingTime] = useState<number | null>(null)
  const [faqItems, setFaqItems] = useState<FaqItem[]>([])
  const [faqOpen, setFaqOpen] = useState(false)
  const [articleSchedule, setArticleSchedule] = useState<ArticleSchedule>({ scheduled_for: null, published_at: null })

  // Publication actions
  const [actionError, setActionError] = useState('')
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [scheduleDate, setScheduleDate] = useState('')
  const [scheduleTime, setScheduleTime] = useState('')

  // Inline comment state
  const [commentAnchor, setCommentAnchor] = useState<CommentAnchor | null>(null)
  const [selectedCommentId, setSelectedCommentId] = useState<string | null>(null)
  const [selectedCommentPopup, setSelectedCommentPopup] = useState<{ top: number; left: number } | null>(null)
  const [comments, setComments] = useState<ArticleComment[]>([])
  const [commentsLoading, setCommentsLoading] = useState(true)
  const [commentInput, setCommentInput] = useState('')
  const [sendingComment, setSendingComment] = useState(false)
  const [commentRefreshKey, setCommentRefreshKey] = useState(0)
  const commentPopoverRef = useRef<HTMLDivElement>(null)

  // Refs (stable references for closures)
  const metaRef = useRef<MetaFields>(EMPTY_META)
  const faqRef = useRef<FaqItem[]>([])
  const authorNameRef = useRef('')
  const readingTimeRef = useRef<number | null>(null)
  const featuredRef = useRef(false)
  const autosaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pendingSaveRef = useRef(false)
  const titleRef = useRef<HTMLTextAreaElement>(null)
  const isHydratingEditorRef = useRef(false)
  const lastHydratedArticleIdRef = useRef<string | null>(null)
  const lastHydratedContentRef = useRef<string | null>(null)
  const slugManuallyEditedRef = useRef(false)

  // Navigation blocker
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      (pendingSaveRef.current || autosaveStatus === 'saving') &&
      currentLocation.pathname !== nextLocation.pathname
  )

  // ─── TipTap editor ──────────────────────────────────────────────────────────

  const editor = useEditor({
    extensions: [
      StarterKit,
      UnderlineExtension,
      LinkExtension.configure({ openOnClick: false }),
      EditorImageExtension,
      Placeholder.configure({ placeholder: 'Commencez à rédiger votre article…' }),
      TaskList,
      TaskItem.configure({ nested: true }),
      Table.configure({
        resizable: true,
        HTMLAttributes: { class: 'editor-table' },
      }),
      TableRow,
      TableHeader,
      TableCell,
      CalloutExtension.configure({
        HTMLAttributes: { 'data-block-type': 'callout' },
      }),
      CommentMark,
    ],
    content: '',
    editable: true,
    editorProps: {
      attributes: {
        class: 'tiptap-content min-h-[58vh] px-10 pb-10 pt-0 [&>*:first-child]:mt-0',
      },
      handleClick: (_view, _pos, event) => {
        const target = event.target as HTMLElement
        const marked = target.closest('[data-comment-id]') as HTMLElement | null
        if (!marked) return false
        const commentId = marked.getAttribute('data-comment-id')
        if (!commentId) return false
        setSelectedCommentId(commentId)
        setSelectedCommentPopup({
          top: Math.max(12, Math.min(event.clientY + 12, window.innerHeight - 220)),
          left: Math.max(12, Math.min(event.clientX + 12, window.innerWidth - 292)),
        })
        return false
      },
    },
    onUpdate: ({ editor: e }) => {
      if (isHydratingEditorRef.current) return
      // Tant que l'hydratation initiale de CET article n'a pas eu lieu au
      // moins une fois, l'éditeur peut encore contenir son état par défaut
      // (<p></p>) hérité d'un montage précédent — sauvegarder à ce moment-là
      // écraserait la vraie révision avec un corps vide (observé en
      // production : révisions "human" à 7 caractères remplaçant un article
      // de 13800 caractères généré par l'IA).
      if (lastHydratedArticleIdRef.current !== articleId) return
      scheduleAutosave(e.getHTML())
    },
  })

  useEffect(() => {
    if (editor) editor.setEditable(viewMode === 'edit')
  }, [editor, viewMode])

  const activeRightTab: RightTab = rightTab

  // ─── Autosave ───────────────────────────────────────────────────────────────

  const scheduleAutosave = useCallback((html: string) => {
    if (autosaveTimer.current) clearTimeout(autosaveTimer.current)
    const pid = projectId
    const aid = articleId
    // Défense en profondeur : les handlers de champs meta (titre, catégorie,
    // FAQ...) appellent scheduleAutosave(editor?.getHTML() ?? '') sans passer
    // par le garde d'hydratation de onUpdate — si l'un d'eux se déclenche
    // avant l'hydratation initiale de cet article, ne rien planifier plutôt
    // que d'écraser la révision existante avec un contenu vide.
    if (lastHydratedArticleIdRef.current !== aid) return
    pendingSaveRef.current = true
    autosaveTimer.current = setTimeout(() => {
      if (!pid || !aid) return
      setAutosaveStatus('saving')
      autosaveArticle(pid, aid, {
        content: html,
        title: metaRef.current.title || undefined,
        slug: metaRef.current.slug || undefined,
        excerpt: metaRef.current.excerpt || undefined,
        keyword: normalizeOptionalText(metaRef.current.keyword),
        meta_title: metaRef.current.meta_title || undefined,
        meta_description: metaRef.current.meta_description || undefined,
        category_id: normalizeOptionalText(metaRef.current.category_id),
        sub_niche: normalizeOptionalText(metaRef.current.sub_niche),
        is_featured: featuredRef.current,
        faq: serializeFaqItems(faqRef.current),
        author_name: normalizeOptionalText(authorNameRef.current),
      })
        .then((response) => {
          pendingSaveRef.current = false
          setArticle((prev) => prev ? {
            ...prev,
            title: metaRef.current.title,
            slug: metaRef.current.slug,
            excerpt: metaRef.current.excerpt,
            keyword: normalizeOptionalText(metaRef.current.keyword),
            meta_title: normalizeOptionalText(metaRef.current.meta_title),
            meta_description: normalizeOptionalText(metaRef.current.meta_description),
            category_id: normalizeOptionalText(metaRef.current.category_id),
            sub_niche: normalizeOptionalText(metaRef.current.sub_niche),
            is_featured: featuredRef.current,
            content: html,
            faq: serializeFaqItems(faqRef.current),
            author_name: normalizeOptionalText(authorNameRef.current),
            reading_time_minutes: normalizeReadingTime(readingTimeRef.current),
            word_count: response.word_count,
            updated_at: response.updated_at,
          } : prev)
          setAutosaveStatus('saved')
          setTimeout(() => setAutosaveStatus('idle'), 3000)
        })
        .catch(() => {
          pendingSaveRef.current = false
          setAutosaveStatus('error')
        })
    }, 2000)
  }, [projectId, articleId])

  const handleSaveNow = useCallback(async () => {
    if (autosaveTimer.current) clearTimeout(autosaveTimer.current)
    const pid = projectId
    const aid = articleId
    if (!pid || !aid) return false
    // Même garde que onUpdate : ne jamais persister le contenu de l'éditeur
    // avant que l'hydratation initiale de cet article ait eu lieu, sinon un
    // save déclenché tôt (blocker de navigation, Ctrl+S, beforeunload)
    // écrase la vraie révision avec l'état par défaut vide de TipTap.
    if (lastHydratedArticleIdRef.current !== aid) return false
    setAutosaveStatus('saving')
    try {
      const content = editor?.getHTML() ?? ''
      const response = await autosaveArticle(pid, aid, {
        content,
        title: metaRef.current.title || undefined,
        slug: metaRef.current.slug || undefined,
        excerpt: metaRef.current.excerpt || undefined,
        keyword: normalizeOptionalText(metaRef.current.keyword),
        meta_title: metaRef.current.meta_title || undefined,
        meta_description: metaRef.current.meta_description || undefined,
        category_id: normalizeOptionalText(metaRef.current.category_id),
        sub_niche: normalizeOptionalText(metaRef.current.sub_niche),
        is_featured: featuredRef.current,
        faq: serializeFaqItems(faqRef.current),
        author_name: normalizeOptionalText(authorNameRef.current),
      })
      pendingSaveRef.current = false
      setArticle((prev) => prev ? {
        ...prev,
        title: metaRef.current.title,
        slug: metaRef.current.slug,
        excerpt: metaRef.current.excerpt,
        keyword: normalizeOptionalText(metaRef.current.keyword),
        meta_title: normalizeOptionalText(metaRef.current.meta_title),
        meta_description: normalizeOptionalText(metaRef.current.meta_description),
        category_id: normalizeOptionalText(metaRef.current.category_id),
        sub_niche: normalizeOptionalText(metaRef.current.sub_niche),
        is_featured: featuredRef.current,
        content,
        faq: serializeFaqItems(faqRef.current),
        author_name: normalizeOptionalText(authorNameRef.current),
        reading_time_minutes: normalizeReadingTime(readingTimeRef.current),
        word_count: response.word_count,
        updated_at: response.updated_at,
      } : prev)
      setAutosaveStatus('saved')
      setTimeout(() => setAutosaveStatus('idle'), 3000)
      return true
    } catch {
      pendingSaveRef.current = false
      setAutosaveStatus('error')
      return false
    }
  }, [articleId, editor, projectId])

  useEffect(() => {
    if (blocker.state !== 'blocked') return
    void handleSaveNow().then((saved) => {
      if (saved) blocker.proceed?.()
      else blocker.reset?.()
    })
  }, [blocker, handleSaveNow])

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault()
        void handleSaveNow()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleSaveNow])

  useEffect(() => {
    function handleBeforeUnload(e: BeforeUnloadEvent) {
      if (pendingSaveRef.current || autosaveStatus === 'saving') e.preventDefault()
    }
    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [autosaveStatus])

  // ─── Data loading ────────────────────────────────────────────────────────────

  const hydrateFromArticle = useCallback((art: EditorArticle, options: { setContent?: boolean } = {}) => {
    setArticle(art)
    const meta: MetaFields = {
      title: art.title ?? '',
      slug: art.slug ?? '',
      excerpt: art.excerpt ?? '',
      meta_title: art.meta_title ?? '',
      meta_description: art.meta_description ?? '',
      keyword: art.keyword ?? '',
      category_id: art.category_id ?? '',
      sub_niche: art.sub_niche ?? '',
    }
    setMetaFields(meta)
    metaRef.current = meta
    const faq = parseFaqItems(art.faq)
    setFaqItems(faq)
    faqRef.current = faq
    setManualAuthorName(art.author_name ?? '')
    authorNameRef.current = art.author_name ?? ''
    setManualReadingTime(normalizeReadingTime(art.reading_time_minutes))
    readingTimeRef.current = normalizeReadingTime(art.reading_time_minutes)
    featuredRef.current = Boolean(art.is_featured)
    if (options.setContent && editor && art.content) editor.commands.setContent(art.content)
  }, [editor])

  useEffect(() => {
    if (!projectId || !articleId) return
    Promise.all([
      getEditorArticle(projectId, articleId),
      listCategories(projectId),
      listCalloutTemplates(projectId).catch(() => [] as CalloutTemplate[]),
      listMembers(projectId).catch(() => [] as ProjectMember[]),
    ])
      .then(([art, cats, callouts, mems]) => {
        setCategories(cats)
        setCalloutTemplates(callouts)
        setMembers(mems)
        setLatestSeoAnalysis(null)
        setLatestReadyCheck(null)
        setArticleSchedule({ scheduled_for: null, published_at: null })
        hydrateFromArticle(art)
        slugManuallyEditedRef.current = false
        setIsGenerating(GENERATING_STATUSES.includes(art.status))
        setLoadStatus('success')
      })
      .catch(() => setLoadStatus('error'))
  }, [projectId, articleId, user?.id, hydrateFromArticle])

  useEffect(() => {
    if (!editor || !article) return

    const incomingContent = article.content ?? ''
    const currentHtml = editor.getHTML()
    const currentArticleId = article.id
    const lastHydratedArticleId = lastHydratedArticleIdRef.current
    const lastHydratedContent = lastHydratedContentRef.current
    const articleChanged = lastHydratedArticleId !== currentArticleId
    const contentChangedSinceHydration = lastHydratedContent !== incomingContent
    const editorIsSafeToHydrate =
      articleChanged ||
      isEffectivelyEmptyHtml(currentHtml) ||
      currentHtml === (lastHydratedContent ?? '')

    if (!editorIsSafeToHydrate || (!contentChangedSinceHydration && !articleChanged)) return

    isHydratingEditorRef.current = true
    try {
      editor.commands.setContent(incomingContent, { emitUpdate: false })
    } finally {
      isHydratingEditorRef.current = false
    }
    lastHydratedArticleIdRef.current = currentArticleId
    lastHydratedContentRef.current = incomingContent
  }, [editor, article])

  useEffect(() => {
    if (!articleId) return
    let active = true
    Promise.resolve().then(() => { if (active) setCommentsLoading(true) })
    listComments(articleId)
      .then((items) => {
        if (active) setComments(items)
      })
      .catch(() => {
        if (active) setComments([])
      })
      .finally(() => {
        if (active) setCommentsLoading(false)
      })
    return () => { active = false }
  }, [articleId, commentRefreshKey])

  function handleCalloutTemplateCreated(template: CalloutTemplate) {
    setCalloutTemplates((current) => {
      if (current.some((item) => item.id === template.id)) return current
      return [...current, template]
    })
  }

  useEffect(() => {
    if (!selectedCommentId) return
    const stillVisible = comments.some((comment) => comment.id === selectedCommentId && !comment.resolved)
    if (!stillVisible) {
      Promise.resolve().then(() => {
        setSelectedCommentId(null)
        setSelectedCommentPopup(null)
      })
    }
  }, [comments, selectedCommentId])

  // ─── Generation polling ──────────────────────────────────────────────────────

  useEffect(() => {
    if (!isGenerating || !projectId || !articleId) return
    let count = 0
    const id = setInterval(async () => {
      count++
      if (count > 40) {
        clearInterval(id)
        setIsGenerating(false)
        setGenerationTimedOut(true)
        return
      }
      try {
        const art = await getEditorArticle(projectId, articleId)
        if (!GENERATING_STATUSES.includes(art.status)) {
          clearInterval(id)
          setIsGenerating(false)
          setGenerationTimedOut(false)
          hydrateFromArticle(art, { setContent: true })
        }
      } catch { /* ignore poll errors */ }
    }, 3000)
    return () => clearInterval(id)
  }, [isGenerating, projectId, articleId, editor, hydrateFromArticle])

  async function handleRefreshGeneration() {
    if (!projectId || !articleId) return
    setGenerationTimedOut(false)
    try {
      const art = await getEditorArticle(projectId, articleId)
      if (GENERATING_STATUSES.includes(art.status)) {
        setIsGenerating(true)
      } else {
        setIsGenerating(false)
        hydrateFromArticle(art, { setContent: true })
      }
    } catch { /* ignore */ }
  }

  // ─── Comment mode selection ──────────────────────────────────────────────────

  useEffect(() => {
    if (viewMode !== 'comment' || !editor) return

    function handleMouseUp(e: MouseEvent) {
      if (commentPopoverRef.current?.contains(e.target as Node)) return
      setSelectedCommentPopup(null)
      const sel = window.getSelection()
      if (!sel || sel.rangeCount === 0) { setCommentAnchor(null); return }
      const text = sel.toString().trim()
      if (!text) { setCommentAnchor(null); return }
      const rangeForPosition = sel.getRangeAt(0)
      let from = editor.state.selection.from
      let to = editor.state.selection.to
      try {
        from = editor.view.posAtDOM(rangeForPosition.startContainer, rangeForPosition.startOffset)
        to = editor.view.posAtDOM(rangeForPosition.endContainer, rangeForPosition.endOffset)
      } catch {
        // Keep the ProseMirror selection as fallback.
      }
      const start = Math.min(from, to)
      const end = Math.max(from, to)
      if (start === end) { setCommentAnchor(null); return }
      const range = rangeForPosition
      const rect = range.getBoundingClientRect()
      if (rect.width === 0 && rect.height === 0) { setCommentAnchor(null); return }
      const top = rect.bottom + 8
      const left = Math.max(8, Math.min(rect.left, window.innerWidth - 264))
      setCommentAnchor({ text, top, left, from: start, to: end })
      setCommentInput('')
    }

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') { setCommentAnchor(null); setCommentInput('') }
    }

    document.addEventListener('mouseup', handleMouseUp)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mouseup', handleMouseUp)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [viewMode, editor])

  // ─── Field change handlers ───────────────────────────────────────────────────

  function slugify(text: string): string {
    return text.toLowerCase().trim()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^\w\s-]/g, '')
      .replace(/[\s_]+/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '') || 'item'
  }

  function handleMetaChange(name: keyof MetaFields, value: string) {
    const next = { ...metaRef.current, [name]: value }
    if (name === 'title' && !slugManuallyEditedRef.current && article && article.status !== ArticleStatus.PUBLISHED) {
      next.slug = slugify(value || 'item')
    }
    if (name === 'slug') {
      slugManuallyEditedRef.current = true
    }
    metaRef.current = next
    setMetaFields(next)
    if (name === 'title') setArticle((prev) => prev ? { ...prev, title: value, slug: next.slug } : prev)
    scheduleAutosave(editor?.getHTML() ?? '')
  }

  function handleCategoryChange(categoryId: string) {
    const next = { ...metaRef.current, category_id: categoryId }
    metaRef.current = next
    setMetaFields(next)
    setArticle((prev) => prev ? {
      ...prev,
      category_id: normalizeOptionalText(next.category_id),
    } : prev)
    scheduleAutosave(editor?.getHTML() ?? '')
  }

  function handleSubNicheChange(value: string) {
    const next = { ...metaRef.current, sub_niche: value }
    metaRef.current = next
    setMetaFields(next)
    setArticle((prev) => prev ? {
      ...prev,
      sub_niche: normalizeOptionalText(next.sub_niche),
    } : prev)
    scheduleAutosave(editor?.getHTML() ?? '')
  }

  function handleAuthorNameChange(value: string) {
    authorNameRef.current = value
    setManualAuthorName(value)
    setArticle((prev) => prev ? { ...prev, author_name: normalizeOptionalText(value) } : prev)
    scheduleAutosave(editor?.getHTML() ?? '')
  }

  function handleReadingTimeChange(value: string) {
    const trimmed = value.trim()
    const nextValue = trimmed ? normalizeReadingTime(Number(trimmed)) : null
    readingTimeRef.current = nextValue
    setManualReadingTime(nextValue)
    setArticle((prev) => prev ? { ...prev, reading_time_minutes: nextValue } : prev)
    scheduleAutosave(editor?.getHTML() ?? '')
  }

  function handleTitleInput(e: React.ChangeEvent<HTMLTextAreaElement>) {
    handleMetaChange('title', e.target.value)
    e.currentTarget.style.height = 'auto'
    e.currentTarget.style.height = `${e.currentTarget.scrollHeight}px`
  }

  useEffect(() => {
    const title = titleRef.current
    if (!title) return
    title.style.height = 'auto'
    title.style.height = `${title.scrollHeight}px`
  }, [metaFields.title])

  function handleFaqChange(index: number, field: keyof FaqItem, value: string) {
    const next = faqItems.map((item, i) => i === index ? { ...item, [field]: value } : item)
    setFaqItems(next)
    faqRef.current = next
    scheduleAutosave(editor?.getHTML() ?? '')
  }

  function handleFaqAdd() {
    const next = [...faqItems, { question: '', answer: '' }]
    setFaqItems(next)
    faqRef.current = next
    setFaqOpen(true)
    scheduleAutosave(editor?.getHTML() ?? '')
  }

  function handleFaqDelete(index: number) {
    const next = faqItems.filter((_, i) => i !== index)
    setFaqItems(next)
    faqRef.current = next
    scheduleAutosave(editor?.getHTML() ?? '')
  }

  // ─── Publication actions ─────────────────────────────────────────────────────

  function applyArticleUpdate(updated: { status: ArticleStatusCode; updated_at: string; published_at?: string | null; scheduled_for?: string | null }) {
    setArticle((prev) => prev ? { ...prev, status: updated.status, updated_at: updated.updated_at } : prev)
    setArticleSchedule((prev) => ({
      scheduled_for: updated.scheduled_for !== undefined ? updated.scheduled_for : prev.scheduled_for,
      published_at: updated.published_at !== undefined ? updated.published_at : prev.published_at,
    }))
  }

  async function doAction(key: string) {
    if (!projectId || !article) return
    setActionLoading(key)
    setActionError('')
    try {
      if (key === 'publish' || key === 'promote') {
        if (autosaveTimer.current) clearTimeout(autosaveTimer.current)
        // Ne jamais utiliser un éditeur non hydraté comme source du contenu
        // publié — mieux vaut retomber sur article.content (déjà connu bon)
        // que de publier un corps vide par accident.
        const content = (lastHydratedArticleIdRef.current === article.id ? editor?.getHTML() : null) ?? article.content ?? ''
        await autosaveArticle(projectId, article.id, {
          content,
          title: metaRef.current.title || undefined,
          slug: metaRef.current.slug || undefined,
          excerpt: metaRef.current.excerpt || undefined,
          keyword: normalizeOptionalText(metaRef.current.keyword),
          meta_title: metaRef.current.meta_title || undefined,
          meta_description: normalizeOptionalText(metaRef.current.meta_description),
          category_id: normalizeOptionalText(metaRef.current.category_id),
          sub_niche: normalizeOptionalText(metaRef.current.sub_niche),
          is_featured: featuredRef.current,
          faq: serializeFaqItems(faqRef.current),
          author_name: normalizeOptionalText(authorNameRef.current),
        })
      }
      if (key === 'publish') {
        applyArticleUpdate(await publishArticle(projectId, article.id))
      } else if (key === 'unpublish') {
        applyArticleUpdate(await unpublishArticle(projectId, article.id))
      } else if (key === 'mark-ready') {
        applyArticleUpdate(await markReadyArticle(projectId, article.id))
      } else if (key === 'archive') {
        applyArticleUpdate(await archiveArticle(projectId, article.id))
      } else if (key === 'unarchive') {
        applyArticleUpdate(await unarchiveArticle(projectId, article.id))
      } else if (key === 'unschedule') {
        applyArticleUpdate(await unscheduleArticle(projectId, article.id))
      }
    } catch (err) {
      setActionError(translateError(err))
    } finally {
      setActionLoading(null)
    }
  }

  async function handlePromote() {
    if (!projectId || !article) return
    setActionLoading('promote')
    setActionError('')
    try {
      if (autosaveTimer.current) clearTimeout(autosaveTimer.current)
      const content = editor?.getHTML() ?? article.content ?? ''
      await autosaveArticle(projectId, article.id, {
        content,
        title: metaRef.current.title || undefined,
        slug: metaRef.current.slug || undefined,
        excerpt: metaRef.current.excerpt || undefined,
        keyword: normalizeOptionalText(metaRef.current.keyword),
        meta_title: metaRef.current.meta_title || undefined,
        meta_description: normalizeOptionalText(metaRef.current.meta_description),
        category_id: normalizeOptionalText(metaRef.current.category_id),
        sub_niche: normalizeOptionalText(metaRef.current.sub_niche),
        is_featured: featuredRef.current,
        faq: serializeFaqItems(faqRef.current),
        author_name: normalizeOptionalText(authorNameRef.current),
      })
      const updated: PromoteResponse = await promoteArticle(projectId, article.id)
      applyArticleUpdate(updated)
    } catch (err) {
      setActionError(translateError(err))
    } finally {
      setActionLoading(null)
    }
  }

  async function handleSchedule() {
    if (!projectId || !article || !scheduleDate || !scheduleTime) return
    setActionLoading('schedule')
    setActionError('')
    try {
      const iso = new Date(`${scheduleDate}T${scheduleTime}`).toISOString()
      const updated = await scheduleArticle(projectId, article.id, iso)
      applyArticleUpdate(updated)
      setScheduleDate('')
      setScheduleTime('')
    } catch (err) {
      setActionError(translateError(err))
    } finally {
      setActionLoading(null)
    }
  }

  async function handleSendInlineComment() {
    if (!articleId || !commentAnchor || !commentInput.trim() || !editor) return
    setSendingComment(true)
    try {
      const comment = await createComment(articleId, commentInput.trim(), commentAnchor.text)
      editor.setEditable(true)
      editor
        .chain()
        .focus()
        .setTextSelection({ from: commentAnchor.from, to: commentAnchor.to })
        .setMark('commentMark', { id: comment.id })
        .run()
      editor.commands.setTextSelection(commentAnchor.to)
      editor.setEditable(viewMode === 'edit')
      scheduleAutosave(editor.getHTML())
      setComments((prev) => [comment, ...prev.filter((item) => item.id !== comment.id)])
      setSelectedCommentId(comment.id)
      setSelectedCommentPopup(null)
      setCommentAnchor(null)
      setCommentInput('')
      setCommentRefreshKey((k) => k + 1)
    } catch { /* ignore */ }
    finally {
      setSendingComment(false)
    }
  }

  function removeCommentMark(commentId: string) {
    if (!editor) return
    const markType = editor.schema.marks['commentMark']
    if (!markType) return

    let tr = editor.state.tr
    editor.state.doc.descendants((node, pos) => {
      if (!node.isText) return
      const hasComment = node.marks.some((mark) => mark.type === markType && mark.attrs['id'] === commentId)
      if (hasComment) tr = tr.removeMark(pos, pos + node.nodeSize, markType)
    })

    if (tr.docChanged) {
      editor.view.dispatch(tr)
      scheduleAutosave(editor.getHTML())
    }
  }

  async function handleResolveInlineComment(id: string, resolved = true) {
    if (!articleId) return
    const updated = await resolveComment(articleId, id, resolved)
    setComments((prev) => prev.map((comment) => comment.id === id ? updated : comment))
    if (resolved) {
      removeCommentMark(id)
      setSelectedCommentId(null)
      setSelectedCommentPopup(null)
    }
  }

  async function handleDeleteInlineComment(id: string) {
    if (!articleId) return
    await deleteComment(articleId, id)
    removeCommentMark(id)
    setComments((prev) => prev.filter((comment) => comment.id !== id))
    setSelectedCommentId(null)
    setSelectedCommentPopup(null)
  }

  // ─── Derived values ──────────────────────────────────────────────────────────

  const wordCount = editor
    ? editor.getText().split(/\s+/).filter(Boolean).length
    : (article?.word_count ?? 0)

  const sortedCategories = useMemo(
    () => [...categories].sort((a, b) => a.name.localeCompare(b.name, 'fr')),
    [categories],
  )

  const calculatedReadingTime = Math.max(1, Math.ceil(wordCount / 200))
  const readingTime = normalizeReadingTime(manualReadingTime) ?? calculatedReadingTime
  const isEditable = viewMode === 'edit'
  const busy = actionLoading !== null
  const selectedComment = comments.find((comment) => comment.id === selectedCommentId) ?? null

  // ─── Loading / error ─────────────────────────────────────────────────────────

  if (loadStatus === 'loading') return <LoadingState />
  if (loadStatus === 'error' || !article) {
    return <ErrorState message="Impossible de charger l'article." onRetry={() => navigate(0)} />
  }

  // ─── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="flex h-full flex-col min-h-0">
      {/* Generation overlay */}
      {(isGenerating || generationTimedOut) && (
        <div className="flex flex-1 items-center justify-center">
          <div className="flex flex-col items-center gap-4 text-center max-w-xs">
            <div className={`flex h-12 w-12 items-center justify-center rounded-[16px] ${generationTimedOut ? 'bg-danger/8' : 'bg-accent/10'}`}>
              {generationTimedOut
                ? <AlertCircle size={22} className="text-danger" />
                : <Loader2 size={22} className="animate-spin text-accent" />
              }
            </div>
            <div>
              <p className="text-[15px] font-medium text-primary">
                {generationTimedOut ? 'La génération prend plus de temps que prévu' : 'Génération en cours…'}
              </p>
              <p className="mt-1 text-[14px] text-secondary">
                {generationTimedOut
                  ? 'Cliquez sur Rafraîchir pour vérifier si le brouillon est disponible.'
                  : "L'IA rédige votre brouillon. La page se mettra à jour automatiquement."
                }
              </p>
            </div>
            <button
              onClick={handleRefreshGeneration}
              className={`flex items-center gap-1.5 rounded-[10px] px-4 py-2 text-[14px] font-medium transition-colors ${
                generationTimedOut ? 'bg-accent text-white hover:bg-accent/90' : 'bg-surface-soft text-secondary hover:bg-surface-muted'
              }`}
            >
              <RefreshCw size={13} />
              Rafraîchir
            </button>
            <button onClick={() => navigate(`/projects/${projectId}/production?tab=ideas`)} className="text-[12px] text-tertiary hover:text-secondary transition-colors">
              ← Retour à la production
            </button>
          </div>
        </div>
      )}

      {/* 3-card layout */}
      {!isGenerating && !generationTimedOut && (
        <div className="grid min-h-0 flex-1 grid-cols-[56px_minmax(0,1fr)_300px] items-start gap-4 overflow-y-auto overflow-x-hidden p-4 max-xl:grid-cols-[52px_minmax(0,1fr)_280px]">

          {/* ── LEFT: Toolbar card ── */}
          <div className="sticky top-0 flex max-h-[calc(100vh-112px)] min-w-0 flex-col overflow-y-auto rounded-[14px] border border-border bg-surface">
            <EditorToolbar
              editor={editor}
              projectId={projectId}
              articleId={articleId}
              calloutTemplates={calloutTemplates}
              onCalloutTemplateCreated={handleCalloutTemplateCreated}
              disabled={viewMode !== 'edit'}
            />
          </div>

          {/* ── CENTER: Article card ── */}
          <div className={`flex min-w-0 flex-col overflow-hidden rounded-[14px] border border-border ${!isEditable ? 'bg-app' : 'bg-surface'}`}>

            {/* Internal bar */}
            <div className="flex items-center justify-between gap-2 px-4 py-2 border-b border-border shrink-0 bg-surface">
              {/* Left: back + autosave */}
              <div className="flex items-center gap-2 min-w-0">
                <div className="flex rounded-[10px] bg-surface-soft p-1">
                  {([
                    { mode: 'read' as ViewMode, label: 'Lecture', icon: <BookOpen size={12} /> },
                    { mode: 'edit' as ViewMode, label: 'Édition', icon: <PencilLine size={12} /> },
                    { mode: 'comment' as ViewMode, label: 'Commentaire', icon: <MessageCircle size={12} /> },
                  ]).map(({ mode, label, icon }) => (
                    <button
                      key={mode}
                      onClick={() => setViewMode(mode)}
                      className={`flex h-7 items-center gap-1.5 rounded-[7px] px-2.5 text-[12px] font-medium transition-all ${
                        viewMode === mode
                          ? 'bg-surface text-primary shadow-none'
                          : 'text-secondary hover:text-primary'
                      }`}
                    >
                      {icon}
                      {label}
                    </button>
                  ))}
                </div>
                <span className="text-border text-[10px]">·</span>
                <span className="hidden text-[12px] text-secondary truncate max-w-[200px]">
                  {metaFields.title || article.title}
                </span>
                <AutosaveIndicator status={autosaveStatus} />
              </div>

              {/* Right: word count + preview + history */}
              <div className="flex items-center gap-1.5 shrink-0">
                <div className="hidden rounded-[8px] border border-border overflow-hidden">
                  {([
                    { mode: 'read'    as ViewMode, label: 'Lecture' },
                    { mode: 'edit'    as ViewMode, label: 'Édition' },
                    { mode: 'comment' as ViewMode, label: 'Commentaire', icon: <MessageCircle size={11} /> },
                  ]).map(({ mode, label, icon }) => (
                    <button
                      key={mode}
                      onClick={() => setViewMode(mode)}
                      className={`flex items-center gap-1 px-2.5 py-1 text-[12px] font-medium transition-colors ${
                        viewMode === mode
                          ? 'bg-accent text-white'
                          : 'text-secondary hover:text-primary hover:bg-surface-soft'
                      }`}
                    >
                      {icon}
                      {label}
                    </button>
                  ))}
                </div>

                <span className="flex items-center gap-1 text-[12px] text-tertiary px-1">
                  <Type size={10} />
                  {wordCount.toLocaleString('fr-FR')}
                </span>

                <button
                  onClick={() => navigate(`/projects/${projectId}/articles/${articleId}/preview`)}
                  className="flex items-center gap-1 text-[12px] text-secondary hover:text-primary transition-colors rounded-[6px] px-2 py-1 hover:bg-surface-soft"
                >
                  <Eye size={12} />
                  Prévisualiser
                </button>
                <button
                  onClick={() => editor?.chain().focus().undo().run()}
                  disabled={!editor?.can().undo()}
                  className="flex h-7 w-7 items-center justify-center rounded-[7px] text-secondary transition-colors hover:bg-surface-soft hover:text-primary disabled:opacity-35"
                  title="Annuler"
                >
                  <Undo2 size={13} />
                </button>
                <button
                  onClick={() => editor?.chain().focus().redo().run()}
                  disabled={!editor?.can().redo()}
                  className="flex h-7 w-7 items-center justify-center rounded-[7px] text-secondary transition-colors hover:bg-surface-soft hover:text-primary disabled:opacity-35"
                  title="Refaire"
                >
                  <Redo2 size={13} />
                </button>
              </div>
            </div>

            {/* Scrollable content area */}
            <div className="flex-1 overflow-y-auto">

              {/* Comment mode banner */}
              {viewMode === 'comment' && (
                <div className="flex items-center gap-2 px-10 py-2 bg-accent/5 border-b border-accent/20">
                  <MessageCircle size={13} className="text-accent shrink-0" />
                  <span className="text-[12px] text-accent">
                    Mode commentaire — sélectionnez du texte pour ajouter un commentaire
                  </span>
                </div>
              )}

              {/* Title */}
              <div className="px-10 pt-7 pb-2">
                <textarea
                  ref={titleRef}
                  value={metaFields.title}
                  onChange={handleTitleInput}
                  readOnly={!isEditable}
                  placeholder="Titre de l'article…"
                  rows={1}
                  className={`block w-full max-w-full resize-none overflow-hidden whitespace-normal break-words bg-transparent text-[28px] font-bold leading-tight text-primary outline-none placeholder:text-tertiary/40 [overflow-wrap:anywhere] ${!isEditable ? 'cursor-default' : ''}`}
                />
              </div>

              {/* TipTap editor */}
              <EditorContent
                editor={editor}
                className={`${!isEditable ? 'cursor-default select-text' : ''}`}
              />

              {/* FAQ section */}
              <div className="px-10 py-4 border-t border-border/60 mt-4">
                <button
                  onClick={() => setFaqOpen((v) => !v)}
                  className="flex items-center gap-2 w-full text-left"
                >
                  <span className="text-[12px] font-semibold text-secondary uppercase tracking-wide flex-1">
                    FAQ {faqItems.length > 0 && `(${faqItems.length})`}
                  </span>
                  {faqOpen ? <ChevronUp size={14} className="text-tertiary" /> : <ChevronDown size={14} className="text-tertiary" />}
                </button>

                {faqOpen && (
                  <div className="mt-3 flex flex-col gap-3">
                    {faqItems.map((item, i) => (
                      <div key={i} className="rounded-[10px] border border-border bg-surface-soft p-3 flex flex-col gap-2">
                        <div className="flex items-start gap-2">
                          <input
                            type="text"
                            value={item.question}
                            onChange={(e) => handleFaqChange(i, 'question', e.target.value)}
                            placeholder="Question…"
                            className="flex-1 bg-transparent text-[14px] font-semibold text-primary outline-none placeholder:text-tertiary"
                          />
                          <button onClick={() => handleFaqDelete(i)} className="shrink-0 text-tertiary hover:text-danger transition-colors mt-0.5">
                            <Trash2 size={13} />
                          </button>
                        </div>
                        <textarea
                          rows={2}
                          value={item.answer}
                          onChange={(e) => handleFaqChange(i, 'answer', e.target.value)}
                          placeholder="Réponse…"
                          className="w-full bg-white rounded-[8px] border border-border px-2.5 py-1.5 text-[14px] text-primary placeholder:text-tertiary resize-none outline-none focus:ring-1 focus:ring-accent/50 focus:border-accent/60 transition-colors"
                        />
                      </div>
                    ))}
                    <button
                      onClick={handleFaqAdd}
                      className="flex items-center gap-1.5 text-[12px] text-accent hover:underline"
                    >
                      <Plus size={13} />
                      Ajouter FAQ
                    </button>
                  </div>
                )}

                {!faqOpen && faqItems.length === 0 && (
                  <button
                    onClick={handleFaqAdd}
                    className="mt-2 flex items-center gap-1.5 text-[12px] text-tertiary hover:text-accent transition-colors"
                  >
                    <Plus size={13} />
                    Ajouter une FAQ
                  </button>
                )}
              </div>
            </div>

            {/* Footer: word count + reading time */}
            <div className="flex items-center justify-end gap-3 px-10 py-2 border-t border-border/60 bg-surface shrink-0">
              <span className="flex items-center gap-1 text-[12px] text-tertiary">
                <BookOpen size={10} />
                {readingTime} min de lecture
              </span>
              <span className="text-[12px] text-tertiary">{wordCount.toLocaleString('fr-FR')} mots</span>
            </div>
          </div>

          {/* ── RIGHT: Panel card ── */}
          <div className="sticky top-0 flex max-h-[calc(100vh-112px)] min-w-0 flex-col overflow-hidden rounded-[14px] border border-border bg-surface">

            {/* Tab bar */}
            <div className="flex border-b border-border shrink-0">
              {RIGHT_TABS.map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setRightTab(tab.key)}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-[12px] font-medium border-b-2 transition-colors ${
                    activeRightTab === tab.key
                      ? 'border-accent text-accent'
                      : 'border-transparent text-tertiary hover:text-secondary'
                  }`}
                >
                  {tab.icon}
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab content */}
            <div className="flex-1 overflow-y-auto">

              {/* ── Publication tab ── */}
              {activeRightTab === 'publish' && (
                <div className="flex flex-col divide-y divide-border">

                  {/* Paramètres éditoriaux */}
                  <div className="p-3 flex flex-col gap-3">
                    <Field label="Mot-clé">
                      <input
                        type="text"
                        value={metaFields.keyword}
                        onChange={(e) => handleMetaChange('keyword', e.target.value)}
                        className={INPUT}
                        placeholder="ex: marketing digital"
                      />
                    </Field>

                    <Field label="Slug">
                      <div className="flex gap-1.5">
                        <input
                          type="text"
                          value={metaFields.slug}
                          onChange={(e) => handleMetaChange('slug', e.target.value)}
                          className={INPUT}
                          placeholder="/mon-article"
                        />
                        <button
                          type="button"
                          onClick={() => {
                            const s = slugify(metaFields.title || 'item')
                            handleMetaChange('slug', s)
                            slugManuallyEditedRef.current = false
                          }}
                          className="shrink-0 rounded-[8px] border border-border bg-surface px-2 text-[12px] text-secondary transition-colors hover:bg-surface-soft hover:text-primary"
                          title="Régénérer depuis le titre"
                        >
                          ↻
                        </button>
                      </div>
                    </Field>

                    <Field label="Meta description">
                      <textarea
                        rows={3}
                        value={metaFields.meta_description}
                        onChange={(e) => handleMetaChange('meta_description', e.target.value)}
                        className={`${INPUT} resize-none`}
                        placeholder="Description pour les moteurs de recherche..."
                      />
                    </Field>

                    <div className="flex flex-col gap-2">
                      <span className="text-[12px] font-medium text-secondary">Chemin éditorial</span>
                      <div className="grid grid-cols-2 gap-2">
                        <Field label="Catégorie">
                          <select
                            value={metaFields.category_id}
                            onChange={(e) => handleCategoryChange(e.target.value)}
                            className={INPUT}
                            disabled={sortedCategories.length === 0}
                          >
                            <option value="">Choisir une catégorie</option>
                            {sortedCategories.map((cat) => (
                              <option key={cat.id} value={cat.id}>{cat.name}</option>
                            ))}
                          </select>
                        </Field>
                        <Field label="Sous-niche">
                          <input
                            type="text"
                            value={metaFields.sub_niche}
                            onChange={(e) => handleSubNicheChange(e.target.value)}
                            className={INPUT}
                            placeholder="ex: nutrition sportive"
                          />
                        </Field>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <Field label="Durée de lecture">
                        <input
                          type="number"
                          min={1}
                          value={manualReadingTime ?? ''}
                          placeholder={`${calculatedReadingTime} min`}
                          onChange={(e) => handleReadingTimeChange(e.target.value)}
                          className={INPUT}
                        />
                      </Field>
                      <Field label="Nom de l'auteur">
                        <input
                          type="text"
                          value={manualAuthorName}
                          onChange={(e) => handleAuthorNameChange(e.target.value)}
                          placeholder={user?.name ?? "Nom d'auteur"}
                          className={INPUT}
                        />
                      </Field>
                    </div>
                  </div>

                  {/* Publication */}
                  <div className="p-3 flex flex-col gap-3">
                    <div className="flex items-center justify-between">
                      <span className="text-[12px] font-medium text-secondary">Statut</span>
                      <StatusBadge status={article.status} />
                    </div>

                    {article.status === ArticleStatus.SCHEDULED && articleSchedule.scheduled_for && (
                      <div className="flex flex-col gap-2 px-3 pb-3">
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => void handlePromote()}
                          loading={actionLoading === 'promote'}
                          disabled={busy}
                        >
                          Mettre à jour le contenu
                        </Button>
                        <p className="text-center text-[11px] text-tertiary">
                          La date de publication reste le {formatDate(articleSchedule.scheduled_for)}
                        </p>
                      </div>
                    )}

                    {article.status === ArticleStatus.PUBLISHED && (
                      <div className="flex flex-col gap-2 px-3 pb-3">
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => void handlePromote()}
                          loading={actionLoading === 'promote'}
                          disabled={busy}
                        >
                          Mettre à jour
                        </Button>
                        <div className="px-1 text-[11px] text-tertiary">
                          <p>Publié le {articleSchedule.published_at ? formatDate(articleSchedule.published_at) : '—'}</p>
                          {article.updated_at && articleSchedule.published_at && article.updated_at !== articleSchedule.published_at && (
                            <p>Dernière mise à jour : {formatDate(article.updated_at)}</p>
                          )}
                        </div>
                      </div>
                    )}

                    <div className="flex flex-col gap-2">
                      {/* Scheduled → Déprogrammer */}
                      {article.status === ArticleStatus.SCHEDULED && (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="w-full justify-center"
                          onClick={() => doAction('unschedule')}
                          disabled={busy}
                        >
                          {actionLoading === 'unschedule' ? <Loader2 size={13} className="animate-spin" /> : null}
                          Déprogrammer
                        </Button>
                      )}

                      {/* Published → Dépublier + promote si changements */}
                      {article.status === ArticleStatus.PUBLISHED && (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="w-full justify-center"
                          onClick={() => doAction('unpublish')}
                          disabled={busy}
                        >
                          {actionLoading === 'unpublish' ? <Loader2 size={13} className="animate-spin" /> : null}
                          Dépublier
                        </Button>
                      )}

                      {/* Default (draft, ready_to_publish, etc.) → Publier + Archiver */}
                      {article.status !== ArticleStatus.PUBLISHED && article.status !== ArticleStatus.ARCHIVED && article.status !== ArticleStatus.SCHEDULED && (
                        <>
                          <Popover>
                            <PopoverTrigger asChild>
                              <Button
                                size="sm"
                                variant="primary"
                                className="w-full justify-center"
                                disabled={busy}
                              >
                                {actionLoading === 'publish' ? (
                                  <Loader2 size={13} className="animate-spin" />
                                ) : null}
                                Publier
                              </Button>
                            </PopoverTrigger>
                            <PopoverContent align="start" sideOffset={6} className="min-w-0 w-[var(--radix-popover-trigger-width)] p-3">
                              <div className="flex flex-col gap-2">
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="w-full justify-center"
                                  onClick={() => doAction('publish')}
                                  disabled={busy}
                                >
                                  {actionLoading === 'publish' ? (
                                    <Loader2 size={13} className="animate-spin" />
                                  ) : null}
                                  Publier maintenant
                                </Button>

                                <div className="border-t border-border my-1" />

                                <div className="flex flex-col gap-2">
                                  <p className="text-[11px] font-medium text-secondary">Programmer</p>
                                  <input
                                    type="date"
                                    value={scheduleDate}
                                    onChange={(e) => setScheduleDate(e.target.value)}
                                    className="h-9 rounded-[8px] border border-border bg-transparent px-2.5 text-[13px] text-primary outline-none focus:border-accent"
                                  />
                                  <input
                                    type="time"
                                    value={scheduleTime}
                                    onChange={(e) => setScheduleTime(e.target.value)}
                                    className="h-9 rounded-[8px] border border-border bg-transparent px-2.5 text-[13px] text-primary outline-none focus:border-accent"
                                  />
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    className="w-full justify-center"
                                    onClick={handleSchedule}
                                    disabled={!scheduleDate || !scheduleTime || busy}
                                  >
                                    {actionLoading === 'schedule' ? (
                                      <Loader2 size={13} className="animate-spin" />
                                    ) : null}
                                    Programmer
                                  </Button>
                                </div>
                              </div>
                            </PopoverContent>
                          </Popover>

                          <Button
                            size="sm"
                            variant="ghost"
                            className="w-full justify-center"
                            onClick={() => doAction('archive')}
                            disabled={busy}
                          >
                            {actionLoading === 'archive' ? <Loader2 size={13} className="animate-spin" /> : null}
                            Archiver
                          </Button>
                        </>
                      )}

                      {/* Archived → Désarchiver uniquement */}
                      {article.status === ArticleStatus.ARCHIVED && (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="w-full justify-center"
                          onClick={() => doAction('unarchive')}
                          disabled={busy}
                        >
                          {actionLoading === 'unarchive' ? <Loader2 size={13} className="animate-spin" /> : null}
                          Désarchiver
                        </Button>
                      )}
                    </div>
                  </div>

                  {/* Commentaires éditoriaux */}
                  <div className="p-3">
                    <p className="text-[12px] font-medium text-secondary mb-2 flex items-center gap-1.5">
                      <MessageCircle size={12} className="text-tertiary" />
                      Commentaires éditoriaux
                    </p>
                    {selectedCommentId && (
                      <p className="mb-2 rounded-[7px] bg-accent/6 px-2 py-1 text-[10px] text-accent">
                        Commentaire selectionne dans le texte.
                      </p>
                    )}
                    <CommentsPanel
                      articleId={articleId!}
                      comments={comments}
                      loading={commentsLoading}
                      selectedCommentId={selectedCommentId}
                      onResolve={handleResolveInlineComment}
                      onDelete={handleDeleteInlineComment}
                      onSelect={(comment) => {
                        setSelectedCommentId(comment.id)
                        setSelectedCommentPopup(null)
                      }}
                    />
                  </div>

                  {/* Error */}
                  {actionError && (
                    <div className="mx-3 mb-2 flex items-start gap-1.5 rounded-[8px] bg-danger/5 border border-danger/20 px-2.5 py-2 text-[12px] text-danger">
                      <AlertCircle size={11} className="mt-0.5 shrink-0" />
                      <span>{actionError}</span>
                    </div>
                  )}
                </div>
              )}

              {/* ── Analyse tab ── */}
              {activeRightTab === 'analyse' && (
                <AnalysePanel
                  article={{ ...article, title: metaFields.title }}
                  projectId={projectId!}
                  onBeforeAnalyze={async () => { await handleSaveNow() }}
                  initialAnalysis={latestSeoAnalysis}
                  initialReadiness={latestReadyCheck}
                  onAnalysisUpdate={(analysis) => {
                    setLatestSeoAnalysis(analysis)
                    setArticle((prev) => prev ? {
                      ...prev,
                      latest_analysis: {
                        seo_score: analysis.seo_score,
                        readability_score: analysis.readability_score,
                        quality_score: analysis.quality_score,
                        eeat_score: analysis.eeat_score,
                        geo_score: prev.latest_analysis?.geo_score ?? null,
                        global_score: prev.latest_analysis?.global_score ?? null,
                        created_at: analysis.created_at,
                      },
                    } : prev)
                  }}
                  onReadinessUpdate={setLatestReadyCheck}
                />
              )}

              {/* ── Versions tab ── */}
              {activeRightTab === 'versions' && (
                <div className="p-3">
                  <VersionsPanel
                    projectId={projectId!}
                    articleId={articleId!}
                    members={members}
                    onRestore={(restored) => {
                      hydrateFromArticle(restored, { setContent: true })
                      setRightTab('publish')
                    }}
                  />
                </div>
              )}

            </div>
          </div>

        </div>
      )}

      {/* Inline comment popover (fixed overlay) */}
      {commentAnchor && viewMode === 'comment' && (
        <div
          ref={commentPopoverRef}
          style={{ top: commentAnchor.top, left: commentAnchor.left, boxShadow: '0 20px 60px rgba(0,0,0,0.14)' }}
          className="fixed z-50 w-[256px] rounded-[14px] border border-border bg-surface p-3 flex flex-col gap-2"
        >
          <p className="text-[10px] text-secondary leading-snug">
            Sur :{' '}
            <span className="italic text-primary">
              «{commentAnchor.text.slice(0, 80)}{commentAnchor.text.length > 80 ? '…' : ''}»
            </span>
          </p>
          <textarea
            autoFocus
            rows={3}
            value={commentInput}
            onChange={(e) => setCommentInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); handleSendInlineComment() }
            }}
            placeholder="Votre commentaire…"
            className="w-full rounded-[8px] border border-border bg-surface-soft px-2.5 py-1.5 text-[12px] text-primary placeholder:text-tertiary resize-none focus:outline-none focus:ring-1 focus:ring-accent/50 focus:border-accent/60 transition-colors"
          />
          <div className="flex gap-1.5">
            <button
              onClick={() => { setCommentAnchor(null); setCommentInput('') }}
              className="flex-1 rounded-[8px] border border-border py-1.5 text-[12px] text-secondary hover:bg-surface-muted transition-colors"
            >
              Annuler
            </button>
            <button
              onClick={handleSendInlineComment}
              disabled={!commentInput.trim() || sendingComment}
              className="flex-1 flex items-center justify-center gap-1 rounded-[8px] bg-accent py-1.5 text-[12px] font-medium text-white hover:bg-accent/90 disabled:opacity-40 transition-colors"
            >
              {sendingComment ? <Loader2 size={11} className="animate-spin" /> : <Send size={11} />}
              Commenter
            </button>
          </div>
        </div>
      )}

      {selectedComment && selectedCommentPopup && (
        <div
          style={{ top: selectedCommentPopup.top, left: selectedCommentPopup.left, boxShadow: '0 20px 60px rgba(0,0,0,0.14)' }}
          className="fixed z-50 w-[280px] rounded-[14px] border border-border bg-surface p-3"
        >
          {selectedComment.selected_text && (
            <p className="mb-2 rounded-[8px] bg-accent/6 px-2 py-1 text-[10px] leading-snug text-secondary">
              «{selectedComment.selected_text.slice(0, 110)}{selectedComment.selected_text.length > 110 ? '…' : ''}»
            </p>
          )}
          <p className="text-[12px] leading-snug text-primary">{selectedComment.text}</p>
          <div className="mt-3 flex gap-1.5">
            <button
              onClick={() => void handleResolveInlineComment(selectedComment.id, true)}
              className="flex flex-1 items-center justify-center gap-1 rounded-[8px] bg-success/10 py-1.5 text-[12px] font-medium text-success transition-colors hover:bg-success/15"
            >
              <Check size={11} />
              Valider
            </button>
            <button
              onClick={() => void handleDeleteInlineComment(selectedComment.id)}
              className="flex flex-1 items-center justify-center gap-1 rounded-[8px] border border-border py-1.5 text-[12px] font-medium text-danger transition-colors hover:bg-danger/5"
            >
              <Trash2 size={11} />
              Supprimer
            </button>
          </div>
        </div>
      )}

    </div>
  )
}
