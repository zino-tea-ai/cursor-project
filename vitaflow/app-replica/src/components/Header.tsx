import { Bell } from 'lucide-react'

export function Header() {
  return (
    <div 
      className="flex items-center justify-between py-2"
      style={{ height: '40px' }}
      data-testid="header"
    >
      {/* App 名称 */}
      <h1 className="text-2xl font-bold text-text-primary">Vitaflow</h1>
      
      {/* 通知图标 */}
      <button 
        className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-surface-secondary transition-colors"
        aria-label="通知"
      >
        <Bell size={24} className="text-text-primary" />
      </button>
    </div>
  )
}
