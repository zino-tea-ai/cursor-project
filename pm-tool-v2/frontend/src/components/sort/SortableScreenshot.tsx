'use client'

import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { Check, Play, Flag } from 'lucide-react'
import { getThumbnailUrl } from '@/lib/api'
import type { SortableScreenshotProps } from '@/types/sort'

export function SortableScreenshot({
  screenshot,
  projectName,
  index,
  isSelected,
  isNewlyAdded = false,
  onCardClick,
  onboardingStart,
  onboardingEnd,
}: SortableScreenshotProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ 
    id: screenshot.filename,
    transition: {
      duration: 200,
      easing: 'cubic-bezier(0.25, 1, 0.5, 1)',
    },
  })

  const isInOnboarding =
    onboardingStart >= 0 &&
    onboardingEnd >= 0 &&
    index >= onboardingStart &&
    index <= onboardingEnd

  const isStart = index === onboardingStart
  const isEnd = index === onboardingEnd

  const style = {
    transform: CSS.Transform.toString(transform),
    transition: transition || 'transform 200ms cubic-bezier(0.25, 1, 0.5, 1)',
    opacity: isDragging ? 0.3 : 1,
    zIndex: isDragging ? 100 : 'auto',
  }

  const getBorderStyle = () => {
    if (isDragging) return '2px dashed rgba(255,255,255,0.4)'
    if (isNewlyAdded) return '3px solid #f59e0b'
    if (isSelected) return '3px solid #3b82f6'
    if (isInOnboarding) return '2px solid #22c55e'
    return '2px solid rgba(255,255,255,0.15)'
  }

  const getBoxShadow = () => {
    if (isNewlyAdded) return '0 0 20px rgba(245, 158, 11, 0.5)'
    if (isSelected) return '0 0 0 2px rgba(59, 130, 246, 0.5)'
    if (isDragging) return '0 20px 40px rgba(0, 0, 0, 0.4)'
    return undefined
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="sortable-screenshot"
      {...attributes}
    >
      <div
        onClick={onCardClick}
        className="sortable-screenshot__card"
        style={{
          border: getBorderStyle(),
          boxShadow: getBoxShadow(),
          animation: isNewlyAdded ? 'pulse 1s ease-in-out infinite' : undefined,
        }}
      >
        {/* Drag Handle */}
        <div
          {...listeners}
          className="sortable-screenshot__drag-handle"
          style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
        />

        <img
          src={getThumbnailUrl(projectName, screenshot.filename, 'small')}
          alt={screenshot.filename}
          className="sortable-screenshot__image"
          loading="lazy"
        />

        {/* 选中遮罩和勾选图标 */}
        {isSelected && (
          <div className="sortable-screenshot__selected-overlay">
            <div className="sortable-screenshot__check-icon">
              <Check size={24} style={{ color: '#3b82f6' }} />
            </div>
          </div>
        )}

        {/* 索引 */}
        <div className="sortable-screenshot__index">
          {String(index + 1).padStart(4, '0')}
        </div>

        {/* START/END 标记 */}
        {isStart && (
          <div className="sortable-screenshot__badge sortable-screenshot__badge--start">
            <Play size={8} /> START
          </div>
        )}
        {isEnd && (
          <div className="sortable-screenshot__badge sortable-screenshot__badge--end">
            <Flag size={8} /> END
          </div>
        )}

        {/* Onboarding 范围内标记 */}
        {isInOnboarding && !isStart && !isEnd && (
          <div className="sortable-screenshot__onboarding-dot" />
        )}

        {/* 新添加标记 */}
        {isNewlyAdded && (
          <div className="sortable-screenshot__new-badge">NEW</div>
        )}
      </div>

      <style jsx>{`
        .sortable-screenshot__card {
          position: relative;
          aspect-ratio: 9/16;
          overflow: hidden;
          background: var(--bg-secondary);
          cursor: pointer;
          border-radius: 6px;
          transition: border 150ms, box-shadow 150ms;
        }
        .sortable-screenshot__drag-handle {
          position: absolute;
          inset: 0;
        }
        .sortable-screenshot__image {
          width: 100%;
          height: 100%;
          object-fit: cover;
          pointer-events: none;
        }
        .sortable-screenshot__selected-overlay {
          position: absolute;
          inset: 0;
          background: rgba(59, 130, 246, 0.35);
          display: flex;
          align-items: center;
          justify-content: center;
          pointer-events: none;
        }
        .sortable-screenshot__check-icon {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          background: #fff;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        .sortable-screenshot__index {
          position: absolute;
          top: 4px;
          left: 4px;
          padding: 2px 6px;
          background: rgba(0, 0, 0, 0.7);
          border-radius: 4px;
          font-size: 10px;
          color: var(--text-secondary);
          font-family: var(--font-mono);
        }
        .sortable-screenshot__badge {
          position: absolute;
          bottom: 4px;
          left: 4px;
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 9px;
          color: #fff;
          font-weight: 600;
          display: flex;
          align-items: center;
          gap: 2px;
        }
        .sortable-screenshot__badge--start {
          background: #22c55e;
        }
        .sortable-screenshot__badge--end {
          background: #f59e0b;
        }
        .sortable-screenshot__onboarding-dot {
          position: absolute;
          bottom: 4px;
          left: 4px;
          width: 6px;
          height: 6px;
          background: #22c55e;
          border-radius: 50%;
        }
        .sortable-screenshot__new-badge {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          padding: 4px 8px;
          background: #f59e0b;
          border-radius: 4px;
          font-size: 10px;
          color: #fff;
          font-weight: 700;
          text-transform: uppercase;
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.7; }
        }
      `}</style>
    </div>
  )
}
