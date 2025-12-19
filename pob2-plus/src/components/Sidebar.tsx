import { useBuildStore } from '../store/buildStore';
import { useTreeStore } from '../store/treeStore';
import { useSkillStore } from '../store/skillStore';
import { useEquipmentStore } from '../store/equipmentStore';
import { useI18nStore } from '../store/i18nStore';

export function Sidebar() {
  const { t, language } = useI18nStore();
  const { 
    characterName, 
    characterLevel, 
    characterClass,
    setCharacterName,
    setCharacterLevel,
    setCharacterClass,
    damageResult,
    modifiers
  } = useBuildStore();

  const { allocatedNodes, getAllocatedModifiers } = useTreeStore();
  const { skillSetup, getAllModifiers: getSkillModifiers } = useSkillStore();
  const { getAllModifiers: getEquipmentModifiers } = useEquipmentStore();
  
  const passiveModifiers = getAllocatedModifiers();
  const skillModifiers = getSkillModifiers();
  const equipmentModifiers = getEquipmentModifiers();
  const totalModifiers = modifiers.length + passiveModifiers.length + skillModifiers.length + equipmentModifiers.length;

  const classes = ['Sorceress', 'Witch', 'Monk', 'Ranger', 'Warrior', 'Mercenary'];

  return (
    <aside className="w-64 bg-poe-panel border-r border-poe-border p-4 flex flex-col gap-4 overflow-y-auto">
      {/* 角色信息 */}
      <div className="panel">
        <h2 className="text-sm font-semibold text-poe-gold mb-3">{t('character.name')}</h2>
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-gray-400 mb-1">{t('character.name')}</label>
            <input
              type="text"
              value={characterName}
              onChange={(e) => setCharacterName(e.target.value)}
              className="input-field w-full text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">{t('character.class')}</label>
            <select
              value={characterClass}
              onChange={(e) => setCharacterClass(e.target.value)}
              className="input-field w-full text-sm"
            >
              {classes.map(cls => (
                <option key={cls} value={cls}>{cls}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">{t('character.level')}</label>
            <input
              type="number"
              min={1}
              max={100}
              value={characterLevel}
              onChange={(e) => setCharacterLevel(Number(e.target.value))}
              className="input-field w-full text-sm"
            />
          </div>
        </div>
      </div>

      {/* 当前技能 */}
      {skillSetup.activeSkill && (
        <div className="panel">
          <h2 className="text-sm font-semibold text-poe-gold mb-2">{t('skill.activeSkill')}</h2>
          <div className="text-sm text-white">
            {language === 'zh' ? skillSetup.activeSkill.nameZh : skillSetup.activeSkill.name}
          </div>
          <div className="text-xs text-gray-500">
            Lv.{skillSetup.activeSkillLevel} + {skillSetup.supportGems.length} {t('skill.linkedSupports')}
          </div>
        </div>
      )}

      {/* 被动点数 */}
      <div className="panel">
        <h2 className="text-sm font-semibold text-poe-gold mb-3">{t('tree.title')}</h2>
        <div className="space-y-2 text-sm">
          <StatRow 
            label={t('tree.allocated')} 
            value={`${allocatedNodes.size} ${t('tree.points')}`} 
          />
          <StatRow 
            label={t('tree.available')} 
            value={`${Math.max(0, characterLevel - allocatedNodes.size)} ${t('tree.points')}`} 
          />
        </div>
      </div>

      {/* 修改器统计 */}
      <div className="panel">
        <h2 className="text-sm font-semibold text-poe-gold mb-2">{t('modifier.title')}</h2>
        <div className="space-y-1 text-xs">
          <div className="flex justify-between text-gray-400">
            <span>{t('modifier.passive')}</span>
            <span>{passiveModifiers.length}</span>
          </div>
          <div className="flex justify-between text-gray-400">
            <span>{t('modifier.support')}</span>
            <span>{skillModifiers.length}</span>
          </div>
          <div className="flex justify-between text-gray-400">
            <span>{t('modifier.equipment')}</span>
            <span>{equipmentModifiers.length}</span>
          </div>
          <div className="flex justify-between text-white font-medium pt-1 border-t border-poe-border">
            <span>Total</span>
            <span>{totalModifiers}</span>
          </div>
        </div>
      </div>

      {/* 伤害统计 */}
      <div className="panel flex-1">
        <h2 className="text-sm font-semibold text-poe-gold mb-3">{t('damage.title')}</h2>
        {damageResult ? (
          <div className="space-y-2 text-sm">
            <StatRow label={t('damage.dps')} value={formatNumber(damageResult.dps)} highlight />
            <StatRow 
              label={t('damage.average')} 
              value={formatNumber(damageResult.averageDamage)} 
            />
            <StatRow 
              label={`${t('damage.min')} - ${t('damage.max')}`} 
              value={`${formatNumber(damageResult.minDamage)} - ${formatNumber(damageResult.maxDamage)}`} 
            />
            <div className="border-t border-poe-border my-2" />
            <StatRow 
              label={t('damage.crit')} 
              value={`${damageResult.critChance.toFixed(1)}%`} 
            />
            <StatRow 
              label={t('damage.critMult')} 
              value={`${damageResult.critMultiplier.toFixed(0)}%`} 
            />
            <StatRow 
              label={t('damage.speed')} 
              value={`${damageResult.attackSpeed.toFixed(2)}/s`} 
            />
          </div>
        ) : (
          <p className="text-gray-500 text-sm">{t('damage.selectSkill')}</p>
        )}
      </div>
    </aside>
  );
}

interface StatRowProps {
  label: string;
  value: string;
  highlight?: boolean;
}

function StatRow({ label, value, highlight }: StatRowProps) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-gray-400">{label}</span>
      <span className={`stat-value ${highlight ? 'text-poe-gold text-lg font-bold' : 'text-gray-200'}`}>
        {value}
      </span>
    </div>
  );
}

function formatNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(2) + 'M';
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  return num.toFixed(1);
}



































