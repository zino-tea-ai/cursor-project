/**
 * 被动技能树类型定义
 */

// 节点连接
export interface NodeConnection {
  orbit: number;
  id: number;
}

// 技能树节点
export interface TreeNode {
  orbit: number;
  orbitIndex: number;
  stats: string[];
  connections: NodeConnection[];
  group: number;
  name: string;
  icon: string;
  skill?: number;
  isKeystone?: boolean;
  isNotable?: boolean;
  isJewelSocket?: boolean;
  isMastery?: boolean;
  isAscendancyStart?: boolean;
  ascendancyName?: string;
  classStartIndex?: number;
  grantedStrength?: number;
  grantedDexterity?: number;
  grantedIntelligence?: number;
  grantedPassivePoints?: number;
}

// 节点组
export interface TreeGroup {
  nodes: number[];
  orbits: number[];
  x: number;
  y: number;
  isProxy?: boolean;
}

// 升华职业
export interface Ascendancy {
  id: string;
  internalId: string;
  name: string;
  background: {
    width: number;
    height: number;
    x: number;
    y: number;
    section: string;
    image: string;
  };
}

// 职业
export interface CharacterClass {
  name: string;
  base_str: number;
  base_dex: number;
  base_int: number;
  ascendancies: Ascendancy[];
  background: {
    width: number;
    height: number;
    x: number;
    y: number;
    image: string;
    section: string;
    active?: { width: number; height: number };
    bg?: { width: number; height: number };
  };
}

// 技能树常量
export interface TreeConstants {
  classes: {
    StrClass: number;
    DexClass: number;
    IntClass: number;
    StrDexClass: number;
    StrIntClass: number;
    DexIntClass: number;
    StrDexIntClass: number;
  };
  characterAttributes: {
    Strength: number;
    Dexterity: number;
    Intelligence: number;
  };
  PSSCentreInnerRadius: number;
  skillsPerOrbit: number[];
  orbitRadii: number[];
}

// 完整技能树数据
export interface TreeData {
  tree: string;
  min_x: number;
  min_y: number;
  max_x: number;
  max_y: number;
  groups: (TreeGroup | null)[];
  nodes: Record<string, TreeNode>;
  classes: CharacterClass[];
  constants: TreeConstants;
  assets: Record<string, any>;
  nodeOverlay: any;
  connectionArt: any;
  jewelSlots: number[];
  ddsCoords: Record<string, any>;
}

// 视口状态
export interface Viewport {
  x: number;      // 视口中心 X
  y: number;      // 视口中心 Y
  scale: number;  // 缩放比例
}

// 计算后的节点位置
export interface NodePosition {
  id: number;
  x: number;
  y: number;
  node: TreeNode;
}































































