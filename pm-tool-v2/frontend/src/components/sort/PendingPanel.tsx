'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  getPendingScreenshots,
  getPendingThumbnailUrl,
  importScreenshot,
  getApowersoftConfig,
  saveApowersoftConfig,
  type PendingScreenshot,
  type ApowersoftConfig,
} from '@/lib/api'
import {
  FolderOpen,
  Settings,
  RefreshCw,
  Check,
  ImageIcon,
} from 'lucide-react'
import { toast } from 'sonner'

interface PendingPanelProps {
  selectedProject: string | null
  onImportSuccess: () => void
}

export function PendingPanel({ selectedProject, onImportSuccess }: PendingPanelProps) {
  const [screenshots, setScreenshots] = useState<PendingScreenshot[]>([])
  const [loading, setLoading] = useState(false)
  const [config, setConfig] = useState<ApowersoftConfig | null>(null)
  const [showConfig, setShowConfig] = useState(false)
  const [configPath, setConfigPath] = useState('')
  const [saving, setSaving] = useState(false)
  const [importing, setImporting] = useState<string | null>(null)
  const [lastImported, setLastImported] = useState<string | null>(null)

  // 加载待处理截图
  const loadPending = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getPendingScreenshots()
      setScreenshots(data.screenshots)
    } catch (error) {
      console.error('Failed to load pending screenshots:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  // 加载配置
  const loadConfig = useCallback(async () => {
    try {
      const data = await getApowersoftConfig()
      setConfig(data)
      setConfigPath(data.path || '')
    } catch (error) {
      console.error('Failed to load config:', error)
    }
  }, [])

  // 初始化
  useEffect(() => {
    loadPending()
    loadConfig()
    
    // 每 10 秒刷新一次
    const interval = setInterval(loadPending, 10000)
    return () => clearInterval(interval)
  }, [loadPending, loadConfig])

  // 保存配置
  const handleSaveConfig = async () => {
    setSaving(true)
    try {
      await saveApowersoftConfig(configPath, config?.auto_import || false)
      await loadConfig()
      await loadPending()
      setShowConfig(false)
    } catch (error) {
      console.error('Failed to save config:', error)
      toast.error('保存配置失败: ' + (error as Error).message)
    } finally {
      setSaving(false)
    }
  }

  // 导入截图
  const handleImport = async (filename: string) => {
    if (!selectedProject) {
      toast.error('请先选择一个项目')
      return
    }

    setImporting(filename)
    try {
      const result = await importScreenshot(selectedProject, filename)
      if (result.success) {
        // 显示成功提示
        setLastImported(result.new_filename || filename)
        toast.success(`已导入 ${result.new_filename || filename}`)
        setTimeout(() => setLastImported(null), 3000)
        
        await loadPending()
        onImportSuccess()
      } else {
        toast.error('导入失败: ' + result.message)
      }
    } catch (error) {
      console.error('Failed to import:', error)
      toast.error('导入失败: ' + (error as Error).message)
    } finally {
      setImporting(null)
    }
  }

  // 处理拖拽
  const handleDragStart = (e: React.DragEvent, screenshot: PendingScreenshot) => {
    e.dataTransfer.setData('application/x-pending-screenshot', JSON.stringify({
      filename: screenshot.filename,
      type: 'pending',
    }))
    e.dataTransfer.effectAllowed = 'copy'
  }

  return (
    <div
      style={{
        background: 'var(--bg-card)',
        borderRadius: '8px',
        overflow: 'hidden',
      }}
    >
      {/* 标题栏 */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 16px',
          borderBottom: '1px solid var(--border-default)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ImageIcon size={16} style={{ color: 'var(--text-muted)' }} />
          <span style={{ fontWeight: 500, fontSize: '13px' }}>
            待处理 Pending
          </span>
          <span
            style={{
              padding: '2px 6px',
              background: 'var(--bg-secondary)',
              borderRadius: '10px',
              fontSize: '11px',
              color: 'var(--text-muted)',
            }}
          >
            {screenshots.length}
          </span>
        </div>

        <div style={{ display: 'flex', gap: '4px' }}>
          <button
            onClick={loadPending}
            disabled={loading}
            style={{
              padding: '4px',
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              borderRadius: '4px',
            }}
            title="刷新"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
          <button
            onClick={() => setShowConfig(!showConfig)}
            style={{
              padding: '4px',
              background: showConfig ? 'var(--bg-secondary)' : 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              borderRadius: '4px',
            }}
            title="配置"
          >
            <Settings size={14} />
          </button>
        </div>
      </div>

      {/* 配置面板 */}
      <AnimatePresence>
        {showConfig && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            style={{
              padding: '12px 16px',
              borderBottom: '1px solid var(--border-default)',
              background: 'var(--bg-secondary)',
            }}
          >
            <div style={{ marginBottom: '8px', fontSize: '12px', color: 'var(--text-muted)' }}>
              傲软投屏截图目录
            </div>
            {/* 改为上下布局，避免保存按钮被挤掉 */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <input
                type="text"
                value={configPath}
                onChange={(e) => setConfigPath(e.target.value)}
                placeholder="C:\Users\...\Pictures\Apowersoft"
                style={{
                  width: '100%',
                  padding: '8px 10px',
                  background: 'var(--bg-primary)',
                  border: '1px solid var(--border-default)',
                  borderRadius: '4px',
                  color: 'var(--text-primary)',
                  fontSize: '12px',
                  boxSizing: 'border-box',
                }}
              />
              <button
                onClick={handleSaveConfig}
                disabled={saving}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  background: 'var(--success)',
                  border: 'none',
                  borderRadius: '4px',
                  color: '#fff',
                  fontSize: '12px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '4px',
                }}
              >
                {saving ? <RefreshCw size={12} className="animate-spin" /> : <Check size={12} />}
                保存配置
              </button>
            </div>
            {config?.detected && (
              <div style={{ marginTop: '6px', fontSize: '11px', color: 'var(--success)' }}>
                ✓ 已自动检测到傲软目录
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* 截图列表 */}
      <div
        style={{
          padding: '12px',
          maxHeight: '300px',
          overflowY: 'auto',
        }}
      >
        {loading && screenshots.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '20px', color: 'var(--text-muted)', fontSize: '12px' }}>
            加载中...
          </div>
        ) : screenshots.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '20px', color: 'var(--text-muted)', fontSize: '12px' }}>
            <FolderOpen size={24} style={{ marginBottom: '8px', opacity: 0.5 }} />
            <div>暂无待处理截图</div>
            {!config?.path && (
              <div style={{ marginTop: '4px', fontSize: '11px' }}>
                请先配置傲软截图目录
              </div>
            )}
          </div>
        ) : (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: '10px',
            }}
          >
            {screenshots.slice(0, 12).map((screenshot) => (
              <div
                key={screenshot.filename}
                draggable={!!selectedProject}
                onDragStart={(e) => handleDragStart(e, screenshot)}
                style={{
                  aspectRatio: '9/16',
                  background: 'var(--bg-secondary)',
                  borderRadius: '4px',
                  overflow: 'hidden',
                  cursor: selectedProject ? 'grab' : 'not-allowed',
                  position: 'relative',
                  opacity: importing === screenshot.filename ? 0.5 : 1,
                  transition: 'transform 0.15s, box-shadow 0.15s',
                }}
                title={selectedProject ? `拖拽到右侧排序区域导入` : '请先选择项目'}
                onMouseEnter={(e) => {
                  if (selectedProject) {
                    e.currentTarget.style.transform = 'scale(1.05)'
                    e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)'
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'scale(1)'
                  e.currentTarget.style.boxShadow = 'none'
                }}
              >
                <img
                  src={getPendingThumbnailUrl(screenshot.filename)}
                  alt={screenshot.filename}
                  style={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                  }}
                  loading="lazy"
                  onError={(e) => {
                    const target = e.target as HTMLImageElement
                    target.style.display = 'none'
                    // 显示占位图标
                    const parent = target.parentElement
                    if (parent && !parent.querySelector('.img-placeholder')) {
                      const placeholder = document.createElement('div')
                      placeholder.className = 'img-placeholder'
                      placeholder.style.cssText = 'position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--text-muted);'
                      placeholder.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21,15 16,10 5,21"/></svg>'
                      parent.appendChild(placeholder)
                    }
                  }}
                />
                {importing === screenshot.filename && (
                  <div
                    style={{
                      position: 'absolute',
                      inset: 0,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: 'rgba(0,0,0,0.5)',
                    }}
                  >
                    <RefreshCw size={16} className="animate-spin" style={{ color: '#fff' }} />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {screenshots.length > 12 && (
          <div
            style={{
              textAlign: 'center',
              marginTop: '8px',
              fontSize: '11px',
              color: 'var(--text-muted)',
            }}
          >
            还有 {screenshots.length - 12} 张截图...
          </div>
        )}
      </div>

      {/* 底部提示 */}
      {screenshots.length > 0 && (
        <div
          style={{
            padding: '8px 12px',
            borderTop: '1px solid var(--border-default)',
            fontSize: '11px',
            color: lastImported ? 'var(--success)' : 'var(--text-muted)',
            textAlign: 'center',
            transition: 'color 0.2s',
          }}
        >
          {lastImported ? (
            <>✓ 已导入 {lastImported}</>
          ) : selectedProject ? (
            <>拖拽到右侧导入到项目</>
          ) : (
            <>请先选择项目</>
          )}
        </div>
      )}
    </div>
  )
}

export default PendingPanel
