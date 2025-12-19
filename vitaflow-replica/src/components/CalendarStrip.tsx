interface DayProps {
  dayName: string
  date: number
  isSelected?: boolean
  isToday?: boolean
  hasProgress?: boolean
}

function DayItem({ dayName, date, isSelected, isToday, hasProgress }: DayProps) {
  return (
    <div className="flex flex-col items-center gap-1.5 w-12" data-testid="calendar-day">
      <span className={`text-sm ${isSelected ? 'text-text-primary font-medium' : 'text-text-tertiary'}`}>
        {dayName}
      </span>
      <div className="relative">
        {/* 进度环 - 粉色 */}
        {hasProgress && (
          <div 
            className="absolute inset-0 rounded-full border-2 border-accent-pink"
            style={{ width: '36px', height: '36px' }}
          />
        )}
        {/* 日期圆圈 */}
        <div 
          className={`
            w-9 h-9 rounded-full flex items-center justify-center text-base font-medium
            ${isSelected 
              ? 'bg-text-primary text-white' 
              : isToday 
                ? 'bg-primary text-white'
                : 'text-text-primary'
            }
          `}
        >
          {date}
        </div>
      </div>
    </div>
  )
}

export function CalendarStrip() {
  const days = [
    { dayName: 'Thu', date: 27, hasProgress: true },
    { dayName: 'Fri', date: 28 },
    { dayName: 'Sat', date: 29 },
    { dayName: 'Sun', date: 30, isToday: true },
    { dayName: 'Mon', date: 31, isSelected: true },
    { dayName: 'Tue', date: 1 },
    { dayName: 'Wed', date: 2 },
  ]

  return (
    <div 
      className="flex items-center justify-between mt-4"
      style={{ height: '64px' }}
      data-testid="calendar-strip"
    >
      {days.map((day, index) => (
        <DayItem key={index} {...day} />
      ))}
    </div>
  )
}
