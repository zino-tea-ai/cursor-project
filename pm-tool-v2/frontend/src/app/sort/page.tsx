'use client'

import { useEffect, useCallback, useRef, useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  type DropAnimation,
  defaultDropAnimationSideEffects,
} from '@dnd-kit/core'
import {
  SortableContext,
  sortableKeyboardCoordinates,
  rectSortingStrategy,
} from '@dnd-kit/sortable'
import { AppLayout } from '@/components/layout'
import {
  PreviewPanel,
  PendingPanel,
  StatusBar,
  ShortcutsHint,
  ProjectSelector,
  SortableScreenshot,
  DragPreview,
  ZoomControl,
  SelectionBar,
} from '@/components/sort'
import { useProjectStore } from '@/store/project-store'
import { useSortStore } from '@/store/sort'
import { importScreenshot, uploadScreenshot } from '@/lib/api'
import type { Screenshot } from '@/types'
import { ZOOM_CONFIG } from '@/types/sort'
import {
  ArrowUpDown,
  Save,
  Check,
  Trash2,
  RotateCcw,
  CheckSquare,
  X,
} from 'lucide-react'
import { toast } from 'sonner'

// ==================== 配置 ====================

const dropAnimation: DropAnimation = {
  sideEffects: defaultDropAnimationSideEffects({
    styles: { active: { opacity: '0.5' } },
  }),
  duration: 250,
  easing: 'cubic-bezier(0.25, 1, 0.5, 1)',
}

function getCardMinWidth(zoom: number): number {
  return Math.round(100 * (zoom / 100))
}

// ==================== 主页面 ====================

export default function SortPage() {
  // Store
  const { projects, fetchProjects } = useProjectStore()
  const {
    sortedScreenshots,
    deletedBatches,
    selectedFiles,
    onboardingRange,
    previewIndex,
    loading,
    saving,
    error,
    hasChanges,
    zoom,
    fetchData,
    reorder,
    toggleSelect,
    selectAll,
    deselectAll,
    setSelectedFiles,
    deleteSelected,
    restoreBatch,
    saveSortOrder,
    applySortOrder,
    setPreviewIndex,
    prevPreview,
    nextPreview,
    reset,
    zoomIn,
    zoomOut,
    resetZoom,
    setLastClickedIndex,
    lastClickedIndex,
  } = useSortStore()

  // Local State
  const [selectedProject, setSelectedProject] = useState<string | null>(null)
  const [activeId, setActiveId] = useState<string | null>(null)
  const [showDeleted, setShowDeleted] = useState(false)
  const [isDragOver, setIsDragOver] = useState(false)
  const [dropTargetIndex, setDropTargetIndex] = useState<number | null>(null)
  const [uploadMessage, setUploadMessage] = useState<string | null>(null)
  const [newlyAdded, setNewlyAdded] = useState<string | null>(null)
  
  // Refs
  const contentRef = useRef<HTMLDivElement>(null)
  const gridRef = useRef<HTMLDivElement>(null)

  // DnD Sensors
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  )

  // ==================== Effects ====================

  // 加载项目列表
  useEffect(() => {
    fetchProjects()
  }, [fetchProjects])

  // 离开页面提示
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasChanges) {
        e.preventDefault()
        e.returnValue = '你有未保存的排序更改，确定要离开吗？'
      }
    }
    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [hasChanges])

  // 切换项目时加载数据
  useEffect(() => {
    if (selectedProject) {
      fetchData(selectedProject)
    } else {
      reset()
    }
  }, [selectedProject, fetchData, reset])

  // 滚轮缩放
  useEffect(() => {
    if (!selectedProject) return
    
    const handleWheel = (e: WheelEvent) => {
      if (e.ctrlKey) {
        e.preventDefault()
        e.deltaY < 0 ? zoomIn() : zoomOut()
      }
    }
    
    const contentArea = contentRef.current
    if (contentArea) {
      contentArea.addEventListener('wheel', handleWheel, { passive: false })
      return () => contentArea.removeEventListener('wheel', handleWheel)
    }
  }, [selectedProject, zoomIn, zoomOut])

  // 全局快捷键
  useEffect(() => {
    if (!selectedProject) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'a') { e.preventDefault(); selectAll() }
      if (e.ctrlKey && (e.key === '=' || e.key === '+')) { e.preventDefault(); zoomIn() }
      if (e.ctrlKey && e.key === '-') { e.preventDefault(); zoomOut() }
      if (e.ctrlKey && e.key === '0') { e.preventDefault(); resetZoom() }
      if (e.key === 'Delete' && selectedFiles.size > 0) {
        const count = selectedFiles.size
        if (count <= 10 || window.confirm(`确定要删除 ${count} 张截图吗？`)) {
          deleteSelected(selectedProject)
        }
      }
      if (e.key === 'Escape') { deselectAll(); setPreviewIndex(null) }
      if (e.key === 'ArrowLeft' && previewIndex !== null) { prevPreview() }
      if (e.key === 'ArrowRight' && previewIndex !== null) { nextPreview() }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedProject, selectedFiles, previewIndex, selectAll, deselectAll, 
      deleteSelected, setPreviewIndex, prevPreview, nextPreview, zoomIn, zoomOut, resetZoom])

  // ==================== Handlers ====================

  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveId(event.active.id as string)
  }, [])

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event
    setActiveId(null)

    if (over && active.id !== over.id) {
      const oldIndex = sortedScreenshots.findIndex(s => s.filename === active.id)
      const newIndex = sortedScreenshots.findIndex(s => s.filename === over.id)
      reorder(oldIndex, newIndex)
    }
  }, [sortedScreenshots, reorder])

  const handleCardClick = useCallback((e: React.MouseEvent, index: number, filename: string) => {
    setPreviewIndex(index)
    
    if (e.shiftKey && lastClickedIndex !== null) {
      const start = Math.min(lastClickedIndex, index)
      const end = Math.max(lastClickedIndex, index)
      setSelectedFiles(new Set(sortedScreenshots.slice(start, end + 1).map(s => s.filename)))
    } else if (e.ctrlKey || e.metaKey) {
      toggleSelect(filename)
    } else {
      setSelectedFiles(new Set([filename]))
    }
    
    setLastClickedIndex(index)
  }, [lastClickedIndex, sortedScreenshots, setPreviewIndex, setSelectedFiles, toggleSelect, setLastClickedIndex])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!selectedProject) return
    
    const hasFiles = e.dataTransfer.types.includes('Files')
    const hasPending = e.dataTransfer.types.includes('application/x-pending-screenshot')
    
    if (hasFiles || hasPending) {
      setIsDragOver(true)
      e.dataTransfer.dropEffect = 'copy'
      
      if (gridRef.current) {
        const cards = gridRef.current.querySelectorAll('[data-screenshot-card]')
        let targetIndex = sortedScreenshots.length
        
        for (let i = 0; i < cards.length; i++) {
          const card = cards[i] as HTMLElement
          const rect = card.getBoundingClientRect()
          const cardCenterX = rect.left + rect.width / 2
          
          if (e.clientY < rect.bottom && e.clientY > rect.top - 20) {
            if (e.clientX < cardCenterX) { targetIndex = i; break }
            else if (i === cards.length - 1 || e.clientX < rect.right) { targetIndex = i + 1; break }
          }
        }
        setDropTargetIndex(targetIndex)
      }
    }
  }, [selectedProject, sortedScreenshots.length])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const relatedTarget = e.relatedTarget as HTMLElement
    if (!contentRef.current?.contains(relatedTarget)) {
      setIsDragOver(false)
      setDropTargetIndex(null)
    }
  }, [])

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    const targetIndex = dropTargetIndex ?? sortedScreenshots.length
    setIsDragOver(false)
    setDropTargetIndex(null)
    
    if (!selectedProject) { toast.error('请先选择一个项目'); return }

    // 处理待处理区拖来的截图
    const pendingData = e.dataTransfer.getData('application/x-pending-screenshot')
    if (pendingData) {
      try {
        const { filename } = JSON.parse(pendingData)
        const result = await importScreenshot(selectedProject, filename)
        if (result.success && result.new_filename) {
          const newScreenshot: Screenshot = { filename: result.new_filename, path: '' }
          const current = useSortStore.getState().sortedScreenshots
          useSortStore.setState({
            sortedScreenshots: [...current.slice(0, targetIndex), newScreenshot, ...current.slice(targetIndex)],
            hasChanges: true
          })
          setUploadMessage(`✓ 已插入 ${result.new_filename}`)
          setNewlyAdded(result.new_filename)
          setTimeout(() => { setUploadMessage(null); setNewlyAdded(null) }, 3000)
        }
      } catch (error) { toast.error('导入失败: ' + (error as Error).message) }
      return
    }

    // 处理外部文件
    const files = Array.from(e.dataTransfer.files).filter(f => 
      f.type.startsWith('image/') || /\.(png|jpg|jpeg|webp)$/i.test(f.name)
    )
    if (files.length === 0) { toast.error('请拖入图片文件'); return }

    const uploadedFiles: string[] = []
    for (const file of files) {
      try {
        const result = await uploadScreenshot(selectedProject, file)
        if (result.success && result.new_filename) uploadedFiles.push(result.new_filename)
      } catch (error) { console.error('Upload failed:', error) }
    }

    if (uploadedFiles.length > 0) {
      const newScreenshots: Screenshot[] = uploadedFiles.map(filename => ({ filename, path: '' }))
      const current = useSortStore.getState().sortedScreenshots
      useSortStore.setState({
        sortedScreenshots: [...current.slice(0, targetIndex), ...newScreenshots, ...current.slice(targetIndex)],
        hasChanges: true
      })
      setUploadMessage(`✓ 已导入 ${uploadedFiles.length} 张截图`)
      setNewlyAdded(uploadedFiles[uploadedFiles.length - 1])
      setTimeout(() => { setUploadMessage(null); setNewlyAdded(null) }, 3000)
    }
  }, [selectedProject, dropTargetIndex, sortedScreenshots.length])

  const handleImportSuccess = useCallback(() => {
    if (selectedProject) fetchData(selectedProject)
  }, [selectedProject, fetchData])

  const handleDeleteSelected = useCallback(() => {
    if (!selectedProject) return
    const count = selectedFiles.size
    if (count <= 10 || window.confirm(`确定要删除 ${count} 张截图吗？`)) {
      deleteSelected(selectedProject)
    }
  }, [selectedProject, selectedFiles.size, deleteSelected])

  // ==================== Derived State ====================

  const activeScreenshot = activeId ? sortedScreenshots.find(s => s.filename === activeId) : null
  const previewScreenshot = previewIndex !== null ? sortedScreenshots[previewIndex] : null
  const displayProjectName = selectedProject?.replace('downloads_2024/', '') || ''

  // ==================== Render ====================

  return (
    <AppLayout>
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* 左侧待处理区 */}
        <div className="pending-sidebar">
          <PendingPanel selectedProject={selectedProject} onImportSuccess={handleImportSuccess} />
        </div>

        {/* 主内容区 */}
        <div className="main-content">
          {/* 顶栏 */}
          <div className="topbar">
            <h1 className="topbar-title">截图排序</h1>
            <div style={{ flex: 1 }} />

            {/* 缩放控制 */}
            {selectedProject && sortedScreenshots.length > 0 && (
              <ZoomControl
                zoom={zoom}
                onZoomIn={zoomIn}
                onZoomOut={zoomOut}
                onReset={resetZoom}
              />
            )}

            {/* 项目选择器 */}
            <div style={{ marginLeft: 12 }}>
              <ProjectSelector
                projects={projects}
                selectedProject={selectedProject}
                onSelect={setSelectedProject}
              />
            </div>

            {/* 操作按钮 */}
            {selectedProject && sortedScreenshots.length > 0 && (
              <div className="topbar-actions">
                <button className="btn-ghost" onClick={() => selectedFiles.size > 0 ? deselectAll() : selectAll()}>
                  {selectedFiles.size > 0 ? <><X size={16} />取消 ({selectedFiles.size})</> : <><CheckSquare size={16} />全选</>}
                </button>

                {selectedFiles.size > 0 && (
                  <button className="btn-ghost" onClick={handleDeleteSelected} disabled={saving} style={{ color: 'var(--danger)' }}>
                    <Trash2 size={16} />删除 ({selectedFiles.size})
                  </button>
                )}

                {deletedBatches.length > 0 && (
                  <button className={`btn-ghost ${showDeleted ? 'active' : ''}`} onClick={() => setShowDeleted(!showDeleted)}>
                    <RotateCcw size={16} />已删除 ({deletedBatches.reduce((a, b) => a + b.count, 0)})
                  </button>
                )}

                {hasChanges && (
                  <>
                    <button className="btn-ghost" onClick={() => selectedProject && saveSortOrder(selectedProject)} disabled={saving}>
                      <Save size={16} />保存排序
                    </button>
                    <button 
                      className="btn-ghost" 
                      onClick={() => selectedProject && applySortOrder(selectedProject)} 
                      disabled={saving}
                      style={{ background: 'var(--success)', color: '#fff' }}
                    >
                      <Check size={16} />{saving ? '应用中...' : '应用并重命名'}
                    </button>
                  </>
                )}
              </div>
            )}
          </div>

          {/* 状态栏 */}
          {selectedProject && sortedScreenshots.length > 0 && (
            <StatusBar
              projectName={displayProjectName}
              total={sortedScreenshots.length}
              selected={selectedFiles.size}
              moved={hasChanges ? 1 : 0}
              onboardingStart={onboardingRange.start}
              onboardingEnd={onboardingRange.end}
            />
          )}

          {/* 内容区 */}
          <div 
            ref={contentRef}
            className="content-area" 
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            {/* 拖拽提示 */}
            {isDragOver && (
              <div className="drop-overlay">
                <div className="drop-message">
                  {dropTargetIndex !== null && dropTargetIndex < sortedScreenshots.length
                    ? `释放插入到位置 ${dropTargetIndex + 1}`
                    : '释放添加到末尾'}
                </div>
              </div>
            )}
            
            {/* 上传成功提示 */}
            {uploadMessage && <div className="upload-toast">{uploadMessage}</div>}

            {/* 空状态 */}
            {!selectedProject && (
              <div className="empty-state">
                <ArrowUpDown size={48} />
                <p>请选择一个项目来排序截图</p>
              </div>
            )}

            {/* 加载中 */}
            {selectedProject && loading && (
              <div className="loading-state"><div className="spinner" /></div>
            )}

            {/* 错误 */}
            {error && <div className="error-message">{error}</div>}

            {/* 已删除面板 */}
            <AnimatePresence>
              {showDeleted && deletedBatches.length > 0 && (
                <div className="deleted-panel">
                  <h3>已删除的截图</h3>
                  {deletedBatches.map((batch) => (
                    <div key={batch.timestamp} className="deleted-batch">
                      <span>{batch.count} 张截图 - {batch.timestamp}</span>
                      <button onClick={() => selectedProject && restoreBatch(selectedProject, batch.timestamp)} disabled={saving}>
                        <RotateCcw size={12} />恢复
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </AnimatePresence>

            {/* 排序网格 */}
            {selectedProject && !loading && sortedScreenshots.length > 0 && (
              <DndContext
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragStart={handleDragStart}
                onDragEnd={handleDragEnd}
              >
                <SortableContext items={sortedScreenshots.map(s => s.filename)} strategy={rectSortingStrategy}>
                  <div
                    ref={gridRef}
                    className="sort-grid"
                    style={{
                      gridTemplateColumns: `repeat(auto-fill, minmax(${getCardMinWidth(zoom)}px, 1fr))`,
                      gap: `${Math.round(10 * (zoom / 100))}px`,
                    }}
                  >
                    {sortedScreenshots.map((screenshot, index) => (
                      <div key={screenshot.filename} style={{ position: 'relative' }}>
                        {isDragOver && dropTargetIndex === index && <div className="drop-indicator" />}
                        <div data-screenshot-card>
                          <SortableScreenshot
                            screenshot={screenshot}
                            projectName={selectedProject}
                            index={index}
                            isSelected={selectedFiles.has(screenshot.filename)}
                            isNewlyAdded={screenshot.filename === newlyAdded}
                            onCardClick={(e) => handleCardClick(e, index, screenshot.filename)}
                            onboardingStart={onboardingRange.start}
                            onboardingEnd={onboardingRange.end}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </SortableContext>

                <DragOverlay dropAnimation={dropAnimation}>
                  {activeScreenshot && selectedProject && (
                    <DragPreview screenshot={activeScreenshot} projectName={selectedProject} zoom={zoom} />
                  )}
                </DragOverlay>
              </DndContext>
            )}

            {/* 空列表 */}
            {selectedProject && !loading && sortedScreenshots.length === 0 && (
              <div className="empty-state">该项目没有截图</div>
            )}
          </div>
        </div>

        {/* 右侧预览面板 */}
        {selectedProject && (
          <PreviewPanel
            screenshot={previewScreenshot}
            projectName={selectedProject}
            currentIndex={previewIndex !== null ? previewIndex : -1}
            total={sortedScreenshots.length}
            onClose={() => setPreviewIndex(null)}
            onPrev={prevPreview}
            onNext={nextPreview}
            onboardingStart={onboardingRange.start}
            onboardingEnd={onboardingRange.end}
          />
        )}
      </div>

      {/* 快捷键提示 */}
      {selectedProject && <ShortcutsHint />}

      {/* 底部选择操作栏 */}
      <AnimatePresence>
        {selectedFiles.size > 0 && selectedProject && (
          <SelectionBar
            selectedCount={selectedFiles.size}
            onDeselect={deselectAll}
            onDelete={handleDeleteSelected}
            disabled={saving}
          />
        )}
      </AnimatePresence>

      <style jsx>{`
        .pending-sidebar {
          width: 280px;
          flex-shrink: 0;
          border-right: 1px solid var(--border-default);
          overflow-y: auto;
          padding: 12px;
        }
        .main-content {
          flex: 1;
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }
        .topbar-actions {
          display: flex;
          gap: 8px;
          margin-left: 16px;
        }
        .content-area {
          flex: 1;
          overflow: auto;
          position: relative;
        }
        .drop-overlay {
          position: absolute;
          inset: 0;
          background: rgba(245, 158, 11, 0.05);
          border: 3px dashed #f59e0b;
          border-radius: 12px;
          z-index: 5;
          display: flex;
          align-items: flex-start;
          justify-content: center;
          padding-top: 20px;
          pointer-events: none;
        }
        .drop-message {
          background: rgba(0,0,0,0.9);
          padding: 12px 24px;
          border-radius: 8px;
          color: #f59e0b;
          font-size: 14px;
          font-weight: 500;
        }
        .upload-toast {
          position: fixed;
          bottom: 24px;
          left: 50%;
          transform: translateX(-50%);
          background: #22c55e;
          color: #fff;
          padding: 12px 24px;
          border-radius: 8px;
          font-size: 14px;
          font-weight: 500;
          z-index: 100;
          box-shadow: 0 4px 20px rgba(34, 197, 94, 0.4);
        }
        .empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 400px;
          color: var(--text-muted);
          gap: 16px;
        }
        .loading-state {
          display: flex;
          height: 256px;
          align-items: center;
          justify-content: center;
        }
        .error-message {
          padding: 12px 16px;
          background: rgba(239, 68, 68, 0.2);
          color: var(--danger);
          border-radius: 8px;
          margin-bottom: 16px;
        }
        .deleted-panel {
          background: var(--bg-card);
          border-radius: 8px;
          margin-bottom: 16px;
          padding: 16px;
        }
        .deleted-panel h3 {
          font-size: 14px;
          font-weight: 600;
          margin-bottom: 12px;
        }
        .deleted-batch {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 8px 12px;
          background: var(--bg-secondary);
          border-radius: 6px;
          margin-top: 8px;
          font-size: 13px;
        }
        .deleted-batch button {
          padding: 4px 8px;
          font-size: 12px;
          background: transparent;
          border: 1px solid var(--border-default);
          border-radius: 4px;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 4px;
          color: var(--text-primary);
        }
        .sort-grid {
          display: grid;
          position: relative;
          transition: gap 200ms ease;
        }
        .drop-indicator {
          position: absolute;
          left: -6px;
          top: 0;
          bottom: 0;
          width: 4px;
          background: #f59e0b;
          border-radius: 2px;
          z-index: 10;
          box-shadow: 0 0 10px rgba(245, 158, 11, 0.8);
        }
      `}</style>
    </AppLayout>
  )
}
