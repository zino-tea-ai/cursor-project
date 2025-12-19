'use client'

import { motion } from 'framer-motion'
import { CheckSquare, X, Trash2 } from 'lucide-react'
import type { SelectionBarProps } from '@/types/sort'

export function SelectionBar({
  selectedCount,
  onDeselect,
  onDelete,
  disabled = false,
}: SelectionBarProps) {
  if (selectedCount === 0) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 50 }}
      transition={{ duration: 0.2, ease: [0.25, 1, 0.5, 1] }}
      className="selection-bar"
    >
      <span className="selection-bar__info">
        <CheckSquare size={18} className="selection-bar__icon" />
        已选择 {selectedCount} 张截图
      </span>
      
      <div className="selection-bar__divider" />
      
      <button
        onClick={onDeselect}
        className="selection-bar__btn selection-bar__btn--secondary"
      >
        <X size={14} />
        取消选择
      </button>
      
      <button
        onClick={onDelete}
        disabled={disabled}
        className="selection-bar__btn selection-bar__btn--danger"
      >
        <Trash2 size={14} />
        删除选中
      </button>

      <style jsx>{`
        .selection-bar {
          position: fixed;
          bottom: 24px;
          left: 50%;
          transform: translateX(-50%);
          background: rgba(30, 30, 30, 0.95);
          backdrop-filter: blur(12px);
          border-radius: 12px;
          padding: 12px 20px;
          display: flex;
          align-items: center;
          gap: 16px;
          box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255,255,255,0.1);
          z-index: 1000;
        }
        .selection-bar__info {
          color: #fff;
          font-size: 14px;
          font-weight: 500;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .selection-bar__icon {
          color: #3b82f6;
        }
        .selection-bar__divider {
          width: 1px;
          height: 24px;
          background: rgba(255,255,255,0.2);
        }
        .selection-bar__btn {
          padding: 8px 16px;
          border: none;
          border-radius: 8px;
          font-size: 13px;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 6px;
          transition: background 150ms, opacity 150ms;
        }
        .selection-bar__btn--secondary {
          background: rgba(255,255,255,0.1);
          color: #fff;
        }
        .selection-bar__btn--secondary:hover {
          background: rgba(255,255,255,0.15);
        }
        .selection-bar__btn--danger {
          background: #ef4444;
          color: #fff;
        }
        .selection-bar__btn--danger:hover:not(:disabled) {
          background: #dc2626;
        }
        .selection-bar__btn--danger:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
      `}</style>
    </motion.div>
  )
}
