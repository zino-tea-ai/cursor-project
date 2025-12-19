/**
 * 技能配置状态管理
 */

import { create } from 'zustand';
import type { ActiveSkill, SupportGem, SkillSetup } from '../types/skills';
import type { Modifier } from '../types';
import { ACTIVE_SKILLS, SUPPORT_GEMS } from '../data/skills';

interface SkillState {
  // 当前技能配置
  skillSetup: SkillSetup;
  
  // 可用技能和辅助宝石
  availableSkills: ActiveSkill[];
  availableSupports: SupportGem[];
  
  // Actions
  setActiveSkill: (skill: ActiveSkill | null) => void;
  setSkillLevel: (level: number) => void;
  addSupportGem: (gem: SupportGem) => void;
  removeSupportGem: (gemId: string) => void;
  setSupportGemLevel: (gemId: string, level: number) => void;
  clearSupports: () => void;
  
  // 计算相关
  getEffectiveStats: () => {
    minDamage: number;
    maxDamage: number;
    critChance: number;
    castTime: number;
    manaCost: number;
  };
  getAllModifiers: () => Modifier[];
  getTotalManaMultiplier: () => number;
}

export const useSkillStore = create<SkillState>((set, get) => ({
  // 初始状态
  skillSetup: {
    activeSkill: ACTIVE_SKILLS[0], // 默认选择电弧
    activeSkillLevel: 1,
    supportGems: [],
    enabled: true
  },
  
  availableSkills: ACTIVE_SKILLS,
  availableSupports: SUPPORT_GEMS,
  
  // 设置主动技能
  setActiveSkill: (skill) => {
    set((state) => ({
      skillSetup: {
        ...state.skillSetup,
        activeSkill: skill,
        // 清除不兼容的辅助宝石
        supportGems: skill 
          ? state.skillSetup.supportGems.filter(sg => 
              sg.gem.tags.some(tag => skill.tags.includes(tag))
            )
          : []
      }
    }));
  },
  
  // 设置技能等级
  setSkillLevel: (level) => {
    set((state) => ({
      skillSetup: {
        ...state.skillSetup,
        activeSkillLevel: Math.max(1, Math.min(20, level))
      }
    }));
  },
  
  // 添加辅助宝石
  addSupportGem: (gem) => {
    const { skillSetup } = get();
    
    // 检查是否已添加
    if (skillSetup.supportGems.some(sg => sg.gem.id === gem.id)) {
      return;
    }
    
    // 最多6个辅助宝石
    if (skillSetup.supportGems.length >= 6) {
      return;
    }
    
    set((state) => ({
      skillSetup: {
        ...state.skillSetup,
        supportGems: [...state.skillSetup.supportGems, { gem, level: 1 }]
      }
    }));
  },
  
  // 移除辅助宝石
  removeSupportGem: (gemId) => {
    set((state) => ({
      skillSetup: {
        ...state.skillSetup,
        supportGems: state.skillSetup.supportGems.filter(sg => sg.gem.id !== gemId)
      }
    }));
  },
  
  // 设置辅助宝石等级
  setSupportGemLevel: (gemId, level) => {
    set((state) => ({
      skillSetup: {
        ...state.skillSetup,
        supportGems: state.skillSetup.supportGems.map(sg =>
          sg.gem.id === gemId 
            ? { ...sg, level: Math.max(1, Math.min(20, level)) }
            : sg
        )
      }
    }));
  },
  
  // 清空辅助宝石
  clearSupports: () => {
    set((state) => ({
      skillSetup: {
        ...state.skillSetup,
        supportGems: []
      }
    }));
  },
  
  // 获取有效属性（考虑等级加成）
  getEffectiveStats: () => {
    const { skillSetup } = get();
    const { activeSkill, activeSkillLevel } = skillSetup;
    
    if (!activeSkill) {
      return { minDamage: 0, maxDamage: 0, critChance: 0, castTime: 1, manaCost: 0 };
    }
    
    const levelBonus = (activeSkillLevel - 1) * activeSkill.levelScaling.damagePerLevel;
    const manaBonus = (activeSkillLevel - 1) * activeSkill.levelScaling.manaCostPerLevel;
    
    return {
      minDamage: activeSkill.baseMinDamage + levelBonus * 0.8,
      maxDamage: activeSkill.baseMaxDamage + levelBonus * 1.2,
      critChance: activeSkill.baseCritChance,
      castTime: activeSkill.baseCastTime,
      manaCost: Math.round(activeSkill.baseManaCost + manaBonus)
    };
  },
  
  // 获取所有辅助宝石提供的修改器
  getAllModifiers: () => {
    const { skillSetup } = get();
    const modifiers: Modifier[] = [];
    
    for (const { gem, level } of skillSetup.supportGems) {
      for (const mod of gem.modifiers) {
        // 简单的等级加成：每级增加5%效果
        const levelMultiplier = 1 + (level - 1) * 0.05;
        modifiers.push({
          name: mod.stat,
          type: mod.type,
          value: Math.round(mod.value * levelMultiplier),
          source: `support:${gem.id}`
        });
      }
    }
    
    return modifiers;
  },
  
  // 获取总魔力倍率
  getTotalManaMultiplier: () => {
    const { skillSetup } = get();
    return skillSetup.supportGems.reduce(
      (mult, { gem }) => mult * gem.manaMultiplier,
      1
    );
  }
}));



































