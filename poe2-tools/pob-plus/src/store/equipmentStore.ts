/**
 * 装备系统状态管理
 */

import { create } from 'zustand';
import type { Item, ItemSlot, Modifier } from '../types';

// 装备槽位配置
export const EQUIPMENT_SLOTS: { id: ItemSlot; name: string; nameZh: string }[] = [
  { id: 'weapon1', name: 'Main Hand', nameZh: '主手' },
  { id: 'weapon2', name: 'Off Hand', nameZh: '副手' },
  { id: 'helmet', name: 'Helmet', nameZh: '头盔' },
  { id: 'body', name: 'Body Armour', nameZh: '胸甲' },
  { id: 'gloves', name: 'Gloves', nameZh: '手套' },
  { id: 'boots', name: 'Boots', nameZh: '鞋子' },
  { id: 'amulet', name: 'Amulet', nameZh: '项链' },
  { id: 'ring1', name: 'Ring 1', nameZh: '戒指1' },
  { id: 'ring2', name: 'Ring 2', nameZh: '戒指2' },
  { id: 'belt', name: 'Belt', nameZh: '腰带' }
];

// 基础装备类型
export const BASE_ITEMS: Record<ItemSlot, { name: string; nameZh: string; baseType: string }[]> = {
  weapon1: [
    { name: 'Driftwood Wand', nameZh: '浮木法杖', baseType: 'wand' },
    { name: 'Iron Sword', nameZh: '铁剑', baseType: 'sword' },
    { name: 'Driftwood Sceptre', nameZh: '浮木权杖', baseType: 'sceptre' },
    { name: 'Crude Bow', nameZh: '粗制弓', baseType: 'bow' },
  ],
  weapon2: [
    { name: 'Twig Spirit Shield', nameZh: '细枝灵盾', baseType: 'shield' },
    { name: 'Goathide Buckler', nameZh: '羊皮圆盾', baseType: 'shield' },
  ],
  helmet: [
    { name: 'Iron Hat', nameZh: '铁帽', baseType: 'helmet' },
    { name: 'Leather Cap', nameZh: '皮帽', baseType: 'helmet' },
  ],
  body: [
    { name: 'Plate Vest', nameZh: '板甲背心', baseType: 'body' },
    { name: 'Shabby Jerkin', nameZh: '破旧短衫', baseType: 'body' },
  ],
  gloves: [
    { name: 'Iron Gauntlets', nameZh: '铁护手', baseType: 'gloves' },
    { name: 'Rawhide Gloves', nameZh: '生皮手套', baseType: 'gloves' },
  ],
  boots: [
    { name: 'Iron Greaves', nameZh: '铁胫甲', baseType: 'boots' },
    { name: 'Rawhide Boots', nameZh: '生皮靴', baseType: 'boots' },
  ],
  amulet: [
    { name: 'Coral Amulet', nameZh: '珊瑚护身符', baseType: 'amulet' },
    { name: 'Jade Amulet', nameZh: '翠玉护身符', baseType: 'amulet' },
  ],
  ring1: [
    { name: 'Iron Ring', nameZh: '铁戒', baseType: 'ring' },
    { name: 'Coral Ring', nameZh: '珊瑚戒指', baseType: 'ring' },
  ],
  ring2: [
    { name: 'Iron Ring', nameZh: '铁戒', baseType: 'ring' },
    { name: 'Sapphire Ring', nameZh: '蓝宝石戒指', baseType: 'ring' },
  ],
  belt: [
    { name: 'Chain Belt', nameZh: '链条腰带', baseType: 'belt' },
    { name: 'Leather Belt', nameZh: '皮革腰带', baseType: 'belt' },
  ],
  flask1: [], flask2: [], flask3: [], flask4: [], flask5: []
};

// 可用词缀
export const AVAILABLE_MODIFIERS: { name: string; nameZh: string; type: 'BASE' | 'INC' | 'MORE'; minValue: number; maxValue: number }[] = [
  { name: 'PhysicalDamage', nameZh: '物理伤害', type: 'INC', minValue: 10, maxValue: 80 },
  { name: 'SpellDamage', nameZh: '法术伤害', type: 'INC', minValue: 10, maxValue: 80 },
  { name: 'FireDamage', nameZh: '火焰伤害', type: 'INC', minValue: 10, maxValue: 50 },
  { name: 'ColdDamage', nameZh: '冰霜伤害', type: 'INC', minValue: 10, maxValue: 50 },
  { name: 'LightningDamage', nameZh: '闪电伤害', type: 'INC', minValue: 10, maxValue: 50 },
  { name: 'ChaosDamage', nameZh: '混沌伤害', type: 'INC', minValue: 10, maxValue: 50 },
  { name: 'CritChance', nameZh: '暴击几率', type: 'INC', minValue: 15, maxValue: 80 },
  { name: 'CritMultiplier', nameZh: '暴击伤害', type: 'BASE', minValue: 10, maxValue: 40 },
  { name: 'CastSpeed', nameZh: '施法速度', type: 'INC', minValue: 5, maxValue: 25 },
  { name: 'AttackSpeed', nameZh: '攻击速度', type: 'INC', minValue: 5, maxValue: 25 },
  { name: 'MaxLife', nameZh: '最大生命', type: 'BASE', minValue: 20, maxValue: 100 },
  { name: 'MaxMana', nameZh: '最大魔力', type: 'BASE', minValue: 20, maxValue: 80 },
  { name: 'Strength', nameZh: '力量', type: 'BASE', minValue: 10, maxValue: 50 },
  { name: 'Dexterity', nameZh: '敏捷', type: 'BASE', minValue: 10, maxValue: 50 },
  { name: 'Intelligence', nameZh: '智慧', type: 'BASE', minValue: 10, maxValue: 50 },
];

interface EquipmentState {
  // 装备槽位
  equipment: Partial<Record<ItemSlot, Item>>;
  
  // 当前编辑的槽位
  editingSlot: ItemSlot | null;
  
  // Actions
  setItem: (slot: ItemSlot, item: Item | null) => void;
  addModifierToItem: (slot: ItemSlot, modifier: Modifier) => void;
  removeModifierFromItem: (slot: ItemSlot, modIndex: number) => void;
  clearSlot: (slot: ItemSlot) => void;
  setEditingSlot: (slot: ItemSlot | null) => void;
  
  // 工具方法
  getAllModifiers: () => Modifier[];
  getItemInSlot: (slot: ItemSlot) => Item | null;
}

let itemIdCounter = 0;

export const useEquipmentStore = create<EquipmentState>((set, get) => ({
  equipment: {},
  editingSlot: null,
  
  setItem: (slot, item) => {
    set((state) => ({
      equipment: {
        ...state.equipment,
        [slot]: item || undefined
      }
    }));
  },
  
  addModifierToItem: (slot, modifier) => {
    const { equipment } = get();
    const item = equipment[slot];
    
    if (!item) {
      // 创建新物品
      const baseItems = BASE_ITEMS[slot];
      const baseItem = baseItems?.[0];
      
      if (baseItem) {
        const newItem: Item = {
          id: `item_${++itemIdCounter}`,
          name: baseItem.name,
          baseType: baseItem.baseType,
          rarity: 'rare',
          slot,
          modifiers: [modifier]
        };
        set((state) => ({
          equipment: { ...state.equipment, [slot]: newItem }
        }));
      }
    } else {
      // 添加词缀到现有物品（最多6个）
      if (item.modifiers.length < 6) {
        set((state) => ({
          equipment: {
            ...state.equipment,
            [slot]: {
              ...item,
              modifiers: [...item.modifiers, modifier]
            }
          }
        }));
      }
    }
  },
  
  removeModifierFromItem: (slot, modIndex) => {
    const { equipment } = get();
    const item = equipment[slot];
    
    if (item) {
      const newMods = item.modifiers.filter((_, i) => i !== modIndex);
      set((state) => ({
        equipment: {
          ...state.equipment,
          [slot]: { ...item, modifiers: newMods }
        }
      }));
    }
  },
  
  clearSlot: (slot) => {
    set((state) => {
      const newEquipment = { ...state.equipment };
      delete newEquipment[slot];
      return { equipment: newEquipment };
    });
  },
  
  setEditingSlot: (slot) => {
    set({ editingSlot: slot });
  },
  
  getAllModifiers: () => {
    const { equipment } = get();
    const modifiers: Modifier[] = [];
    
    for (const item of Object.values(equipment)) {
      if (item) {
        for (const mod of item.modifiers) {
          modifiers.push({
            ...mod,
            source: `equipment:${item.slot}`
          });
        }
      }
    }
    
    return modifiers;
  },
  
  getItemInSlot: (slot) => {
    return get().equipment[slot] || null;
  }
}));































































