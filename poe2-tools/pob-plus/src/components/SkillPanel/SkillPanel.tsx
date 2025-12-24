/**
 * 技能配置面板
 */

import { useEffect } from 'react';
import { useSkillStore } from '../../store/skillStore';
import { useBuildStore } from '../../store/buildStore';
import { useI18nStore } from '../../store/i18nStore';
import { getCompatibleSupports } from '../../data/skills';

export function SkillPanel() {
  const { t, language } = useI18nStore();
  const {
    skillSetup,
    availableSkills,
    setActiveSkill,
    setSkillLevel,
    addSupportGem,
    removeSupportGem,
    setSupportGemLevel,
    getEffectiveStats,
    getTotalManaMultiplier
  } = useSkillStore();
  
  const { setActiveSkill: setBuildSkill, calculateDamage } = useBuildStore();
  
  // 当技能配置改变时，更新 buildStore 并重新计算
  useEffect(() => {
    if (skillSetup.activeSkill) {
      const stats = getEffectiveStats();
      setBuildSkill({
        id: skillSetup.activeSkill.id,
        name: skillSetup.activeSkill.name,
        nameZh: skillSetup.activeSkill.nameZh,
        damageType: skillSetup.activeSkill.damageType,
        minDamage: stats.minDamage,
        maxDamage: stats.maxDamage,
        critChance: stats.critChance,
        castTime: stats.castTime,
        isSpell: skillSetup.activeSkill.tags.includes('Spell'),
        isAttack: skillSetup.activeSkill.tags.includes('Attack')
      });
    }
    calculateDamage();
  }, [skillSetup, setBuildSkill, calculateDamage, getEffectiveStats]);
  
  const stats = getEffectiveStats();
  const manaMultiplier = getTotalManaMultiplier();
  const finalManaCost = Math.round(stats.manaCost * manaMultiplier);
  
  // 获取兼容的辅助宝石
  const compatibleSupports = skillSetup.activeSkill 
    ? getCompatibleSupports(skillSetup.activeSkill)
    : [];
  
  // 已添加的辅助宝石ID
  const addedGemIds = new Set(skillSetup.supportGems.map(sg => sg.gem.id));
  
  return (
    <div className="p-4 space-y-6 overflow-y-auto h-full">
      {/* 主动技能选择 */}
      <section className="panel">
        <h2 className="text-lg font-semibold text-poe-gold mb-4">
          {t('skill.activeSkill')}
        </h2>
        
        <div className="space-y-3">
          <select
            value={skillSetup.activeSkill?.id || ''}
            onChange={(e) => {
              const skill = availableSkills.find(s => s.id === e.target.value);
              setActiveSkill(skill || null);
            }}
            className="input-field w-full"
          >
            <option value="">{t('skill.selectSkill')}</option>
            {availableSkills.map(skill => (
              <option key={skill.id} value={skill.id}>
                {language === 'zh' ? skill.nameZh : skill.name}
              </option>
            ))}
          </select>
          
          {skillSetup.activeSkill && (
            <>
              <div className="flex items-center gap-4">
                <label className="text-sm text-gray-400">{t('skill.level')}:</label>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={skillSetup.activeSkillLevel}
                  onChange={(e) => setSkillLevel(parseInt(e.target.value) || 1)}
                  className="input-field w-20"
                />
              </div>
              
              <div className="text-sm text-gray-400">
                <p>{language === 'zh' 
                  ? skillSetup.activeSkill.descriptionZh 
                  : skillSetup.activeSkill.description}</p>
              </div>
              
              {/* 技能属性 */}
              <div className="grid grid-cols-2 gap-2 text-sm mt-3 pt-3 border-t border-poe-border">
                <div>
                  <span className="text-gray-500">{t('skill.damage')}:</span>
                  <span className="ml-2 text-white">
                    {stats.minDamage.toFixed(0)} - {stats.maxDamage.toFixed(0)}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">{t('skill.critChance')}:</span>
                  <span className="ml-2 text-white">{stats.critChance}%</span>
                </div>
                <div>
                  <span className="text-gray-500">{t('skill.castTime')}:</span>
                  <span className="ml-2 text-white">{stats.castTime}s</span>
                </div>
                <div>
                  <span className="text-gray-500">{t('skill.manaCost')}:</span>
                  <span className="ml-2 text-white">
                    {finalManaCost}
                    {manaMultiplier !== 1 && (
                      <span className="text-gray-500 text-xs ml-1">
                        ({(manaMultiplier * 100).toFixed(0)}%)
                      </span>
                    )}
                  </span>
                </div>
              </div>
              
              {/* 标签 */}
              <div className="flex flex-wrap gap-1 mt-2">
                {skillSetup.activeSkill.tags.map(tag => (
                  <span key={tag} className="px-2 py-0.5 text-xs bg-poe-bg rounded text-gray-400">
                    {tag}
                  </span>
                ))}
              </div>
            </>
          )}
        </div>
      </section>
      
      {/* 已链接的辅助宝石 */}
      <section className="panel">
        <h2 className="text-lg font-semibold text-poe-gold mb-4">
          {t('skill.linkedSupports')} ({skillSetup.supportGems.length}/6)
        </h2>
        
        {skillSetup.supportGems.length === 0 ? (
          <p className="text-gray-500 text-sm">{t('skill.noSupports')}</p>
        ) : (
          <div className="space-y-2">
            {skillSetup.supportGems.map(({ gem, level }) => (
              <div 
                key={gem.id} 
                className="flex items-center justify-between p-2 bg-poe-bg rounded"
              >
                <div className="flex-1">
                  <div className="text-sm font-medium text-blue-400">
                    {language === 'zh' ? gem.nameZh : gem.name}
                  </div>
                  <div className="text-xs text-gray-500">
                    {gem.modifiers.map(m => (
                      <span key={m.stat} className="mr-2">
                        {m.type === 'MORE' ? '×' : '+'}{m.value}% {m.stat}
                      </span>
                    ))}
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min={1}
                    max={20}
                    value={level}
                    onChange={(e) => setSupportGemLevel(gem.id, parseInt(e.target.value) || 1)}
                    className="input-field w-14 text-center text-sm"
                  />
                  <button
                    onClick={() => removeSupportGem(gem.id)}
                    className="text-red-400 hover:text-red-300 px-2"
                    title={t('common.remove')}
                  >
                    ✕
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
      
      {/* 可用辅助宝石 */}
      {skillSetup.activeSkill && compatibleSupports.length > 0 && (
        <section className="panel">
          <h2 className="text-lg font-semibold text-poe-gold mb-4">
            {t('skill.availableSupports')}
          </h2>
          
          <div className="grid grid-cols-2 gap-2">
            {compatibleSupports
              .filter(gem => !addedGemIds.has(gem.id))
              .map(gem => (
                <button
                  key={gem.id}
                  onClick={() => addSupportGem(gem)}
                  disabled={skillSetup.supportGems.length >= 6}
                  className="p-2 text-left bg-poe-bg hover:bg-poe-border rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <div className="text-sm text-blue-400">
                    {language === 'zh' ? gem.nameZh : gem.name}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {(gem.manaMultiplier * 100).toFixed(0)}% {t('skill.manaMult')}
                  </div>
                </button>
              ))}
          </div>
        </section>
      )}
    </div>
  );
}































































