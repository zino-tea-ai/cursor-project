import { Cookie, Drumstick, Baby } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

interface MacroCardProps {
  label: string
  value: string
  progress: number
  color: string
  icon: LucideIcon
}

function MacroCard({ label, value, progress, color, icon: Icon }: MacroCardProps) {
  return (
    <div 
      className="bg-surface rounded-xl p-3 shadow-card flex flex-col justify-between"
      style={{ 
        width: 'var(--macro-card-width)', 
        height: 'var(--macro-card-height)' 
      }}
      data-testid={`macro-card-${label.toLowerCase()}`}
    >
      <div className="flex items-start justify-between">
        <div>
          <span className="text-xs text-text-tertiary block mb-0.5">{label}</span>
          <p className="text-lg font-semibold text-text-primary leading-tight">{value}</p>
        </div>
        <Icon size={16} className="text-text-tertiary" />
      </div>
      
      {/* 进度条 */}
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div 
          className="h-full rounded-full transition-all duration-500"
          style={{ 
            width: `${Math.min(progress, 100)}%`,
            backgroundColor: color 
          }}
        />
      </div>
    </div>
  )
}

export function MacroCards() {
  const macros = [
    { 
      label: 'Carbs', 
      value: '165g', 
      progress: 75, 
      color: '#FB923C', // orange
      icon: Baby // 奶瓶图标代替
    },
    { 
      label: 'Fat', 
      value: '98g', 
      progress: 90, 
      color: '#F472B6', // pink
      icon: Drumstick 
    },
    { 
      label: 'Protein', 
      value: '43g', 
      progress: 45, 
      color: '#38BDF8', // blue
      icon: Cookie 
    },
  ]

  return (
    <div 
      className="flex" 
      style={{ gap: 'var(--macro-card-gap)' }}
      data-testid="macro-cards"
    >
      {macros.map((macro) => (
        <MacroCard key={macro.label} {...macro} />
      ))}
    </div>
  )
}
