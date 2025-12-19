'use client'

import { motion } from 'framer-motion'
import { getThumbnailUrl } from '@/lib/api'
import type { DragPreviewProps } from '@/types/sort'

export function DragPreview({
  screenshot,
  projectName,
  zoom = 100,
}: DragPreviewProps) {
  const previewWidth = Math.round(120 * (zoom / 100))
  
  return (
    <motion.div
      className="drag-preview"
      initial={{ scale: 1, rotate: 0 }}
      animate={{ scale: 1.05, rotate: 2 }}
      transition={{ duration: 0.15, ease: 'easeOut' }}
      style={{ width: `${previewWidth}px` }}
    >
      <div className="drag-preview__image-wrapper">
        <img
          src={getThumbnailUrl(projectName, screenshot.filename, 'small')}
          alt={screenshot.filename}
          className="drag-preview__image"
        />
      </div>
      
      <div className="drag-preview__label">
        拖拽中...
      </div>

      <style jsx>{`
        .drag-preview {
          box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5), 0 0 0 2px rgba(255,255,255,0.8);
          border-radius: 8px;
          overflow: hidden;
          cursor: grabbing;
        }
        .drag-preview__image-wrapper {
          aspect-ratio: 9/16;
          overflow: hidden;
          background: var(--bg-secondary);
        }
        .drag-preview__image {
          width: 100%;
          height: 100%;
          object-fit: cover;
          pointer-events: none;
        }
        .drag-preview__label {
          position: absolute;
          bottom: 4px;
          left: 50%;
          transform: translateX(-50%);
          padding: 2px 8px;
          background: rgba(0,0,0,0.8);
          border-radius: 4px;
          font-size: 10px;
          color: #fff;
          font-weight: 500;
          white-space: nowrap;
        }
      `}</style>
    </motion.div>
  )
}
