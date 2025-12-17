import { useState } from 'react';
import { useBuildStore, PRESET_SKILLS, PRESET_MODIFIERS } from '../store/buildStore';

export function DamagePanel() {
  const { 
    activeSkill, 
    setActiveSkill, 
    modifiers, 
    addModifier, 
    removeModifier,
    clearModifiers,
    damageResult,
    engineReady
  } = useBuildStore();

  const [selectedPresetMod, setSelectedPresetMod] = useState<number>(0);
  const [customModValue, setCustomModValue] = useState<number>(50);

  const handleAddModifier = () => {
    const preset = PRESET_MODIFIERS[selectedPresetMod];
    addModifier({
      ...preset,
      value: customModValue
    });
  };

  return (
    <div className="flex-1 p-4 overflow-auto">
      <div className="max-w-4xl mx-auto space-y-4">
        {/* 引擎状态 */}
        {!engineReady && (
          <div className="panel bg-yellow-900/20 border-yellow-600">
            <p className="text-yellow-400">⏳ 正在初始化计算引擎...</p>
          </div>
        )}

        {/* 技能选择 */}
        <div className="panel">
          <h2 className="text-lg font-semibold text-poe-gold mb-4">技能选择</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {PRESET_SKILLS.map(skill => (
              <button
                key={skill.id}
                onClick={() => setActiveSkill(skill)}
                className={`p-3 rounded border transition-all ${
                  activeSkill?.id === skill.id
                    ? 'bg-poe-gold/20 border-poe-gold'
                    : 'bg-poe-bg border-poe-border hover:border-gray-500'
                }`}
              >
                <div className={`font-medium ${getDamageTypeColor(skill.damageType)}`}>
                  {skill.nameZh || skill.name}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {skill.name}
                </div>
                <div className="text-xs text-gray-400 mt-2">
                  {skill.minDamage}-{skill.maxDamage} 伤害
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* 当前技能详情 */}
        {activeSkill && (
          <div className="panel">
            <h2 className="text-lg font-semibold text-poe-gold mb-4">
              {activeSkill.nameZh || activeSkill.name} 详情
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <InfoCard 
                label="基础伤害" 
                value={`${activeSkill.minDamage} - ${activeSkill.maxDamage}`}
                color={getDamageTypeColor(activeSkill.damageType)}
              />
              <InfoCard 
                label="伤害类型" 
                value={activeSkill.damageType}
                color={getDamageTypeColor(activeSkill.damageType)}
              />
              <InfoCard 
                label="暴击率" 
                value={`${activeSkill.critChance}%`}
              />
              <InfoCard 
                label="施法时间" 
                value={`${activeSkill.castTime}s`}
              />
            </div>
          </div>
        )}

        {/* 修改器管理 */}
        <div className="panel">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-poe-gold">修改器 (Modifiers)</h2>
            <button 
              onClick={clearModifiers}
              className="text-sm text-red-400 hover:text-red-300"
            >
              清空全部
            </button>
          </div>

          {/* 添加修改器 */}
          <div className="flex gap-2 mb-4">
            <select
              value={selectedPresetMod}
              onChange={(e) => setSelectedPresetMod(Number(e.target.value))}
              className="input-field flex-1"
            >
              {PRESET_MODIFIERS.map((mod, i) => (
                <option key={i} value={i}>
                  {mod.type === 'INC' ? '增加' : mod.type === 'MORE' ? '更多' : '基础'} {mod.name}
                </option>
              ))}
            </select>
            <input
              type="number"
              value={customModValue}
              onChange={(e) => setCustomModValue(Number(e.target.value))}
              className="input-field w-24"
              placeholder="数值"
            />
            <button onClick={handleAddModifier} className="btn-primary">
              添加
            </button>
          </div>

          {/* 已添加的修改器 */}
          <div className="space-y-2">
            {modifiers.length === 0 ? (
              <p className="text-gray-500 text-sm py-4 text-center">
                还没有添加任何修改器
              </p>
            ) : (
              modifiers.map((mod, index) => (
                <div 
                  key={index}
                  className="flex items-center justify-between bg-poe-bg p-2 rounded border border-poe-border"
                >
                  <span className="text-sm">
                    <span className={getModTypeColor(mod.type)}>
                      {mod.type === 'INC' ? '+' : mod.type === 'MORE' ? '×' : ''}
                      {mod.value}%
                    </span>
                    {' '}
                    <span className="text-gray-400">
                      {mod.type === 'INC' ? '增加' : mod.type === 'MORE' ? '更多' : ''} {mod.name}
                    </span>
                  </span>
                  <button
                    onClick={() => removeModifier(index)}
                    className="text-red-400 hover:text-red-300 text-sm px-2"
                  >
                    ✕
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* 计算结果详情 */}
        {damageResult && (
          <div className="panel">
            <h2 className="text-lg font-semibold text-poe-gold mb-4">计算结果详情</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <h3 className="text-sm font-medium text-gray-400">伤害计算</h3>
                <div className="bg-poe-bg p-3 rounded text-sm space-y-1 font-mono">
                  <div>基础伤害: {damageResult.breakdown.baseDamage.min.toFixed(0)} - {damageResult.breakdown.baseDamage.max.toFixed(0)}</div>
                  <div>增加倍率: ×{damageResult.breakdown.increasedMultiplier.toFixed(2)}</div>
                  <div>更多倍率: ×{(damageResult.breakdown.finalMultiplier / damageResult.breakdown.increasedMultiplier).toFixed(2)}</div>
                  <div className="border-t border-poe-border pt-1 mt-1">
                    最终倍率: ×{damageResult.breakdown.finalMultiplier.toFixed(2)}
                  </div>
                </div>
              </div>
              <div className="space-y-2">
                <h3 className="text-sm font-medium text-gray-400">DPS 计算</h3>
                <div className="bg-poe-bg p-3 rounded text-sm space-y-1 font-mono">
                  <div>平均伤害: {damageResult.averageDamage.toFixed(1)}</div>
                  <div>暴击加成: ×{(1 + (damageResult.critChance / 100) * (damageResult.critMultiplier / 100 - 1)).toFixed(3)}</div>
                  <div>攻击速度: {damageResult.attackSpeed.toFixed(2)}/s</div>
                  <div className="border-t border-poe-border pt-1 mt-1 text-poe-gold text-lg">
                    DPS: {damageResult.dps.toFixed(1)}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

interface InfoCardProps {
  label: string;
  value: string;
  color?: string;
}

function InfoCard({ label, value, color = 'text-gray-200' }: InfoCardProps) {
  return (
    <div className="bg-poe-bg p-3 rounded border border-poe-border">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className={`font-medium ${color}`}>{value}</div>
    </div>
  );
}

function getDamageTypeColor(type: string): string {
  const colors: Record<string, string> = {
    Physical: 'text-poe-physical',
    Fire: 'text-poe-fire',
    Cold: 'text-poe-cold',
    Lightning: 'text-poe-lightning',
    Chaos: 'text-poe-chaos',
  };
  return colors[type] || 'text-gray-200';
}

function getModTypeColor(type: string): string {
  switch (type) {
    case 'INC': return 'text-blue-400';
    case 'MORE': return 'text-green-400';
    case 'BASE': return 'text-yellow-400';
    default: return 'text-gray-400';
  }
}











