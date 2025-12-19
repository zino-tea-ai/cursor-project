/**
 * 被动技能树状态管理
 */

import { create } from 'zustand';
import type { TreeData, TreeNode, Viewport, NodePosition } from '../types/tree';
import type { Modifier } from '../types';

interface TreeState {
  // 数据
  treeData: TreeData | null;
  nodePositions: Map<number, NodePosition>;
  loading: boolean;
  error: string | null;

  // 选择状态
  allocatedNodes: Set<number>;
  hoveredNode: number | null;
  selectedClass: number; // 职业索引

  // 视口
  viewport: Viewport;

  // Actions
  loadTree: () => Promise<void>;
  allocateNode: (nodeId: number) => void;
  deallocateNode: (nodeId: number) => void;
  toggleNode: (nodeId: number) => void;
  setHoveredNode: (nodeId: number | null) => void;
  setSelectedClass: (classIndex: number) => void;
  
  // 视口控制
  setViewport: (viewport: Partial<Viewport>) => void;
  zoomIn: () => void;
  zoomOut: () => void;
  resetViewport: () => void;

  // 工具方法
  getNode: (nodeId: number) => TreeNode | null;
  getNodePosition: (nodeId: number) => NodePosition | null;
  getAllocatedModifiers: () => Modifier[];
  getTotalAllocatedPoints: () => number;
}

// 轨道角度计算
const orbitAngles: Record<number, number[]> = {
  0: [0],
  1: [0, 30, 45, 60, 90, 120, 135, 150, 180, 210, 225, 240, 270, 300, 315, 330],
  2: [0, 10, 20, 30, 40, 45, 50, 60, 70, 80, 90, 100, 110, 120, 130, 135, 140, 150, 160, 170, 180, 190, 200, 210, 220, 225, 230, 240, 250, 260, 270, 280, 290, 300, 310, 315, 320, 330, 340, 350],
  3: [0, 10, 20, 30, 40, 45, 50, 60, 70, 80, 90, 100, 110, 120, 130, 135, 140, 150, 160, 170, 180, 190, 200, 210, 220, 225, 230, 240, 250, 260, 270, 280, 290, 300, 310, 315, 320, 330, 340, 350],
  4: [0, 10, 20, 30, 40, 45, 50, 60, 70, 80, 90, 100, 110, 120, 130, 135, 140, 150, 160, 170, 180, 190, 200, 210, 220, 225, 230, 240, 250, 260, 270, 280, 290, 300, 310, 315, 320, 330, 340, 350],
};

// 默认轨道半径
const defaultOrbitRadii = [0, 82, 162, 335, 493];

// 计算节点位置
function calculateNodePositions(treeData: TreeData): Map<number, NodePosition> {
  const positions = new Map<number, NodePosition>();
  const orbitRadii = treeData.constants?.orbitRadii || defaultOrbitRadii;

  for (const [nodeIdStr, node] of Object.entries(treeData.nodes)) {
    const nodeId = parseInt(nodeIdStr);
    const group = treeData.groups[node.group];
    
    if (!group) continue;

    // 计算节点在组内的位置
    const orbit = node.orbit || 0;
    const orbitIndex = node.orbitIndex || 0;
    const radius = orbitRadii[orbit] || 0;

    // 获取角度
    const angles = orbitAngles[orbit] || orbitAngles[0];
    const angleIndex = orbitIndex % angles.length;
    const angle = (angles[angleIndex] || 0) * Math.PI / 180;

    // 计算最终位置
    const x = group.x + radius * Math.sin(angle);
    const y = group.y - radius * Math.cos(angle);

    positions.set(nodeId, {
      id: nodeId,
      x,
      y,
      node,
    });
  }

  return positions;
}

// 解析 stat 字符串为 Modifier
function parseStatToModifier(stat: string): Modifier | null {
  // 匹配模式: "X% increased/reduced Y" 或 "+X to Y"
  const incMatch = stat.match(/(\d+)%?\s+(increased|reduced)\s+(.+)/i);
  if (incMatch) {
    const value = parseInt(incMatch[1]) * (incMatch[2].toLowerCase() === 'reduced' ? -1 : 1);
    const name = incMatch[3].replace(/\s+/g, '');
    return { name, type: 'INC', value, source: 'passive' };
  }

  const moreMatch = stat.match(/(\d+)%?\s+(more|less)\s+(.+)/i);
  if (moreMatch) {
    const value = parseInt(moreMatch[1]) * (moreMatch[2].toLowerCase() === 'less' ? -1 : 1);
    const name = moreMatch[3].replace(/\s+/g, '');
    return { name, type: 'MORE', value, source: 'passive' };
  }

  const addMatch = stat.match(/\+(\d+)\s+to\s+(.+)/i);
  if (addMatch) {
    const value = parseInt(addMatch[1]);
    const name = addMatch[2].replace(/\s+/g, '');
    return { name, type: 'BASE', value, source: 'passive' };
  }

  return null;
}

export const useTreeStore = create<TreeState>((set, get) => ({
  // 初始状态
  treeData: null,
  nodePositions: new Map(),
  loading: false,
  error: null,
  allocatedNodes: new Set(),
  hoveredNode: null,
  selectedClass: 0,
  viewport: {
    x: 0,
    y: 0,
    scale: 0.05, // 初始缩放比例（树很大，需要缩小）
  },

  // 加载技能树数据
  loadTree: async () => {
    set({ loading: true, error: null });
    try {
      const response = await fetch('/data/tree.json');
      if (!response.ok) {
        throw new Error('Failed to load tree data');
      }
      const treeData: TreeData = await response.json();
      const nodePositions = calculateNodePositions(treeData);
      
      set({ 
        treeData, 
        nodePositions,
        loading: false,
        // 设置初始视口到树中心
        viewport: {
          x: (treeData.min_x + treeData.max_x) / 2,
          y: (treeData.min_y + treeData.max_y) / 2,
          scale: 0.05,
        }
      });
      console.log('✅ 技能树加载完成，节点数:', nodePositions.size);
    } catch (error) {
      set({ error: (error as Error).message, loading: false });
      console.error('❌ 技能树加载失败:', error);
    }
  },

  // 分配节点
  allocateNode: (nodeId) => {
    set((state) => {
      const newAllocated = new Set(state.allocatedNodes);
      newAllocated.add(nodeId);
      return { allocatedNodes: newAllocated };
    });
  },

  // 取消分配
  deallocateNode: (nodeId) => {
    set((state) => {
      const newAllocated = new Set(state.allocatedNodes);
      newAllocated.delete(nodeId);
      return { allocatedNodes: newAllocated };
    });
  },

  // 切换节点状态
  toggleNode: (nodeId) => {
    const { allocatedNodes } = get();
    if (allocatedNodes.has(nodeId)) {
      get().deallocateNode(nodeId);
    } else {
      get().allocateNode(nodeId);
    }
  },

  // 设置悬停节点
  setHoveredNode: (nodeId) => set({ hoveredNode: nodeId }),

  // 设置职业
  setSelectedClass: (classIndex) => set({ selectedClass: classIndex }),

  // 视口控制
  setViewport: (viewport) => set((state) => ({
    viewport: { ...state.viewport, ...viewport }
  })),

  zoomIn: () => set((state) => ({
    viewport: { ...state.viewport, scale: Math.min(state.viewport.scale * 1.2, 1) }
  })),

  zoomOut: () => set((state) => ({
    viewport: { ...state.viewport, scale: Math.max(state.viewport.scale / 1.2, 0.01) }
  })),

  resetViewport: () => {
    const { treeData } = get();
    if (treeData) {
      set({
        viewport: {
          x: (treeData.min_x + treeData.max_x) / 2,
          y: (treeData.min_y + treeData.max_y) / 2,
          scale: 0.05,
        }
      });
    }
  },

  // 工具方法
  getNode: (nodeId) => {
    const { treeData } = get();
    return treeData?.nodes[nodeId] || null;
  },

  getNodePosition: (nodeId) => {
    const { nodePositions } = get();
    return nodePositions.get(nodeId) || null;
  },

  // 获取已分配节点的修改器
  getAllocatedModifiers: () => {
    const { allocatedNodes, treeData } = get();
    const modifiers: Modifier[] = [];

    if (!treeData) return modifiers;

    for (const nodeId of allocatedNodes) {
      const node = treeData.nodes[nodeId];
      if (node?.stats) {
        for (const stat of node.stats) {
          const mod = parseStatToModifier(stat);
          if (mod) {
            modifiers.push(mod);
          }
        }
      }
    }

    return modifiers;
  },

  // 获取总分配点数
  getTotalAllocatedPoints: () => {
    return get().allocatedNodes.size;
  },
}));



































