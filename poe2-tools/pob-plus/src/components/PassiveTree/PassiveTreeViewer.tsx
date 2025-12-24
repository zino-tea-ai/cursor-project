/**
 * 被动技能树查看器
 * 包含 Canvas 和控制面板
 */

import { useState, useEffect, useRef } from 'react';
import { PassiveTreeCanvas } from './PassiveTreeCanvas';
import { useTreeStore } from '../../store/treeStore';

export function PassiveTreeViewer() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  
  const {
    hoveredNode,
    allocatedNodes,
    zoomIn,
    zoomOut,
    resetViewport,
    getNode,
  } = useTreeStore();

  // 监听容器大小变化
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const updateDimensions = () => {
      setDimensions({
        width: container.clientWidth,
        height: container.clientHeight,
      });
    };

    updateDimensions();

    const resizeObserver = new ResizeObserver(updateDimensions);
    resizeObserver.observe(container);

    return () => resizeObserver.disconnect();
  }, []);

  // 获取悬停节点信息
  const hoveredNodeData = hoveredNode ? getNode(hoveredNode) : null;

  return (
    <div className="flex flex-col h-full">
      {/* 工具栏 */}
      <div className="flex items-center justify-between px-4 py-2 bg-poe-panel border-b border-poe-border">
        <div className="flex items-center gap-4">
          <span className="text-poe-gold font-semibold">被动技能树</span>
          <span className="text-sm text-gray-400">
            已分配: {allocatedNodes.size} 点
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={zoomOut}
            className="btn-secondary px-3 py-1 text-sm"
            title="缩小"
          >
            −
          </button>
          <button
            onClick={resetViewport}
            className="btn-secondary px-3 py-1 text-sm"
            title="重置视图"
          >
            ⟲
          </button>
          <button
            onClick={zoomIn}
            className="btn-secondary px-3 py-1 text-sm"
            title="放大"
          >
            +
          </button>
        </div>
      </div>

      {/* Canvas 容器 */}
      <div ref={containerRef} className="flex-1 relative overflow-hidden bg-poe-bg">
        <PassiveTreeCanvas width={dimensions.width} height={dimensions.height} />

        {/* 节点提示 */}
        {hoveredNodeData && (
          <div className="absolute bottom-4 left-4 max-w-md p-4 bg-black/90 border border-poe-gold rounded-lg shadow-xl">
            <div className="font-bold text-lg text-poe-gold mb-2">
              {hoveredNodeData.name}
              {hoveredNodeData.isKeystone && <span className="ml-2 text-xs text-purple-400">[核心]</span>}
              {hoveredNodeData.isNotable && <span className="ml-2 text-xs text-blue-400">[显著]</span>}
            </div>
            {hoveredNodeData.stats && hoveredNodeData.stats.length > 0 && (
              <ul className="text-sm space-y-1">
                {hoveredNodeData.stats.map((stat, i) => (
                  <li key={i} className="text-green-400">{stat}</li>
                ))}
              </ul>
            )}
            <div className="text-xs text-gray-500 mt-3 pt-2 border-t border-gray-700">
              点击选择 / 取消选择
            </div>
          </div>
        )}
      </div>

      {/* 底部提示 */}
      <div className="px-4 py-2 bg-poe-panel border-t border-poe-border text-xs text-gray-500">
        滚轮缩放 | 拖动平移 | 点击选择节点
      </div>
    </div>
  );
}































































