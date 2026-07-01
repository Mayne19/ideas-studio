"use client"

import {
  createContext,
  useContext,
  useState,
  useRef,
  useMemo,
  useEffect,
  useCallback,
} from 'react'
import type { ReactNode, KeyboardEvent } from 'react'
import { cn } from '@/utils/cn'
import { ChevronDown } from '@/components/ui/hugeIcons'

export type ComboboxItem = { value: string; label: string }

type ComboboxContextType = {
  open: boolean
  setOpen: (v: boolean) => void
  search: string
  setSearch: (v: string) => void
  activeIndex: number
  setActiveIndex: (v: number) => void
  value: string
  onValueChange: (v: string) => void
  items: ComboboxItem[]
  filtered: ComboboxItem[]
  selectedItem: ComboboxItem | undefined
}

const ComboboxCtx = createContext<ComboboxContextType | null>(null)

export function useCombobox() {
  const ctx = useContext(ComboboxCtx)
  if (!ctx) throw new Error('Combobox sub-components must be used inside a <Combobox>')
  return ctx
}

type ComboboxProps = {
  items: ComboboxItem[]
  value?: string
  onValueChange?: (value: string) => void
  children: ReactNode
}

export function Combobox({ items, value = '', onValueChange, children }: ComboboxProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)

  const filtered = useMemo(
    () => items.filter((item) => item.label.toLowerCase().includes(search.toLowerCase())),
    [items, search],
  )

  const selectedItem = items.find((item) => item.value === value)

  const handleValueChange = useCallback(
    (v: string) => {
      onValueChange?.(v)
      setSearch('')
      setOpen(false)
    },
    [onValueChange],
  )

  return (
    <ComboboxCtx.Provider
      value={{
        open, setOpen, search, setSearch,
        activeIndex, setActiveIndex,
        value, onValueChange: handleValueChange,
        items, filtered, selectedItem,
      }}
    >
      {children}
    </ComboboxCtx.Provider>
  )
}

// ─── Input ───────────────────────────────────────────────────────────────────

type ComboboxInputProps = {
  placeholder?: string
  className?: string
  disabled?: boolean
}

export function ComboboxInput({ placeholder, className, disabled }: ComboboxInputProps) {
  const { open, setOpen, search, setSearch, selectedItem, filtered, activeIndex, setActiveIndex, onValueChange } =
    useCombobox()
  const ref = useRef<HTMLInputElement>(null)

  const displayValue = open
    ? search
    : selectedItem
      ? selectedItem.label
      : ''

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      if (!open) { setOpen(true); setSearch(''); return }
      setActiveIndex(Math.min(activeIndex + 1, filtered.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIndex(Math.max(activeIndex - 1, 0))
    } else if ((e.key === 'Enter' || e.key === ' ') && open && filtered[activeIndex]) {
      e.preventDefault()
      onValueChange(filtered[activeIndex].value)
      ref.current?.blur()
    } else if (e.key === 'Escape') {
      setOpen(false)
      ref.current?.blur()
    }
  }

  return (
    <div className="relative">
      <input
        ref={ref}
        type="text"
        value={displayValue}
        onChange={(e) => {
          if (!open) setOpen(true)
          setSearch(e.target.value)
          setActiveIndex(0)
        }}
        onFocus={() => {
          if (!open) { setOpen(true); setSearch('') }
        }}
        onKeyDown={handleKeyDown}
        placeholder={!open && !selectedItem ? placeholder : undefined}
        disabled={disabled}
        className={cn(
          'h-10 w-full cursor-pointer appearance-none rounded-[10px] border-2 border-border bg-transparent px-3.5 pr-9 text-[15px] text-primary outline-none transition-all',
          'hover:border-border-strong',
          'focus:border-accent focus:ring-2 focus:ring-accent/10',
          disabled && 'cursor-not-allowed opacity-50',
          className,
        )}
        readOnly
      />
      <ChevronDown
        size={15}
        className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-tertiary"
      />
    </div>
  )
}

// ─── Content ─────────────────────────────────────────────────────────────────

type ComboboxContentProps = {
  children: ReactNode
  className?: string
}

export function ComboboxContent({ children, className }: ComboboxContentProps) {
  const { open, setOpen } = useCombobox()
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleMouseDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    if (open) {
      document.addEventListener('mousedown', handleMouseDown)
      return () => document.removeEventListener('mousedown', handleMouseDown)
    }
  }, [open, setOpen])

  if (!open) return null

  return (
    <div
      ref={ref}
      className={cn(
        'absolute z-50 mt-1 w-full min-w-[200px] overflow-hidden rounded-[12px] border-2 border-border bg-bg shadow-lg',
        className,
      )}
    >
      {children}
    </div>
  )
}

// ─── Empty ───────────────────────────────────────────────────────────────────

export function ComboboxEmpty({ children }: { children: ReactNode }) {
  return (
    <div className="px-3 py-6 text-center text-[13px] text-tertiary">
      {children}
    </div>
  )
}

// ─── List ────────────────────────────────────────────────────────────────────

type ComboboxListProps = {
  children: (item: ComboboxItem) => ReactNode
}

export function ComboboxList({ children }: ComboboxListProps) {
  const { filtered } = useCombobox()
  return (
    <div className="max-h-[220px] overflow-y-auto p-1">
      {filtered.map((item) => children(item))}
    </div>
  )
}

// ─── Item ────────────────────────────────────────────────────────────────────

type ComboboxItemProps = {
  value: string
  children: ReactNode
}

export function ComboboxItem({ value, children }: ComboboxItemProps) {
  const ctx = useCombobox()
  const isSelected = ctx.value === value
  const isActive = ctx.filtered[ctx.activeIndex]?.value === value
  const ref = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (isActive && ref.current) {
      ref.current.scrollIntoView({ block: 'nearest' })
    }
  }, [isActive])

  return (
    <button
      ref={ref}
      onMouseDown={(e) => {
        e.preventDefault()
        ctx.onValueChange(value)
      }}
      onMouseEnter={() => ctx.setActiveIndex(ctx.filtered.findIndex((item) => item.value === value))}
      className={cn(
        'flex w-full items-center rounded-[6px] px-2.5 py-1.5 text-[13px] text-left transition-colors',
        isActive && !isSelected && 'bg-surface-soft',
        isSelected
          ? 'bg-accent/8 text-primary font-medium'
          : 'text-secondary hover:bg-surface-soft hover:text-primary',
      )}
    >
      {children}
    </button>
  )
}
