// PoB2 Plus 类型定义

// 导出技能树类型
export * from './tree';

// 导出技能类型
export * from './skills';

// 伤害类型
export type DamageType = 'Physical' | 'Fire' | 'Cold' | 'Lightning' | 'Chaos';

// 修改器类型
export type ModifierType = 'BASE' | 'INC' | 'MORE' | 'FLAG' | 'OVERRIDE';

// 修改器
export interface Modifier {
  name: string;
  type: ModifierType;
  value: number;
  flags?: number;
  keywordFlags?: number;
  source?: string;
}

// 技能数据
export interface Skill {
  id: string;
  name: string;
  nameZh?: string;
  description?: string;
  damageType: DamageType;
  castTime: number;
  critChance: number;
  levels: SkillLevel[];
}

export interface SkillLevel {
  level: number;
  minDamage: number;
  maxDamage: number;
  manaCost: number;
  levelRequirement: number;
}

// 角色属性
export interface CharacterStats {
  level: number;
  class: string;
  ascendancy?: string;
  strength: number;
  dexterity: number;
  intelligence: number;
  life: number;
  mana: number;
  energyShield: number;
}

// 计算结果
export interface DamageResult {
  minDamage: number;
  maxDamage: number;
  averageDamage: number;
  dps: number;
  critChance: number;
  critMultiplier: number;
  hitChance: number;
  attackSpeed: number;
  breakdown: DamageBreakdown;
}

export interface DamageBreakdown {
  baseDamage: { min: number; max: number };
  increasedMultiplier: number;
  moreMultipliers: number[];
  finalMultiplier: number;
  sources: { name: string; value: number }[];
}

// Build 数据
export interface Build {
  id: string;
  name: string;
  class: string;
  level: number;
  skills: string[];
  passives: number[];
  items: Item[];
  config: BuildConfig;
  createdAt: Date;
  updatedAt: Date;
}

export interface BuildConfig {
  enemyLevel: number;
  enemyResistances: Record<DamageType, number>;
  buffs: string[];
  debuffs: string[];
}

// 物品
export interface Item {
  id: string;
  name: string;
  baseType: string;
  rarity: 'normal' | 'magic' | 'rare' | 'unique';
  slot: ItemSlot;
  modifiers: Modifier[];
  requirements?: {
    level?: number;
    str?: number;
    dex?: number;
    int?: number;
  };
}

export type ItemSlot = 
  | 'weapon1' | 'weapon2' 
  | 'helmet' | 'body' | 'gloves' | 'boots'
  | 'amulet' | 'ring1' | 'ring2' | 'belt'
  | 'flask1' | 'flask2' | 'flask3' | 'flask4' | 'flask5';

// 被动树节点
export interface PassiveNode {
  id: number;
  name: string;
  type: 'normal' | 'notable' | 'keystone' | 'mastery' | 'jewel';
  stats: string[];
  x: number;
  y: number;
  connections: number[];
  allocated?: boolean;
}











