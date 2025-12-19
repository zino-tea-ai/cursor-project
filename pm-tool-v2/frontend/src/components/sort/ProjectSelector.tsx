'use client'

import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown } from 'lucide-react'
import type { ProjectSelectorProps } from '@/types/sort'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

function getLogoUrl(projectName: string): string {
  const appName = projectName.includes('/') 
    ? projectName.split('/').pop() 
    : projectName
  return `${API_BASE}/api/logo/${appName}`
}

export function ProjectSelector({
  projects,
  selectedProject,
  onSelect,
}: ProjectSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // 点击外部关闭
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const selectedProjectData = projects.find(p => p.name === selectedProject)

  return (
    <div ref={dropdownRef} className="project-selector">
      {/* 触发按钮 */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="project-selector__trigger"
      >
        {selectedProjectData ? (
          <>
            <img
              src={getLogoUrl(selectedProjectData.name)}
              alt={selectedProjectData.display_name}
              className="project-selector__logo"
              onError={(e) => {
                const target = e.target as HTMLImageElement
                target.style.display = 'none'
              }}
            />
            <span className="project-selector__name">
              {selectedProjectData.display_name}
            </span>
            <span className="project-selector__count">
              ({selectedProjectData.screen_count})
            </span>
          </>
        ) : (
          <span className="project-selector__placeholder">
            选择项目...
          </span>
        )}
        <ChevronDown size={16} className="project-selector__icon" />
      </button>

      {/* 下拉列表 */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.15 }}
            className="project-selector__dropdown"
          >
            {projects.map((project) => (
              <button
                key={project.name}
                onClick={() => {
                  onSelect(project.name)
                  setIsOpen(false)
                }}
                className={`project-selector__option ${
                  selectedProject === project.name ? 'project-selector__option--selected' : ''
                }`}
              >
                <img
                  src={getLogoUrl(project.name)}
                  alt={project.display_name}
                  className="project-selector__option-logo"
                  onError={(e) => {
                    const target = e.target as HTMLImageElement
                    target.style.display = 'none'
                  }}
                />
                <span className="project-selector__option-name">
                  {project.display_name}
                </span>
                <span className="project-selector__option-count">
                  {project.screen_count}
                </span>
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      <style jsx>{`
        .project-selector {
          position: relative;
          min-width: 240px;
        }
        .project-selector__trigger {
          width: 100%;
          padding: 8px 12px;
          border-radius: 8px;
          background: var(--bg-secondary);
          color: var(--text-primary);
          border: 1px solid var(--border-default);
          font-size: 14px;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .project-selector__logo {
          width: 24px;
          height: 24px;
          border-radius: 5px;
          object-fit: cover;
        }
        .project-selector__name {
          flex: 1;
          text-align: left;
        }
        .project-selector__count {
          color: var(--text-secondary);
          font-size: 12px;
        }
        .project-selector__placeholder {
          flex: 1;
          text-align: left;
          color: var(--text-secondary);
        }
        .project-selector__icon {
          opacity: 0.5;
        }
        .project-selector__dropdown {
          position: absolute;
          top: 100%;
          left: 0;
          right: 0;
          margin-top: 4px;
          background: #1a1a1a;
          border: 1px solid var(--border-default);
          border-radius: 8px;
          box-shadow: 0 10px 40px rgba(0,0,0,0.5);
          max-height: 400px;
          overflow-y: auto;
          z-index: 100;
        }
        .project-selector__option {
          width: 100%;
          padding: 10px 12px;
          background: transparent;
          border: none;
          border-bottom: 1px solid rgba(255,255,255,0.04);
          color: #fff;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 13px;
          text-align: left;
        }
        .project-selector__option:hover {
          background: rgba(255,255,255,0.05);
        }
        .project-selector__option--selected {
          background: rgba(255,255,255,0.08);
        }
        .project-selector__option-logo {
          width: 28px;
          height: 28px;
          border-radius: 6px;
          object-fit: cover;
        }
        .project-selector__option-name {
          flex: 1;
        }
        .project-selector__option-count {
          color: #6b7280;
          font-size: 12px;
        }
      `}</style>
    </div>
  )
}
