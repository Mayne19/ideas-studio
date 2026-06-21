export type PeriodMode = 'day' | 'week' | 'month' | 'quarter' | 'year'

export type PeriodRange = {
  mode: PeriodMode
  cursor: string
  startDate: string
  endDate: string
  label: string
  isCurrent: boolean
}

function toDateKey(date: Date) {
  return date.toISOString().slice(0, 10)
}

function startOfDay(date: Date) {
  const next = new Date(date)
  next.setHours(0, 0, 0, 0)
  return next
}

function endOfDay(date: Date) {
  const next = new Date(date)
  next.setHours(23, 59, 59, 999)
  return next
}

function addDays(date: Date, amount: number) {
  const next = new Date(date)
  next.setDate(next.getDate() + amount)
  return next
}

function addMonths(date: Date, amount: number) {
  const next = new Date(date)
  next.setMonth(next.getMonth() + amount)
  return next
}

function startOfWeek(date: Date) {
  const next = startOfDay(date)
  const day = next.getDay() || 7
  next.setDate(next.getDate() - day + 1)
  return next
}

function startOfMonth(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), 1)
}

function startOfQuarter(date: Date) {
  return new Date(date.getFullYear(), Math.floor(date.getMonth() / 3) * 3, 1)
}

function startOfYear(date: Date) {
  return new Date(date.getFullYear(), 0, 1)
}

function formatLongDate(date: Date) {
  return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })
}

function formatMonth(date: Date) {
  return date.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' })
}

export function getPeriodRange(mode: PeriodMode, cursor: Date = new Date()): PeriodRange {
  const today = startOfDay(new Date())
  let start = startOfDay(cursor)
  let end = endOfDay(cursor)
  let label = formatLongDate(cursor)

  if (mode === 'week') {
    start = startOfWeek(cursor)
    end = endOfDay(addDays(start, 6))
    label = `${formatLongDate(start)} - ${formatLongDate(end)}`
  } else if (mode === 'month') {
    start = startOfMonth(cursor)
    end = endOfDay(addDays(addMonths(start, 1), -1))
    label = formatMonth(start)
  } else if (mode === 'quarter') {
    start = startOfQuarter(cursor)
    end = endOfDay(addDays(addMonths(start, 3), -1))
    label = `T${Math.floor(start.getMonth() / 3) + 1} ${start.getFullYear()}`
  } else if (mode === 'year') {
    start = startOfYear(cursor)
    end = endOfDay(new Date(start.getFullYear(), 11, 31))
    label = String(start.getFullYear())
  }

  return {
    mode,
    cursor: toDateKey(start),
    startDate: toDateKey(start),
    endDate: toDateKey(end),
    label,
    isCurrent: today >= start && today <= end,
  }
}

export function shiftPeriod(range: PeriodRange, direction: -1 | 1) {
  const date = new Date(`${range.cursor}T12:00:00`)
  if (range.mode === 'day') return getPeriodRange('day', addDays(date, direction))
  if (range.mode === 'week') return getPeriodRange('week', addDays(date, direction * 7))
  if (range.mode === 'month') return getPeriodRange('month', addMonths(date, direction))
  if (range.mode === 'quarter') return getPeriodRange('quarter', addMonths(date, direction * 3))
  return getPeriodRange('year', new Date(date.getFullYear() + direction, 0, 1))
}

export function currentPeriod(mode: PeriodMode) {
  return getPeriodRange(mode, new Date())
}

export function isFuturePeriod(range: PeriodRange) {
  return new Date(`${range.startDate}T00:00:00`).getTime() > startOfDay(new Date()).getTime()
}
