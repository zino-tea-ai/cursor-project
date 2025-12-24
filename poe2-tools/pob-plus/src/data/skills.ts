/**
 * 技能数据库
 */

import type { ActiveSkill, SupportGem } from '../types/skills';

// 主动技能列表
export const ACTIVE_SKILLS: ActiveSkill[] = [
  {
    id: 'arc',
    name: 'Arc',
    nameZh: '电弧',
    description: 'An arc of lightning stretches from the caster to a targeted enemy.',
    descriptionZh: '从施法者向目标敌人释放一道闪电弧。',
    damageType: 'Lightning',
    tags: ['Spell', 'Projectile'],
    baseMinDamage: 1,
    baseMaxDamage: 13,
    baseCritChance: 9,
    baseCastTime: 1.1,
    baseManaCost: 8,
    levelScaling: { damagePerLevel: 3, manaCostPerLevel: 1 }
  },
  {
    id: 'fireball',
    name: 'Fireball',
    nameZh: '火球',
    description: 'Unleashes a ball of fire towards a target.',
    descriptionZh: '向目标释放一颗火球。',
    damageType: 'Fire',
    tags: ['Spell', 'Projectile', 'AoE'],
    baseMinDamage: 8,
    baseMaxDamage: 12,
    baseCritChance: 6,
    baseCastTime: 0.85,
    baseManaCost: 6,
    levelScaling: { damagePerLevel: 4, manaCostPerLevel: 1 }
  },
  {
    id: 'ice_spear',
    name: 'Ice Spear',
    nameZh: '冰矛',
    description: 'Launches shards of ice in rapid succession.',
    descriptionZh: '快速发射冰矛碎片。',
    damageType: 'Cold',
    tags: ['Spell', 'Projectile'],
    baseMinDamage: 5,
    baseMaxDamage: 15,
    baseCritChance: 7,
    baseCastTime: 0.75,
    baseManaCost: 7,
    levelScaling: { damagePerLevel: 3.5, manaCostPerLevel: 1 }
  },
  {
    id: 'heavy_strike',
    name: 'Heavy Strike',
    nameZh: '重击',
    description: 'A powerful melee attack.',
    descriptionZh: '强力的近战攻击。',
    damageType: 'Physical',
    tags: ['Attack', 'Melee'],
    baseMinDamage: 10,
    baseMaxDamage: 20,
    baseCritChance: 5,
    baseCastTime: 1.0,
    baseManaCost: 5,
    levelScaling: { damagePerLevel: 5, manaCostPerLevel: 0 }
  },
  {
    id: 'spark',
    name: 'Spark',
    nameZh: '电火花',
    description: 'Launches unpredictable sparks that move randomly.',
    descriptionZh: '释放不可预测的火花，随机移动。',
    damageType: 'Lightning',
    tags: ['Spell', 'Projectile', 'Duration'],
    baseMinDamage: 2,
    baseMaxDamage: 8,
    baseCritChance: 5,
    baseCastTime: 0.65,
    baseManaCost: 5,
    levelScaling: { damagePerLevel: 2.5, manaCostPerLevel: 1 }
  },
  {
    id: 'glacial_cascade',
    name: 'Glacial Cascade',
    nameZh: '冰川之刺',
    description: 'Icicles erupt from the ground in a series.',
    descriptionZh: '从地面连续爆发冰刺。',
    damageType: 'Cold',
    tags: ['Spell', 'AoE'],
    baseMinDamage: 15,
    baseMaxDamage: 25,
    baseCritChance: 6,
    baseCastTime: 0.8,
    baseManaCost: 12,
    levelScaling: { damagePerLevel: 6, manaCostPerLevel: 2 }
  },
  {
    id: 'cleave',
    name: 'Cleave',
    nameZh: '横扫',
    description: 'Swings your weapon in an arc.',
    descriptionZh: '以弧形挥动你的武器。',
    damageType: 'Physical',
    tags: ['Attack', 'Melee', 'AoE'],
    baseMinDamage: 8,
    baseMaxDamage: 15,
    baseCritChance: 5,
    baseCastTime: 0.9,
    baseManaCost: 6,
    levelScaling: { damagePerLevel: 4, manaCostPerLevel: 0 }
  },
  {
    id: 'essence_drain',
    name: 'Essence Drain',
    nameZh: '精华吸取',
    description: 'Fires a projectile that applies chaos damage over time.',
    descriptionZh: '发射一颗投射物，对敌人造成持续混沌伤害。',
    damageType: 'Chaos',
    tags: ['Spell', 'Projectile', 'Duration'],
    baseMinDamage: 10,
    baseMaxDamage: 18,
    baseCritChance: 5,
    baseCastTime: 0.7,
    baseManaCost: 9,
    levelScaling: { damagePerLevel: 4, manaCostPerLevel: 1 }
  }
];

// 辅助宝石列表
export const SUPPORT_GEMS: SupportGem[] = [
  {
    id: 'added_fire',
    name: 'Added Fire Damage',
    nameZh: '附加火焰伤害',
    description: 'Adds fire damage to attacks and spells.',
    descriptionZh: '为攻击和法术附加火焰伤害。',
    tags: ['Spell', 'Attack'],
    manaMultiplier: 1.3,
    modifiers: [
      { stat: 'AddedFireDamage', type: 'BASE', value: 25 }
    ]
  },
  {
    id: 'added_cold',
    name: 'Added Cold Damage',
    nameZh: '附加冰霜伤害',
    description: 'Adds cold damage to attacks and spells.',
    descriptionZh: '为攻击和法术附加冰霜伤害。',
    tags: ['Spell', 'Attack'],
    manaMultiplier: 1.3,
    modifiers: [
      { stat: 'AddedColdDamage', type: 'BASE', value: 25 }
    ]
  },
  {
    id: 'added_lightning',
    name: 'Added Lightning Damage',
    nameZh: '附加闪电伤害',
    description: 'Adds lightning damage to attacks and spells.',
    descriptionZh: '为攻击和法术附加闪电伤害。',
    tags: ['Spell', 'Attack'],
    manaMultiplier: 1.3,
    modifiers: [
      { stat: 'AddedLightningDamage', type: 'BASE', value: 25 }
    ]
  },
  {
    id: 'increased_critical_strikes',
    name: 'Increased Critical Strikes',
    nameZh: '增加暴击几率',
    description: 'Increases critical strike chance.',
    descriptionZh: '增加暴击几率。',
    tags: ['Spell', 'Attack'],
    manaMultiplier: 1.2,
    modifiers: [
      { stat: 'CritChance', type: 'INC', value: 100 }
    ]
  },
  {
    id: 'increased_critical_damage',
    name: 'Increased Critical Damage',
    nameZh: '增加暴击伤害',
    description: 'Increases critical strike multiplier.',
    descriptionZh: '增加暴击伤害倍率。',
    tags: ['Spell', 'Attack'],
    manaMultiplier: 1.3,
    modifiers: [
      { stat: 'CritMultiplier', type: 'BASE', value: 50 }
    ]
  },
  {
    id: 'faster_casting',
    name: 'Faster Casting',
    nameZh: '快速施法',
    description: 'Increases cast speed.',
    descriptionZh: '增加施法速度。',
    tags: ['Spell'],
    manaMultiplier: 1.15,
    modifiers: [
      { stat: 'CastSpeed', type: 'INC', value: 40 }
    ]
  },
  {
    id: 'faster_attacks',
    name: 'Faster Attacks',
    nameZh: '快速攻击',
    description: 'Increases attack speed.',
    descriptionZh: '增加攻击速度。',
    tags: ['Attack'],
    manaMultiplier: 1.15,
    modifiers: [
      { stat: 'AttackSpeed', type: 'INC', value: 40 }
    ]
  },
  {
    id: 'controlled_destruction',
    name: 'Controlled Destruction',
    nameZh: '受控毁灭',
    description: 'More spell damage, less critical strike chance.',
    descriptionZh: '更多法术伤害，更少暴击几率。',
    tags: ['Spell'],
    manaMultiplier: 1.4,
    modifiers: [
      { stat: 'SpellDamage', type: 'MORE', value: 40 },
      { stat: 'CritChance', type: 'INC', value: -50 }
    ]
  },
  {
    id: 'elemental_focus',
    name: 'Elemental Focus',
    nameZh: '元素集中',
    description: 'More elemental damage.',
    descriptionZh: '更多元素伤害。',
    tags: ['Spell', 'Attack'],
    manaMultiplier: 1.3,
    modifiers: [
      { stat: 'ElementalDamage', type: 'MORE', value: 35 }
    ]
  },
  {
    id: 'concentrated_effect',
    name: 'Concentrated Effect',
    nameZh: '集中效应',
    description: 'More area damage, less area of effect.',
    descriptionZh: '更多范围伤害，更小的影响范围。',
    tags: ['AoE'],
    manaMultiplier: 1.4,
    modifiers: [
      { stat: 'AreaDamage', type: 'MORE', value: 50 }
    ]
  },
  {
    id: 'spell_echo',
    name: 'Spell Echo',
    nameZh: '法术回响',
    description: 'Spells repeat an additional time.',
    descriptionZh: '法术额外重复一次。',
    tags: ['Spell'],
    manaMultiplier: 1.4,
    modifiers: [
      { stat: 'CastSpeed', type: 'MORE', value: 50 },
      { stat: 'SpellDamage', type: 'INC', value: -10 }
    ]
  },
  {
    id: 'melee_physical',
    name: 'Melee Physical Damage',
    nameZh: '近战物理伤害',
    description: 'More melee physical damage.',
    descriptionZh: '更多近战物理伤害。',
    tags: ['Attack', 'Melee'],
    manaMultiplier: 1.4,
    modifiers: [
      { stat: 'PhysicalDamage', type: 'MORE', value: 45 }
    ]
  }
];

// 根据 ID 获取技能
export function getSkillById(id: string): ActiveSkill | undefined {
  return ACTIVE_SKILLS.find(s => s.id === id);
}

// 根据 ID 获取辅助宝石
export function getSupportGemById(id: string): SupportGem | undefined {
  return SUPPORT_GEMS.find(g => g.id === id);
}

// 获取与技能标签兼容的辅助宝石
export function getCompatibleSupports(skill: ActiveSkill): SupportGem[] {
  return SUPPORT_GEMS.filter(gem => 
    gem.tags.some(tag => skill.tags.includes(tag))
  );
}































































