/**
 * Build 导入/导出功能
 */

import { create } from 'zustand';
import { useBuildStore } from './buildStore';
import { useTreeStore } from './treeStore';
import { useSkillStore } from './skillStore';
import { useEquipmentStore } from './equipmentStore';
import { ACTIVE_SKILLS, SUPPORT_GEMS } from '../data/skills';

interface BuildExportData {
  version: string;
  name: string;
  character: {
    name: string;
    level: number;
    class: string;
  };
  skill: {
    activeSkillId: string | null;
    activeSkillLevel: number;
    supportGemIds: { id: string; level: number }[];
  };
  passives: number[];
  equipment: {
    slot: string;
    modifiers: { name: string; type: string; value: number }[];
  }[];
  modifiers: { name: string; type: string; value: number }[];
}

interface BuildExportState {
  lastExport: string | null;
  lastImportError: string | null;
  
  exportBuild: () => string;
  importBuild: (data: string) => boolean;
  copyToClipboard: () => Promise<boolean>;
  importFromClipboard: () => Promise<boolean>;
}

export const useBuildExportStore = create<BuildExportState>((set, get) => ({
  lastExport: null,
  lastImportError: null,
  
  exportBuild: () => {
    const buildStore = useBuildStore.getState();
    const treeStore = useTreeStore.getState();
    const skillStore = useSkillStore.getState();
    const equipmentStore = useEquipmentStore.getState();
    
    const exportData: BuildExportData = {
      version: '0.1.0',
      name: buildStore.characterName,
      character: {
        name: buildStore.characterName,
        level: buildStore.characterLevel,
        class: buildStore.characterClass
      },
      skill: {
        activeSkillId: skillStore.skillSetup.activeSkill?.id || null,
        activeSkillLevel: skillStore.skillSetup.activeSkillLevel,
        supportGemIds: skillStore.skillSetup.supportGems.map(sg => ({
          id: sg.gem.id,
          level: sg.level
        }))
      },
      passives: Array.from(treeStore.allocatedNodes),
      equipment: Object.entries(equipmentStore.equipment).map(([slot, item]) => ({
        slot,
        modifiers: item?.modifiers.map(m => ({
          name: m.name,
          type: m.type,
          value: m.value
        })) || []
      })),
      modifiers: buildStore.modifiers.map(m => ({
        name: m.name,
        type: m.type,
        value: m.value
      }))
    };
    
    // Base64 编码
    const jsonStr = JSON.stringify(exportData);
    const encoded = btoa(unescape(encodeURIComponent(jsonStr)));
    
    set({ lastExport: encoded, lastImportError: null });
    return encoded;
  },
  
  importBuild: (data: string) => {
    try {
      // Base64 解码
      const jsonStr = decodeURIComponent(escape(atob(data.trim())));
      const importData: BuildExportData = JSON.parse(jsonStr);
      
      // 验证版本
      if (!importData.version) {
        throw new Error('Invalid build format');
      }
      
      // 导入角色信息
      const buildStore = useBuildStore.getState();
      buildStore.setCharacterName(importData.character.name);
      buildStore.setCharacterLevel(importData.character.level);
      buildStore.setCharacterClass(importData.character.class);
      
      // 导入技能
      const skillStore = useSkillStore.getState();
      if (importData.skill.activeSkillId) {
        const skill = ACTIVE_SKILLS.find(s => s.id === importData.skill.activeSkillId);
        if (skill) {
          skillStore.setActiveSkill(skill);
          skillStore.setSkillLevel(importData.skill.activeSkillLevel);
        }
      }
      
      // 导入辅助宝石
      skillStore.clearSupports();
      for (const { id, level } of importData.skill.supportGemIds) {
        const gem = SUPPORT_GEMS.find(g => g.id === id);
        if (gem) {
          skillStore.addSupportGem(gem);
          skillStore.setSupportGemLevel(id, level);
        }
      }
      
      // 导入被动树
      const treeStore = useTreeStore.getState();
      // 先清空
      for (const nodeId of treeStore.allocatedNodes) {
        treeStore.deallocateNode(nodeId);
      }
      // 再导入
      for (const nodeId of importData.passives) {
        treeStore.allocateNode(nodeId);
      }
      
      // 导入装备
      const equipmentStore = useEquipmentStore.getState();
      for (const eq of importData.equipment) {
        for (const mod of eq.modifiers) {
          equipmentStore.addModifierToItem(eq.slot as any, {
            name: mod.name,
            type: mod.type as any,
            value: mod.value
          });
        }
      }
      
      // 导入手动修改器
      buildStore.clearModifiers();
      for (const mod of importData.modifiers) {
        buildStore.addModifier({
          name: mod.name,
          type: mod.type as any,
          value: mod.value
        });
      }
      
      // 重新计算
      buildStore.calculateDamage();
      
      set({ lastImportError: null });
      return true;
    } catch (error) {
      set({ lastImportError: (error as Error).message });
      return false;
    }
  },
  
  copyToClipboard: async () => {
    const encoded = get().exportBuild();
    try {
      await navigator.clipboard.writeText(encoded);
      return true;
    } catch {
      return false;
    }
  },
  
  importFromClipboard: async () => {
    try {
      const text = await navigator.clipboard.readText();
      return get().importBuild(text);
    } catch {
      set({ lastImportError: 'Failed to read clipboard' });
      return false;
    }
  }
}));











