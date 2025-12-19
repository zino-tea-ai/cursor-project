/**
 * 技能和辅助宝石类型定义
 */

export type DamageTag = 'Physical' | 'Fire' | 'Cold' | 'Lightning' | 'Chaos' | 'Elemental';
export type SkillTag = 'Spell' | 'Attack' | 'Melee' | 'Projectile' | 'AoE' | 'Duration' | 'Minion' | 'Totem' | 'Trap' | 'Mine';

// 主动技能
export interface ActiveSkill {
  id: string;
  name: string;
  nameZh: string;
  description: string;
  descriptionZh: string;
  damageType: DamageTag;
  tags: SkillTag[];
  baseMinDamage: number;
  baseMaxDamage: number;
  baseCritChance: number;
  baseCastTime: number;
  baseManaCost: number;
  levelScaling: {
    damagePerLevel: number;
    manaCostPerLevel: number;
  };
  icon?: string;
}

// 辅助宝石
export interface SupportGem {
  id: string;
  name: string;
  nameZh: string;
  description: string;
  descriptionZh: string;
  tags: SkillTag[];
  manaMultiplier: number; // 1.3 = 130% mana cost
  modifiers: SupportModifier[];
  levelScaling?: {
    valuePerLevel: number;
    modifierIndex: number;
  };
}

export interface SupportModifier {
  stat: string;
  type: 'BASE' | 'INC' | 'MORE';
  value: number;
}

// 技能链接配置
export interface SkillSetup {
  activeSkill: ActiveSkill | null;
  activeSkillLevel: number;
  supportGems: {
    gem: SupportGem;
    level: number;
  }[];
  enabled: boolean;
}



































