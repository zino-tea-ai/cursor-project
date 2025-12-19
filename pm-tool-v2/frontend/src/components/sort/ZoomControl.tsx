'use client'

import { ZoomIn, ZoomOut } from 'lucide-react'
import { ZOOM_CONFIG } from '@/types/sort'
import type { ZoomControlProps } from '@/types/sort'

export function ZoomControl({
  zoom,
  onZoomIn,
  onZoomOut,
  onReset,
  min = ZOOM_CONFIG.min,
  max = ZOOM_CONFIG.max,
}: ZoomControlProps) {
  const isAtMin = zoom <= min
  const isAtMax = zoom >= max
  const isDefault = zoom === ZOOM_CONFIG.default

  return (
    <div className="zoom-control">
      <button
        onClick={onZoomOut}
        disabled={isAtMin}
        className={`zoom-control__btn ${isAtMin ? 'zoom-control__btn--disabled' : ''}`}
        title="缩小 (Ctrl+-)"
      >
        <ZoomOut size={16} />
      </button>
      
      <button
        onClick={onReset}
        className={`zoom-control__value ${!isDefault ? 'zoom-control__value--changed' : ''}`}
        title="重置缩放 (Ctrl+0)"
      >
        {zoom}%
      </button>
      
      <button
        onClick={onZoomIn}
        disabled={isAtMax}
        className={`zoom-control__btn ${isAtMax ? 'zoom-control__btn--disabled' : ''}`}
        title="放大 (Ctrl++)"
      >
        <ZoomIn size={16} />
      </button>

      <style jsx>{`
        .zoom-control {
          display: flex;
          align-items: center;
          gap: 4px;
          padding: 4px 8px;
          background: var(--bg-secondary);
          border-radius: 8px;
        }
        .zoom-control__btn {
          padding: 4px;
          background: transparent;
          border: none;
          border-radius: 4px;
          color: var(--text-secondary);
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: color 150ms, background 150ms;
        }
        .zoom-control__btn:hover:not(.zoom-control__btn--disabled) {
          background: rgba(255,255,255,0.1);
          color: var(--text-primary);
        }
        .zoom-control__btn--disabled {
          color: var(--text-muted);
          cursor: not-allowed;
        }
        .zoom-control__value {
          padding: 2px 8px;
          background: transparent;
          border: none;
          border-radius: 4px;
          color: var(--text-primary);
          cursor: pointer;
          font-size: 12px;
          font-family: var(--font-mono);
          font-weight: 500;
          min-width: 48px;
          transition: background 150ms;
        }
        .zoom-control__value:hover {
          background: rgba(255,255,255,0.1);
        }
        .zoom-control__value--changed {
          background: rgba(59, 130, 246, 0.2);
        }
      `}</style>
    </div>
  )
}
