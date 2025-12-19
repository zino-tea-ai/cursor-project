/**
 * 国际化状态管理
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type Language = 'zh' | 'en';

// 翻译文本
const translations: Record<Language, Record<string, string>> = {
  zh: {
    // 通用
    'common.save': '保存',
    'common.load': '加载',
    'common.remove': '移除',
    'common.clear': '清空',
    'common.cancel': '取消',
    'common.confirm': '确认',
    'common.search': '搜索',
    'common.import': '导入',
    'common.export': '导出',
    
    // 导航
    'nav.damage': '伤害计算',
    'nav.tree': '被动技能树',
    'nav.skills': '技能配置',
    'nav.equipment': '装备',
    'nav.config': '配置',
    
    // 角色
    'character.name': '名称',
    'character.level': '等级',
    'character.class': '职业',
    
    // 技能
    'skill.activeSkill': '主动技能',
    'skill.selectSkill': '选择技能...',
    'skill.level': '等级',
    'skill.damage': '伤害',
    'skill.critChance': '暴击几率',
    'skill.castTime': '施法时间',
    'skill.manaCost': '魔力消耗',
    'skill.linkedSupports': '链接的辅助宝石',
    'skill.noSupports': '点击下方添加辅助宝石',
    'skill.availableSupports': '可用辅助宝石',
    'skill.manaMult': '魔力倍率',
    
    // 装备
    'equipment.title': '装备',
    'equipment.slot': '槽位',
    'equipment.modifiers': '词缀',
    'equipment.addModifier': '添加词缀',
    'equipment.empty': '空',
    'equipment.edit': '编辑',
    
    // 被动树
    'tree.title': '被动技能树',
    'tree.allocated': '已分配',
    'tree.available': '可用',
    'tree.points': '点',
    'tree.search': '搜索节点...',
    
    // 伤害
    'damage.title': '伤害统计',
    'damage.average': '平均伤害',
    'damage.dps': 'DPS',
    'damage.min': '最小伤害',
    'damage.max': '最大伤害',
    'damage.crit': '暴击几率',
    'damage.critMult': '暴击倍率',
    'damage.speed': '速度',
    'damage.selectSkill': '请选择一个技能',
    
    // 修改器
    'modifier.title': '修改器',
    'modifier.add': '添加修改器',
    'modifier.source': '来源',
    'modifier.passive': '被动树',
    'modifier.equipment': '装备',
    'modifier.support': '辅助宝石',
    
    // Build
    'build.import': '导入 Build',
    'build.export': '导出 Build',
    'build.save': '保存',
    'build.load': '加载',
    'build.importSuccess': '导入成功',
    'build.importError': '导入失败：格式无效',
    'build.exportSuccess': '已复制到剪贴板',
    'build.name': 'Build 名称',
    
    // 页脚
    'footer.engine': '计算引擎',
    'footer.version': '版本',
  },
  
  en: {
    // Common
    'common.save': 'Save',
    'common.load': 'Load',
    'common.remove': 'Remove',
    'common.clear': 'Clear',
    'common.cancel': 'Cancel',
    'common.confirm': 'Confirm',
    'common.search': 'Search',
    'common.import': 'Import',
    'common.export': 'Export',
    
    // Navigation
    'nav.damage': 'Damage',
    'nav.tree': 'Passive Tree',
    'nav.skills': 'Skills',
    'nav.equipment': 'Equipment',
    'nav.config': 'Config',
    
    // Character
    'character.name': 'Name',
    'character.level': 'Level',
    'character.class': 'Class',
    
    // Skills
    'skill.activeSkill': 'Active Skill',
    'skill.selectSkill': 'Select skill...',
    'skill.level': 'Level',
    'skill.damage': 'Damage',
    'skill.critChance': 'Crit Chance',
    'skill.castTime': 'Cast Time',
    'skill.manaCost': 'Mana Cost',
    'skill.linkedSupports': 'Linked Support Gems',
    'skill.noSupports': 'Click below to add support gems',
    'skill.availableSupports': 'Available Supports',
    'skill.manaMult': 'Mana Mult',
    
    // Equipment
    'equipment.title': 'Equipment',
    'equipment.slot': 'Slot',
    'equipment.modifiers': 'Modifiers',
    'equipment.addModifier': 'Add Modifier',
    'equipment.empty': 'Empty',
    'equipment.edit': 'Edit',
    
    // Passive Tree
    'tree.title': 'Passive Tree',
    'tree.allocated': 'Allocated',
    'tree.available': 'Available',
    'tree.points': 'points',
    'tree.search': 'Search nodes...',
    
    // Damage
    'damage.title': 'Damage Stats',
    'damage.average': 'Average Damage',
    'damage.dps': 'DPS',
    'damage.min': 'Min Damage',
    'damage.max': 'Max Damage',
    'damage.crit': 'Crit Chance',
    'damage.critMult': 'Crit Multiplier',
    'damage.speed': 'Speed',
    'damage.selectSkill': 'Select a skill',
    
    // Modifiers
    'modifier.title': 'Modifiers',
    'modifier.add': 'Add Modifier',
    'modifier.source': 'Source',
    'modifier.passive': 'Passive',
    'modifier.equipment': 'Equipment',
    'modifier.support': 'Support Gem',
    
    // Build
    'build.import': 'Import Build',
    'build.export': 'Export Build',
    'build.save': 'Save',
    'build.load': 'Load',
    'build.importSuccess': 'Import successful',
    'build.importError': 'Import failed: Invalid format',
    'build.exportSuccess': 'Copied to clipboard',
    'build.name': 'Build Name',
    
    // Footer
    'footer.engine': 'Engine',
    'footer.version': 'Version',
  }
};

interface I18nState {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string) => string;
  toggleLanguage: () => void;
}

export const useI18nStore = create<I18nState>()(
  persist(
    (set, get) => ({
      language: 'zh',
      
      setLanguage: (lang) => set({ language: lang }),
      
      t: (key) => {
        const { language } = get();
        return translations[language][key] || key;
      },
      
      toggleLanguage: () => {
        set((state) => ({
          language: state.language === 'zh' ? 'en' : 'zh'
        }));
      }
    }),
    {
      name: 'pob2-i18n'
    }
  )
);



































