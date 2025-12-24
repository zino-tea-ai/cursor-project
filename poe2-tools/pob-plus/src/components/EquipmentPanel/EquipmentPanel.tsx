/**
 * 装备配置面板
 */

import { useState } from 'react';
import { useEquipmentStore, EQUIPMENT_SLOTS, AVAILABLE_MODIFIERS } from '../../store/equipmentStore';
import { useI18nStore } from '../../store/i18nStore';
import { useBuildStore } from '../../store/buildStore';
import type { ItemSlot } from '../../types';

export function EquipmentPanel() {
  const { t, language } = useI18nStore();
  const { calculateDamage } = useBuildStore();
  const {
    equipment,
    editingSlot,
    setEditingSlot,
    addModifierToItem,
    removeModifierFromItem,
    clearSlot,
    getAllModifiers
  } = useEquipmentStore();
  
  const [selectedModifier, setSelectedModifier] = useState(AVAILABLE_MODIFIERS[0]);
  const [modifierValue, setModifierValue] = useState(50);
  
  // 添加词缀并重新计算
  const handleAddModifier = (slot: ItemSlot) => {
    addModifierToItem(slot, {
      name: selectedModifier.name,
      type: selectedModifier.type,
      value: modifierValue
    });
    calculateDamage();
  };
  
  // 移除词缀并重新计算
  const handleRemoveModifier = (slot: ItemSlot, index: number) => {
    removeModifierFromItem(slot, index);
    calculateDamage();
  };
  
  // 清空槽位并重新计算
  const handleClearSlot = (slot: ItemSlot) => {
    clearSlot(slot);
    setEditingSlot(null);
    calculateDamage();
  };
  
  const totalModifiers = getAllModifiers();
  
  return (
    <div className="p-4 space-y-4 overflow-y-auto h-full">
      {/* 装备总览 */}
      <section className="panel">
        <h2 className="text-lg font-semibold text-poe-gold mb-4">
          {t('equipment.title')}
        </h2>
        
        <div className="grid grid-cols-2 gap-2">
          {EQUIPMENT_SLOTS.map(slot => {
            const item = equipment[slot.id];
            const isEditing = editingSlot === slot.id;
            
            return (
              <button
                key={slot.id}
                onClick={() => setEditingSlot(isEditing ? null : slot.id)}
                className={`p-3 text-left rounded transition-colors ${
                  isEditing 
                    ? 'bg-poe-gold/20 border border-poe-gold' 
                    : item 
                      ? 'bg-poe-bg border border-poe-border hover:border-poe-gold/50'
                      : 'bg-poe-bg/50 border border-dashed border-poe-border hover:border-poe-gold/50'
                }`}
              >
                <div className="text-xs text-gray-500">
                  {language === 'zh' ? slot.nameZh : slot.name}
                </div>
                {item ? (
                  <>
                    <div className="text-sm text-yellow-400 font-medium truncate">
                      {item.name}
                    </div>
                    <div className="text-xs text-gray-400">
                      {item.modifiers.length} {t('equipment.modifiers')}
                    </div>
                  </>
                ) : (
                  <div className="text-sm text-gray-600">{t('equipment.empty')}</div>
                )}
              </button>
            );
          })}
        </div>
      </section>
      
      {/* 编辑面板 */}
      {editingSlot && (
        <section className="panel">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-poe-gold">
              {t('equipment.edit')}: {
                language === 'zh' 
                  ? EQUIPMENT_SLOTS.find(s => s.id === editingSlot)?.nameZh 
                  : EQUIPMENT_SLOTS.find(s => s.id === editingSlot)?.name
              }
            </h3>
            <button
              onClick={() => handleClearSlot(editingSlot)}
              className="text-red-400 hover:text-red-300 text-sm"
            >
              {t('common.clear')}
            </button>
          </div>
          
          {/* 当前词缀 */}
          <div className="mb-4">
            <h4 className="text-sm text-gray-400 mb-2">{t('equipment.modifiers')}:</h4>
            {equipment[editingSlot]?.modifiers.length ? (
              <div className="space-y-1">
                {equipment[editingSlot]!.modifiers.map((mod, i) => (
                  <div key={i} className="flex items-center justify-between p-2 bg-poe-bg rounded">
                    <span className="text-sm">
                      <span className="text-green-400">
                        {mod.type === 'BASE' ? '+' : ''}{mod.value}
                        {mod.type !== 'BASE' ? '%' : ''}
                      </span>
                      <span className="text-gray-400 ml-2">
                        {AVAILABLE_MODIFIERS.find(m => m.name === mod.name)?.[language === 'zh' ? 'nameZh' : 'name'] || mod.name}
                      </span>
                    </span>
                    <button
                      onClick={() => handleRemoveModifier(editingSlot, i)}
                      className="text-red-400 hover:text-red-300 px-2"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-600 text-sm">{t('equipment.empty')}</p>
            )}
          </div>
          
          {/* 添加词缀 */}
          {(!equipment[editingSlot] || equipment[editingSlot]!.modifiers.length < 6) && (
            <div className="space-y-3 pt-3 border-t border-poe-border">
              <h4 className="text-sm text-gray-400">{t('equipment.addModifier')}:</h4>
              
              <select
                value={selectedModifier.name}
                onChange={(e) => {
                  const mod = AVAILABLE_MODIFIERS.find(m => m.name === e.target.value);
                  if (mod) {
                    setSelectedModifier(mod);
                    setModifierValue(Math.round((mod.minValue + mod.maxValue) / 2));
                  }
                }}
                className="input-field w-full"
              >
                {AVAILABLE_MODIFIERS.map(mod => (
                  <option key={mod.name} value={mod.name}>
                    {language === 'zh' ? mod.nameZh : mod.name} ({mod.type})
                  </option>
                ))}
              </select>
              
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min={selectedModifier.minValue}
                  max={selectedModifier.maxValue}
                  value={modifierValue}
                  onChange={(e) => setModifierValue(parseInt(e.target.value))}
                  className="flex-1"
                />
                <input
                  type="number"
                  min={selectedModifier.minValue}
                  max={selectedModifier.maxValue}
                  value={modifierValue}
                  onChange={(e) => setModifierValue(parseInt(e.target.value) || selectedModifier.minValue)}
                  className="input-field w-20"
                />
              </div>
              
              <button
                onClick={() => handleAddModifier(editingSlot)}
                className="btn-primary w-full"
              >
                {t('equipment.addModifier')}
              </button>
            </div>
          )}
        </section>
      )}
      
      {/* 总词缀统计 */}
      <section className="panel">
        <h3 className="text-sm font-semibold text-poe-gold mb-2">
          {t('modifier.title')} ({totalModifiers.length})
        </h3>
        {totalModifiers.length > 0 ? (
          <div className="text-xs text-gray-400 space-y-0.5 max-h-32 overflow-y-auto">
            {totalModifiers.map((mod, i) => (
              <div key={i}>
                {mod.type === 'BASE' ? '+' : ''}{mod.value}
                {mod.type !== 'BASE' ? '%' : ''} {mod.name}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-600 text-xs">{t('equipment.empty')}</p>
        )}
      </section>
    </div>
  );
}































































