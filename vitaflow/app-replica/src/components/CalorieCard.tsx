import { Dumbbell } from 'lucide-react'

interface CircularProgressProps {
  value: number
  max: number
  size?: number
  strokeWidth?: number
}

function CircularProgress({ value, max, size = 125, strokeWidth = 8 }: CircularProgressProps) {
  const radius = (size - strokeWidth) / 2
  const circumference = radius * 2 * Math.PI
  const progress = Math.min(value / max, 1)
  const strokeDashoffset = circumference - progress * circumference

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg className="progress-ring" width={size} height={size}>
        {/* 背景圆环 */}
        <circle
          stroke="#E5E7EB"
          fill="transparent"
          strokeWidth={strokeWidth}
          r={radius}
          cx={size / 2}
          cy={size / 2}
        />
        {/* 进度圆环 */}
        <circle
          className="progress-ring__circle"
          stroke="url(#gradient)"
          fill="transparent"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${circumference} ${circumference}`}
          strokeDashoffset={strokeDashoffset}
          r={radius}
          cx={size / 2}
          cy={size / 2}
        />
        {/* 渐变定义 */}
        <defs>
          <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#2DD4BF" />
            <stop offset="100%" stopColor="#5EEAD4" />
          </linearGradient>
        </defs>
      </svg>
      
      {/* 中心内容 */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <Dumbbell size={16} className="text-text-tertiary mb-0.5" />
        <span className="text-sm text-text-tertiary">Left</span>
      </div>
      
      {/* 进度点 */}
      <div 
        className="absolute w-1.5 h-1.5 bg-primary-light rounded-full"
        style={{
          top: '15%',
          right: '20%',
        }}
      />
    </div>
  )
}

export function CalorieCard() {
  const currentCalories = 2505
  const targetCalories = 3000

  return (
    <div 
      className="bg-surface rounded-2xl p-4 shadow-card"
      style={{ height: 'var(--calorie-card-height)' }}
      data-testid="calorie-card"
    >
      <div className="flex items-start justify-between">
        {/* 左侧 - 卡路里数值 */}
        <div className="flex flex-col">
          <span className="text-base text-text-secondary mb-12">Calories</span>
          <div className="flex items-baseline">
            <span className="text-4xl font-bold text-text-primary">
              {currentCalories.toLocaleString()}
            </span>
            <span className="text-xl text-text-secondary ml-1">kcal</span>
          </div>
        </div>
        
        {/* 右侧 - 进度环 */}
        <CircularProgress value={currentCalories} max={targetCalories} />
      </div>
    </div>
  )
}
