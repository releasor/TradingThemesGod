/** A 股交易日 / 盘中状态（按 Asia/Shanghai；优先服务端交易日历，失败则周末兜底）。 */

export type MarketSession =
  | 'weekend_closed'
  | 'pre_open'
  | 'call_auction'
  | 'morning_open'
  | 'lunch_break'
  | 'afternoon_open'
  | 'after_close'

export interface MarketClockInfo {
  nowText: string
  dateText: string
  isTradingDay: boolean
  tradingDayLabel: string
  session: MarketSession
  sessionLabel: string
  /** 逻辑上的数据交易日（非开市日回退） */
  dataTradeDate: string
}

export interface MarketCalendarOverride {
  isTradingDay: boolean
  dataTradeDate: string
}

const SESSION_LABELS: Record<MarketSession, string> = {
  weekend_closed: '休市（周末）',
  pre_open: '未开盘',
  call_auction: '集合竞价',
  morning_open: '开盘中（上午）',
  lunch_break: '午间休市',
  afternoon_open: '开盘中（下午）',
  after_close: '已收盘',
}

let calendarOverride: MarketCalendarOverride | null = null

export function setMarketCalendarOverride(value: MarketCalendarOverride | null) {
  calendarOverride = value
}

export function getMarketCalendarOverride(): MarketCalendarOverride | null {
  return calendarOverride
}

function shanghaiParts(now: Date) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    weekday: 'short',
  }).formatToParts(now)

  const get = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((part) => part.type === type)?.value ?? ''

  const weekday = get('weekday')
  const year = get('year')
  const month = get('month')
  const day = get('day')
  const hour = Number(get('hour') === '24' ? '0' : get('hour'))
  const minute = Number(get('minute'))
  const second = Number(get('second'))

  return {
    weekday,
    year,
    month,
    day,
    hour,
    minute,
    second,
    dateText: `${year}-${month}-${day}`,
    nowText: `${year}-${month}-${day} ${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}:${String(second).padStart(2, '0')}`,
    minutesOfDay: hour * 60 + minute,
  }
}

function isWeekend(weekday: string): boolean {
  return weekday === 'Sat' || weekday === 'Sun'
}

function previousWeekdayDate(dateText: string, weekday: string): string {
  const [y, m, d] = dateText.split('-').map(Number)
  const utc = new Date(Date.UTC(y, m - 1, d))
  const back = weekday === 'Sun' ? 2 : weekday === 'Sat' ? 1 : 0
  utc.setUTCDate(utc.getUTCDate() - back)
  return utc.toISOString().slice(0, 10)
}

function sessionForMinutes(minutesOfDay: number): MarketSession {
  if (minutesOfDay < 9 * 60 + 15) return 'pre_open'
  if (minutesOfDay < 9 * 60 + 25) return 'call_auction'
  if (minutesOfDay < 9 * 60 + 30) return 'pre_open'
  if (minutesOfDay < 11 * 60 + 30) return 'morning_open'
  if (minutesOfDay < 13 * 60) return 'lunch_break'
  if (minutesOfDay < 15 * 60) return 'afternoon_open'
  return 'after_close'
}

export function resolveMarketClock(now: Date = new Date()): MarketClockInfo {
  const parts = shanghaiParts(now)
  const weekend = isWeekend(parts.weekday)

  const isTradingDay = calendarOverride
    ? calendarOverride.isTradingDay
    : !weekend
  const dataTradeDate = calendarOverride
    ? calendarOverride.dataTradeDate
    : weekend
      ? previousWeekdayDate(parts.dateText, parts.weekday)
      : parts.dateText

  const session = !isTradingDay
    ? 'weekend_closed'
    : sessionForMinutes(parts.minutesOfDay)

  return {
    nowText: parts.nowText,
    dateText: parts.dateText,
    isTradingDay,
    tradingDayLabel: isTradingDay ? '交易日' : '非交易日',
    session,
    sessionLabel: !isTradingDay
      ? weekend
        ? SESSION_LABELS.weekend_closed
        : '休市'
      : SESSION_LABELS[session],
    dataTradeDate,
  }
}
