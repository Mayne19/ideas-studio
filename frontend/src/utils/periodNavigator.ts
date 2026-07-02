export type PeriodMode = 'day' | 'week' | 'month' | 'quarter' | 'semester' | 'year' | 'custom'

export type PeriodRange = {
  mode: PeriodMode
  cursor: string
  startDate: string
  endDate: string
  label: string
  isCurrent: boolean
}

function toDateKey(date: Date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
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
    end = endOfDay(cursor)
    start = startOfDay(addDays(end, -89))
    label = `${formatLongDate(start)} - ${formatLongDate(end)}`
  } else if (mode === 'semester') {
    end = endOfDay(cursor)
    start = startOfDay(addDays(end, -179))
    label = `${formatLongDate(start)} - ${formatLongDate(end)}`
  } else if (mode === 'year') {
    start = startOfYear(cursor)
    end = endOfDay(new Date(start.getFullYear(), 11, 31))
    label = String(start.getFullYear())
  }

  return {
    mode,
    cursor: mode === 'quarter' || mode === 'semester' ? toDateKey(end) : toDateKey(start),
    startDate: toDateKey(start),
    endDate: toDateKey(end),
    label,
    isCurrent: today >= start && today <= end,
  }
}

export function shiftPeriod(range: PeriodRange, direction: -1 | 1) {
  const date = new Date(`${range.cursor}T12:00:00`)
  if (range.mode === 'custom') {
    const start = new Date(`${range.startDate}T12:00:00`)
    const end = new Date(`${range.endDate}T12:00:00`)
    const days = Math.max(1, Math.round((end.getTime() - start.getTime()) / 86400000) + 1)
    return customPeriod(addDays(start, days * direction), addDays(end, days * direction))
  }
  if (range.mode === 'day') return getPeriodRange('day', addDays(date, direction))
  if (range.mode === 'week') return getPeriodRange('week', addDays(date, direction * 7))
  if (range.mode === 'month') return getPeriodRange('month', addMonths(date, direction))
  if (range.mode === 'quarter') return getPeriodRange('quarter', addDays(date, direction * 90))
  if (range.mode === 'semester') return getPeriodRange('semester', addDays(date, direction * 180))
  return getPeriodRange('year', new Date(date.getFullYear() + direction, 0, 1))
}

export function currentPeriod(mode: PeriodMode) {
  return getPeriodRange(mode, new Date())
}

export function isFuturePeriod(range: PeriodRange) {
  return new Date(`${range.startDate}T00:00:00`).getTime() > startOfDay(new Date()).getTime()
}

export function customPeriod(startInput: Date | string, endInput: Date | string): PeriodRange {
  const start = startOfDay(typeof startInput === 'string' ? new Date(`${startInput}T12:00:00`) : startInput)
  const end = endOfDay(typeof endInput === 'string' ? new Date(`${endInput}T12:00:00`) : endInput)
  const safeEnd = end < start ? endOfDay(start) : end
  const today = startOfDay(new Date())
  return {
    mode: 'custom',
    cursor: toDateKey(start),
    startDate: toDateKey(start),
    endDate: toDateKey(safeEnd),
    label: `${formatLongDate(start)} - ${formatLongDate(safeEnd)}`,
    isCurrent: today >= start && today <= safeEnd,
  }
}
