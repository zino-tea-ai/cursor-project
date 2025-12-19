/**
 * 被动技能树 Canvas 渲染组件
 */

import React, { useRef, useEffect, useCallback } from 'react';
import { useTreeStore } from '../../store/treeStore';
import { useBuildStore } from '../../store/buildStore';

// 节点颜色配置
const NODE_COLORS = {
  normal: {
    fill: '#1a1a2e',
    stroke: '#4a4a6a',
    allocated: '#af6025',
    allocatedStroke: '#ffcc00',
  },
  notable: {
    fill: '#2a2a4e',
    stroke: '#7a7aaa',
    allocated: '#af6025',
    allocatedStroke: '#ffcc00',
  },
  keystone: {
    fill: '#3a3a6e',
    stroke: '#9a9aca',
    allocated: '#af6025',
    allocatedStroke: '#ffcc00',
  },
  hovered: {
    stroke: '#ffffff',
  },
};

// 节点半径
const NODE_RADIUS = {
  normal: 40,
  notable: 60,
  keystone: 80,
};

interface PassiveTreeCanvasProps {
  width: number;
  height: number;
}

export function PassiveTreeCanvas({ width, height }: PassiveTreeCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const {
    treeData,
    nodePositions,
    allocatedNodes,
    hoveredNode,
    viewport,
    loading,
    error,
    loadTree,
    setViewport,
    setHoveredNode,
    toggleNode,
  } = useTreeStore();

  // 世界坐标转屏幕坐标
  const worldToScreen = useCallback((worldX: number, worldY: number) => {
    const screenX = (worldX - viewport.x) * viewport.scale + width / 2;
    const screenY = (worldY - viewport.y) * viewport.scale + height / 2;
    return { x: screenX, y: screenY };
  }, [viewport, width, height]);

  // 屏幕坐标转世界坐标
  const screenToWorld = useCallback((screenX: number, screenY: number) => {
    const worldX = (screenX - width / 2) / viewport.scale + viewport.x;
    const worldY = (screenY - height / 2) / viewport.scale + viewport.y;
    return { x: worldX, y: worldY };
  }, [viewport, width, height]);

  // 获取节点类型
  const getNodeType = (node: any): 'normal' | 'notable' | 'keystone' => {
    if (node.isKeystone) return 'keystone';
    if (node.isNotable) return 'notable';
    return 'normal';
  };

  // 渲染技能树
  const render = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !treeData) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // 清空画布
    ctx.fillStyle = '#0c0c0e';
    ctx.fillRect(0, 0, width, height);

    // 视口裁剪边界（只渲染可见区域的节点）
    const viewBounds = {
      minX: viewport.x - width / 2 / viewport.scale - 200,
      maxX: viewport.x + width / 2 / viewport.scale + 200,
      minY: viewport.y - height / 2 / viewport.scale - 200,
      maxY: viewport.y + height / 2 / viewport.scale + 200,
    };

    // 判断节点是否在视口内
    const isInView = (x: number, y: number) => {
      return x >= viewBounds.minX && x <= viewBounds.maxX && 
             y >= viewBounds.minY && y <= viewBounds.maxY;
    };

    // 第一遍：绘制连线
    ctx.lineWidth = Math.max(1, 2 * viewport.scale);
    for (const [, pos] of nodePositions) {
      if (!isInView(pos.x, pos.y)) continue;
      
      const node = pos.node;
      if (!node.connections) continue;

      const fromScreen = worldToScreen(pos.x, pos.y);

      for (const conn of node.connections) {
        const toPos = nodePositions.get(conn.id);
        if (!toPos) continue;

        const toScreen = worldToScreen(toPos.x, toPos.y);

        // 高亮已分配节点之间的连线
        const bothAllocated = allocatedNodes.has(pos.id) && allocatedNodes.has(conn.id);
        const oneAllocated = allocatedNodes.has(pos.id) || allocatedNodes.has(conn.id);
        
        if (bothAllocated) {
          ctx.strokeStyle = '#af6025';
          ctx.lineWidth = Math.max(2, 4 * viewport.scale);
        } else if (oneAllocated) {
          ctx.strokeStyle = '#5a5a7a';
          ctx.lineWidth = Math.max(1, 2 * viewport.scale);
        } else {
          ctx.strokeStyle = '#2a2a3a';
          ctx.lineWidth = Math.max(1, 1 * viewport.scale);
        }

        ctx.beginPath();
        ctx.moveTo(fromScreen.x, fromScreen.y);
        ctx.lineTo(toScreen.x, toScreen.y);
        ctx.stroke();
      }
    }

    // 第二遍：绘制节点
    for (const [nodeId, pos] of nodePositions) {
      if (!isInView(pos.x, pos.y)) continue;
      
      const node = pos.node;
      const screenPos = worldToScreen(pos.x, pos.y);
      const nodeType = getNodeType(node);
      const baseRadius = NODE_RADIUS[nodeType];
      const radius = baseRadius * viewport.scale;

      // 跳过太小的节点（性能优化）
      if (radius < 2) continue;

      const isAllocated = allocatedNodes.has(nodeId);
      const isHovered = hoveredNode === nodeId;
      const colors = NODE_COLORS[nodeType];

      // 绘制节点背景
      ctx.beginPath();
      ctx.arc(screenPos.x, screenPos.y, radius, 0, Math.PI * 2);
      
      if (isAllocated) {
        ctx.fillStyle = colors.allocated;
      } else if (nodeType === 'keystone') {
        ctx.fillStyle = '#2a2a5e';
      } else if (nodeType === 'notable') {
        ctx.fillStyle = '#1e1e3e';
      } else {
        ctx.fillStyle = '#1a1a2e';
      }
      ctx.fill();

      // 绘制边框
      ctx.lineWidth = isHovered ? 3 : (isAllocated ? 2 : 1);
      if (isHovered) {
        ctx.strokeStyle = '#ffffff';
      } else if (isAllocated) {
        ctx.strokeStyle = '#ffcc00';
      } else if (nodeType === 'keystone') {
        ctx.strokeStyle = '#8888cc';
      } else if (nodeType === 'notable') {
        ctx.strokeStyle = '#6666aa';
      } else {
        ctx.strokeStyle = '#4a4a6a';
      }
      ctx.stroke();
    }

    // 第三遍：只在高缩放时绘制文字（避免文字重叠）
    if (viewport.scale > 0.15) {
      ctx.fillStyle = '#ffffff';
      ctx.font = `${Math.max(10, 14 * viewport.scale)}px sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';

      for (const [, pos] of nodePositions) {
        if (!isInView(pos.x, pos.y)) continue;
        
        const node = pos.node;
        if (!node.name) continue;
        
        const nodeType = getNodeType(node);
        // 只显示 notable 和 keystone 的名称
        if (nodeType === 'normal' && viewport.scale < 0.3) continue;

        const screenPos = worldToScreen(pos.x, pos.y);
        const radius = NODE_RADIUS[nodeType] * viewport.scale;

        ctx.fillText(node.name, screenPos.x, screenPos.y + radius + 4);
      }
    }

    // 绘制提示信息
    ctx.fillStyle = 'rgba(0,0,0,0.7)';
    ctx.fillRect(8, 8, 160, 70);
    ctx.fillStyle = '#888888';
    ctx.font = '12px monospace';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.fillText(`节点: ${nodePositions.size}`, 14, 14);
    ctx.fillText(`已分配: ${allocatedNodes.size}`, 14, 30);
    ctx.fillText(`缩放: ${(viewport.scale * 100).toFixed(1)}%`, 14, 46);
    ctx.fillStyle = '#666666';
    ctx.fillText(`滚轮缩放, 拖动平移`, 14, 62);
  }, [treeData, nodePositions, allocatedNodes, hoveredNode, viewport, width, height, worldToScreen]);

  // 处理鼠标滚轮缩放
  const handleWheel = useCallback((e: WheelEvent) => {
    e.preventDefault();
    
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // 获取鼠标位置的世界坐标
    const worldPos = screenToWorld(mouseX, mouseY);

    // 计算新缩放
    const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
    const newScale = Math.max(0.01, Math.min(1, viewport.scale * zoomFactor));

    // 调整视口位置使鼠标位置保持不变
    const newX = worldPos.x - (mouseX - width / 2) / newScale;
    const newY = worldPos.y - (mouseY - height / 2) / newScale;

    setViewport({ x: newX, y: newY, scale: newScale });
  }, [viewport, width, height, screenToWorld, setViewport]);

  // 处理鼠标拖动
  const isDraggingRef = useRef(false);
  const lastMousePosRef = useRef({ x: 0, y: 0 });

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button === 0) { // 左键
      isDraggingRef.current = true;
      lastMousePosRef.current = { x: e.clientX, y: e.clientY };
    }
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // 拖动
    if (isDraggingRef.current) {
      const dx = e.clientX - lastMousePosRef.current.x;
      const dy = e.clientY - lastMousePosRef.current.y;
      lastMousePosRef.current = { x: e.clientX, y: e.clientY };

      setViewport({
        x: viewport.x - dx / viewport.scale,
        y: viewport.y - dy / viewport.scale,
      });
      return;
    }

    // 悬停检测
    const worldPos = screenToWorld(mouseX, mouseY);
    let foundNode: number | null = null;

    for (const [nodeId, pos] of nodePositions) {
      const dx = worldPos.x - pos.x;
      const dy = worldPos.y - pos.y;
      const nodeType = getNodeType(pos.node);
      const radius = NODE_RADIUS[nodeType];
      
      if (dx * dx + dy * dy <= radius * radius) {
        foundNode = nodeId;
        break;
      }
    }

    setHoveredNode(foundNode);
  }, [viewport, nodePositions, screenToWorld, setViewport, setHoveredNode]);

  const handleMouseUp = useCallback(() => {
    isDraggingRef.current = false;
  }, []);

  const handleMouseLeave = useCallback(() => {
    isDraggingRef.current = false;
    setHoveredNode(null);
  }, [setHoveredNode]);

  // 获取伤害计算函数
  const { calculateDamage } = useBuildStore();

  // 处理点击选择节点
  const handleClick = useCallback(() => {
    if (hoveredNode !== null) {
      toggleNode(hoveredNode);
      // 重新计算伤害（延迟执行让状态更新完成）
      setTimeout(() => {
        calculateDamage();
      }, 0);
    }
  }, [hoveredNode, toggleNode, calculateDamage]);

  // 加载数据
  useEffect(() => {
    if (!treeData && !loading) {
      loadTree();
    }
  }, [treeData, loading, loadTree]);

  // 渲染循环
  useEffect(() => {
    render();
  }, [render]);

  // 绑定滚轮事件
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    canvas.addEventListener('wheel', handleWheel, { passive: false });
    return () => canvas.removeEventListener('wheel', handleWheel);
  }, [handleWheel]);

  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-red-400">
        加载失败: {error}
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        加载技能树数据...
      </div>
    );
  }

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      className="cursor-grab active:cursor-grabbing"
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseLeave}
      onClick={handleClick}
    />
  );
}



































