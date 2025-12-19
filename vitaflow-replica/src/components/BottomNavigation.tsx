import { Home, TrendingUp, Dumbbell, User, ScanLine } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

interface NavItemProps {
  icon: LucideIcon
  label: string
  isActive?: boolean
  isCenter?: boolean
}

function NavItem({ icon: Icon, label, isActive, isCenter }: NavItemProps) {
  if (isCenter) {
    return (
      <button 
        className="relative -top-4 w-14 h-14 bg-text-primary rounded-2xl flex items-center justify-center shadow-lg"
        aria-label={label}
        data-testid="nav-scan"
      >
        <ScanLine size={24} className="text-white" />
      </button>
    )
  }

  return (
    <button 
      className="flex flex-col items-center gap-1 py-2 px-3"
      aria-label={label}
      data-testid={`nav-${label.toLowerCase()}`}
    >
      <Icon 
        size={24} 
        className={isActive ? 'text-text-primary' : 'text-text-tertiary'} 
      />
      <span 
        className={`text-xs ${isActive ? 'text-text-primary font-medium' : 'text-text-tertiary'}`}
      >
        {label}
      </span>
    </button>
  )
}

export function BottomNavigation() {
  return (
    <div 
      className="absolute bottom-0 left-0 right-0 bg-surface rounded-t-3xl shadow-nav"
      style={{ height: 'var(--bottom-nav-height)' }}
      data-testid="bottom-navigation"
    >
      <div className="flex items-center justify-around h-16 px-5">
        <NavItem icon={Home} label="Home" isActive />
        <NavItem icon={TrendingUp} label="Progress" />
        <NavItem icon={ScanLine} label="Scan" isCenter />
        <NavItem icon={Dumbbell} label="Exercise" />
        <NavItem icon={User} label="Profile" />
      </div>
      
      {/* Home Indicator */}
      <div className="flex justify-center pt-2">
        <div className="w-36 h-1 bg-text-primary rounded-full" />
      </div>
    </div>
  )
}
