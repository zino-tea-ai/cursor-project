/**
 * Build 状态管理
 */

import { create } from 'zustand';
import type { Modifier, DamageResult } from '../types';
import { getLuaEngine } from '../engine/LuaEngine';
import { useTreeStore } from './treeStore';
import { useSkillStore } from './skillStore';
import { useEquipmentStore } from './equipmentStore';

interface Skill {
  id: string;
  name: string;
  nameZh?: string;
  damageType: string;
  minDamage: number;
  maxDamage: number;
  critChance: number;
  castTime: number;
  isSpell?: boolean;
  isAttack?: boolean;
}

interface BuildState {
  // 角色信息
  characterName: string;
  characterLevel: number;
  characterClass: string;
  
  // 当前技能
  activeSkill: Skill | null;
  
  // 修改器列表
  modifiers: Modifier[];
  
  // 计算结果
  damageResult: DamageResult | null;
  
  // 引擎状态
  engineReady: boolean;
  
  // Actions
  setCharacterName: (name: string) => void;
  setCharacterLevel: (level: number) => void;
  setCharacterClass: (cls: string) => void;
  setActiveSkill: (skill: Skill) => void;
  addModifier: (mod: Modifier) => void;
  removeModifier: (index: number) => void;
  clearModifiers: () => void;
  calculateDamage: () => Promise<void>;
  initializeEngine: () => Promise<void>;
}

export const useBuildStore = create<BuildState>((set, get) => ({
  // 初始状态
  characterName: '未命名角色',
  characterLevel: 1,
  characterClass: 'Sorceress',
  activeSkill: null,
  modifiers: [],
  damageResult: null,
  engineReady: false,

  // Actions
  setCharacterName: (name) => set({ characterName: name }),
  setCharacterLevel: (level) => set({ characterLevel: level }),
  setCharacterClass: (cls) => set({ characterClass: cls }),
  
  setActiveSkill: (skill) => {
    set({ activeSkill: skill });
    // 自动重新计算
    get().calculateDamage();
  },

  addModifier: (mod) => {
    set((state) => ({ modifiers: [...state.modifiers, mod] }));
    get().calculateDamage();
  },

  removeModifier: (index) => {
    set((state) => ({
      modifiers: state.modifiers.filter((_, i) => i !== index)
    }));
    get().calculateDamage();
  },

  clearModifiers: () => {
    set({ modifiers: [] });
    get().calculateDamage();
  },

  initializeEngine: async () => {
    try {
      const engine = getLuaEngine();
      await engine.initialize();
      set({ engineReady: true });
      console.log('✅ 引擎初始化完成');
    } catch (error) {
      console.error('❌ 引擎初始化失败:', error);
    }
  },

  calculateDamage: async () => {
    const { activeSkill, modifiers, engineReady } = get();
    
    if (!engineReady || !activeSkill) {
      set({ damageResult: null });
      return;
    }

    try {
      const engine = getLuaEngine();
      
      // 获取所有来源的修改器
      const passiveModifiers = useTreeStore.getState().getAllocatedModifiers();
      const skillModifiers = useSkillStore.getState().getAllModifiers();
      const equipmentModifiers = useEquipmentStore.getState().getAllModifiers();
      
      // 合并所有修改器
      const allModifiers = [...modifiers, ...passiveModifiers, ...skillModifiers, ...equipmentModifiers];
      
      // 构建 Lua 代码
      const luaCode = `
        -- 创建 ModDB
        local modDB = ModDB.new()
        
        -- 添加修改器（手动 + 被动树）
        ${allModifiers.map(mod => `
        modDB:AddMod({ name = "${mod.name}", type = "${mod.type}", value = ${mod.value} })
        `).join('')}
        
        -- 定义技能
        local skill = {
          name = "${activeSkill.name}",
          damageType = "${activeSkill.damageType}",
          minDamage = ${activeSkill.minDamage},
          maxDamage = ${activeSkill.maxDamage},
          critChance = ${activeSkill.critChance},
          castTime = ${activeSkill.castTime},
          isSpell = ${activeSkill.isSpell ? 'true' : 'false'},
          isAttack = ${activeSkill.isAttack ? 'true' : 'false'}
        }
        
        -- 计算伤害
        local result = calculateDamage(skill, modDB, {})
        
        return result
      `;

      const result = engine.execute(luaCode);
      
      if (result) {
        set({
          damageResult: {
            minDamage: result.minDamage || 0,
            maxDamage: result.maxDamage || 0,
            averageDamage: result.averageDamage || 0,
            dps: result.dps || 0,
            critChance: result.critChance || 0,
            critMultiplier: result.critMultiplier || 150,
            hitChance: 100,
            attackSpeed: result.speed || 1,
            breakdown: {
              baseDamage: {
                min: result.breakdown?.baseDamageMin || 0,
                max: result.breakdown?.baseDamageMax || 0
              },
              increasedMultiplier: result.breakdown?.increased || 1,
              moreMultipliers: [],
              finalMultiplier: (result.breakdown?.increased || 1) * (result.breakdown?.more || 1),
              sources: []
            }
          }
        });
      }
    } catch (error) {
      console.error('计算错误:', error);
      set({ damageResult: null });
    }
  }
}));

// 预设技能数据
export const PRESET_SKILLS: Skill[] = [
  {
    id: 'arc',
    name: 'Arc',
    nameZh: '电弧',
    damageType: 'Lightning',
    minDamage: 1,
    maxDamage: 13,
    critChance: 9,
    castTime: 1.1,
    isSpell: true
  },
  {
    id: 'fireball',
    name: 'Fireball',
    nameZh: '火球',
    damageType: 'Fire',
    minDamage: 8,
    maxDamage: 12,
    critChance: 6,
    castTime: 0.85,
    isSpell: true
  },
  {
    id: 'ice_spear',
    name: 'Ice Spear',
    nameZh: '冰矛',
    damageType: 'Cold',
    minDamage: 5,
    maxDamage: 15,
    critChance: 7,
    castTime: 0.75,
    isSpell: true
  },
  {
    id: 'heavy_strike',
    name: 'Heavy Strike',
    nameZh: '重击',
    damageType: 'Physical',
    minDamage: 10,
    maxDamage: 20,
    critChance: 5,
    castTime: 1.0,
    isAttack: true
  }
];

// 预设修改器
export const PRESET_MODIFIERS: Modifier[] = [
  { name: 'Damage', type: 'INC', value: 50 },
  { name: 'SpellDamage', type: 'INC', value: 30 },
  { name: 'LightningDamage', type: 'INC', value: 40 },
  { name: 'FireDamage', type: 'INC', value: 40 },
  { name: 'ColdDamage', type: 'INC', value: 40 },
  { name: 'PhysicalDamage', type: 'INC', value: 40 },
  { name: 'CritChance', type: 'INC', value: 100 },
  { name: 'CritMultiplier', type: 'BASE', value: 50 },
  { name: 'CastSpeed', type: 'INC', value: 30 },
  { name: 'AttackSpeed', type: 'INC', value: 30 },
  { name: 'Damage', type: 'MORE', value: 20 },
  { name: 'SpellDamage', type: 'MORE', value: 30 },
];































































