import type { PeriodRange } from '@/utils/periodNavigator'

const MONTH_LABELS = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
const WEEKDAY_LABELS = ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam']

export type PeriodBucket = {
  key: string
  label: string
}

export type PeriodBarLayout = {
  barSize: number
  chartWidth: string
  centered: boolean
}

function pad(value: number) {
  return String(value).padStart(2, '0')
}

function parseLocalDate(value: string) {
  const [datePart, timePart] = value.split('T')
  const [year, month, day] = datePart.split('-').map(Number)
  const hour = timePart ? Number(timePart.slice(0, 2)) : 12
  return new Date(year, month - 1, day, Number.isFinite(hour) ? hour : 12, 0, 0, 0)
}

function dateKey(date: Date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

function monthKey(date: Date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}`
}

function hourKey(date: Date) {
  return `${dateKey(date)}T${pad(date.getHours())}`
}

function startOfIsoWeek(date: Date) {
  const next = new Date(date)
  const day = next.getDay() || 7
  next.setDate(next.getDate() - day + 1)
  return next
}

function isoWeekParts(date: Date) {
  const utc = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()))
  const day = utc.getUTCDay() || 7
  utc.setUTCDate(utc.getUTCDate() + 4 - day)
  const yearStart = new Date(Date.UTC(utc.getUTCFullYear(), 0, 1))
  const week = Math.ceil((((utc.getTime() - yearStart.getTime()) / 86_400_000) + 1) / 7)
  return { year: utc.getUTCFullYear(), week }
}

function weekKey(date: Date) {
  const { year, week } = isoWeekParts(date)
  return `${year}-S${pad(week)}`
}

function weekLabel(date: Date) {
  const { week } = isoWeekParts(date)
  return `S${pad(week)}`
}

function addDays(date: Date, days: number) {
  const next = new Date(date)
  next.setDate(next.getDate() + days)
  return next
}

function addMonths(date: Date, months: number) {
  const next = new Date(date)
  next.setMonth(next.getMonth() + months)
  return next
}

function inclusiveDayCount(startDate: string, endDate: string) {
  const start = parseLocalDate(startDate)
  const end = parseLocalDate(endDate)
  return Math.max(1, Math.round((end.getTime() - start.getTime()) / 86_400_000) + 1)
}

export function getPeriodBuckets(period: PeriodRange): PeriodBucket[] {
  const start = parseLocalDate(period.startDate)

  if (period.mode === 'day') {
    return Array.from({ length: 24 }, (_, hour) => ({
      key: `${dateKey(start)}T${pad(hour)}`,
      label: `${pad(hour)}h`,
    }))
  }

  if (period.mode === 'week' || period.mode === 'month') {
    const length = period.mode === 'week' ? 7 : inclusiveDayCount(period.startDate, period.endDate)
    return Array.from({ length }, (_, index) => {
      const current = addDays(start, index)
      return {
        key: dateKey(current),
        label: period.mode === 'week' ? WEEKDAY_LABELS[current.getDay()] : String(current.getDate()),
      }
    })
  }

  if (period.mode === 'quarter' || period.mode === 'semester') {
    const end = parseLocalDate(period.endDate)
    const weeks: PeriodBucket[] = []
    let current = startOfIsoWeek(start)
    while (current <= end) {
      weeks.push({
        key: weekKey(current),
        label: weekLabel(current),
      })
      current = addDays(current, 7)
    }
    return weeks
  }

  const monthCount = 12
  return Array.from({ length: monthCount }, (_, index) => {
    const current = addMonths(start, index)
    return {
      key: monthKey(current),
      label: MONTH_LABELS[current.getMonth()],
    }
  })
}

export function getPeriodBucketKey(value: string, period: PeriodRange) {
  const hourMatch = value.match(/^(\d{2}):\d{2}$/)
  if (hourMatch) return `${period.startDate}T${hourMatch[1]}`
  if (/^\d{4}-S\d{2}$/.test(value)) return value
  if (/^\d{4}-\d{2}$/.test(value)) return value

  const date = parseLocalDate(value)
  if (Number.isNaN(date.getTime())) return null
  if (period.mode === 'day') return hourKey(date)
  if (period.mode === 'week' || period.mode === 'month') return dateKey(date)
  if (period.mode === 'quarter' || period.mode === 'semester') return weekKey(date)
  return monthKey(date)
}

export function getPeriodBarLayout(count: number): PeriodBarLayout {
  if (count <= 3) return { barSize: 28, chartWidth: '220px', centered: true }
  if (count <= 6) return { barSize: 28, chartWidth: '360px', centered: true }
  if (count <= 12) return { barSize: 24, chartWidth: '100%', centered: false }
  if (count <= 24) return { barSize: 14, chartWidth: '100%', centered: false }
  return { barSize: 8, chartWidth: '100%', centered: false }
}
