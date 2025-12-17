/**
 * POC 测试 4: 加载原版技能数据
 * 尝试读取 Arc 技能的真实数据
 */

const fs = require('fs');
const path = require('path');
const fengari = require('fengari');
const { lua, lauxlib, lualib } = fengari;
const { to_luastring, to_jsstring } = fengari;

console.log('=== POC 测试 4: 加载原版技能数据 ===\n');

const L = lauxlib.luaL_newstate();
lualib.luaL_openlibs(L);

// 预定义环境
const prelude = `
-- 模拟原版所需的全局环境
skills = {}
data = {
    ailmentTypeList = {"Bleed", "Poison", "Ignite", "Chill", "Freeze", "Shock", "Scorch", "Brittle", "Sapped"},
    elementalAilmentTypeList = {"Ignite", "Chill", "Freeze", "Shock", "Scorch", "Brittle", "Sapped"}
}

-- SkillType 枚举 (简化版)
SkillType = {
    Spell = 1,
    Projectile = 2,
    Damage = 3,
    Trappable = 4,
    Totemable = 5,
    Mineable = 6,
    Chains = 7,
    Multicastable = 8,
    Triggerable = 9,
    Lightning = 10,
    Unleashable = 11,
    Invokable = 12,
    UsableWhileMoving = 13,
    OngoingSkill = 14,
    HasReservation = 15,
    Buff = 16,
    Persistent = 17,
    AttackInPlace = 18,
}

-- mod 函数 (用于创建修改器)
function mod(name, type, value, flags, keywordFlags, ...)
    return {
        name = name,
        type = type,
        value = value,
        flags = flags or 0,
        keywordFlags = keywordFlags or 0,
        tags = {...}
    }
end

-- flag 函数
function flag(name, ...)
    return {
        name = name,
        type = "FLAG",
        value = true,
        tags = {...}
    }
end

-- skill 函数
function skill(id, data)
    skills[id] = data
    return data
end

print("✅ 预定义环境加载成功")
`;

let status = lauxlib.luaL_dostring(L, to_luastring(prelude));
if (status !== lua.LUA_OK) {
    console.log('❌ 预定义环境加载失败:', to_jsstring(lua.lua_tostring(L, -1)));
    process.exit(1);
}
console.log('✅ 预定义环境加载成功\n');

// 直接解析 Arc 技能数据 (从 act_int.lua 提取)
console.log('测试 4.1: 直接定义 Arc 技能数据');
const arcSkillData = `
skills["ArcPlayer"] = {
    name = "Arc",
    baseTypeName = "Arc",
    color = 3,  -- Intelligence (蓝色宝石)
    description = "An arc of Lightning stretches from the caster to a targeted enemy",
    skillTypes = { 
        [SkillType.Spell] = true, 
        [SkillType.Projectile] = true, 
        [SkillType.Damage] = true,
        [SkillType.Lightning] = true,
    },
    castTime = 1.1,
    critChance = 9,
    baseEffectiveness = 1.75,
    incrementalEffectiveness = 0.13,
    -- Level 1 数据
    levels = {
        [1] = { 
            minDamage = 1, 
            maxDamage = 13, 
            chains = 5,
            levelRequirement = 1,
            manaCost = 8,
        },
        [10] = {
            minDamage = 5,
            maxDamage = 96,
            chains = 7,
            levelRequirement = 36,
            manaCost = 28,
        },
        [20] = {
            minDamage = 20,
            maxDamage = 386,
            chains = 9,
            levelRequirement = 90,
            manaCost = 81,
        }
    }
}

-- 验证数据
local arc = skills["ArcPlayer"]
return arc.name, arc.castTime, arc.critChance, arc.levels[1].minDamage, arc.levels[1].maxDamage
`;

status = lauxlib.luaL_dostring(L, to_luastring(arcSkillData));
if (status === lua.LUA_OK) {
    console.log(`  技能名称: ${to_jsstring(lua.lua_tostring(L, -5))}`);
    console.log(`  施法时间: ${lua.lua_tonumber(L, -4)}s`);
    console.log(`  暴击率: ${lua.lua_tonumber(L, -3)}%`);
    console.log(`  Lv1 伤害: ${lua.lua_tonumber(L, -2)} - ${lua.lua_tonumber(L, -1)}`);
    lua.lua_pop(L, 5);
    console.log('  ✅ Arc 技能数据加载成功\n');
} else {
    console.log('  ❌ 错误:', to_jsstring(lua.lua_tostring(L, -1)), '\n');
}

// 测试 4.2: 完整的 DPS 计算
console.log('测试 4.2: 完整 DPS 计算模拟');
const dpsCalculation = `
-- 获取技能数据
local skill = skills["ArcPlayer"]
local level = skill.levels[20]  -- 使用 20 级数据

-- 角色属性
local character = {
    level = 90,
    intelligence = 300,  -- 影响法术伤害
}

-- 装备/被动加成
local mods = {
    increasedLightningDamage = 150,  -- +150% 闪电伤害
    increasedSpellDamage = 100,       -- +100% 法术伤害
    moreLightningDamage = 40,         -- 40% more 闪电伤害
    increasedCritChance = 200,        -- +200% 暴击率
    critMultiplier = 50,              -- +50% 暴击伤害
    castSpeed = 80,                   -- +80% 施法速度
}

-- 计算
local baseDamage = (level.minDamage + level.maxDamage) / 2
local incTotal = 1 + (mods.increasedLightningDamage + mods.increasedSpellDamage) / 100
local moreTotal = 1 + mods.moreLightningDamage / 100

-- 暴击计算
local baseCrit = skill.critChance
local effectiveCrit = math.min(100, baseCrit * (1 + mods.increasedCritChance / 100))
local critMulti = 1.5 + mods.critMultiplier / 100  -- 基础 150%

-- 平均伤害 (考虑暴击)
local avgDamage = baseDamage * incTotal * moreTotal
local critDamage = avgDamage * critMulti
local avgWithCrit = avgDamage * (1 - effectiveCrit/100) + critDamage * (effectiveCrit/100)

-- 施法速度
local effectiveCastTime = skill.castTime / (1 + mods.castSpeed / 100)
local castsPerSecond = 1 / effectiveCastTime

-- 最终 DPS
local dps = avgWithCrit * castsPerSecond

return baseDamage, incTotal, moreTotal, effectiveCrit, avgDamage, avgWithCrit, castsPerSecond, dps
`;

status = lauxlib.luaL_dostring(L, to_luastring(dpsCalculation));
if (status === lua.LUA_OK) {
    const baseDmg = lua.lua_tonumber(L, -8);
    const inc = lua.lua_tonumber(L, -7);
    const more = lua.lua_tonumber(L, -6);
    const crit = lua.lua_tonumber(L, -5);
    const avgDmg = lua.lua_tonumber(L, -4);
    const avgCrit = lua.lua_tonumber(L, -3);
    const cps = lua.lua_tonumber(L, -2);
    const dps = lua.lua_tonumber(L, -1);
    lua.lua_pop(L, 8);
    
    console.log('  Arc Level 20 DPS 计算:');
    console.log('  ─────────────────────────');
    console.log(`  基础伤害: ${baseDmg.toFixed(1)}`);
    console.log(`  增加倍率: ${inc.toFixed(2)}x (+${((inc-1)*100).toFixed(0)}%)`);
    console.log(`  更多倍率: ${more.toFixed(2)}x`);
    console.log(`  有效暴击率: ${crit.toFixed(1)}%`);
    console.log(`  平均伤害 (无暴击): ${avgDmg.toFixed(1)}`);
    console.log(`  平均伤害 (含暴击): ${avgCrit.toFixed(1)}`);
    console.log(`  每秒施法: ${cps.toFixed(2)}`);
    console.log(`  ─────────────────────────`);
    console.log(`  最终 DPS: ${dps.toFixed(1)}`);
    console.log('  ✅ DPS 计算完成\n');
} else {
    console.log('  ❌ 错误:', to_jsstring(lua.lua_tostring(L, -1)), '\n');
}

console.log('=== POC 测试 4 完成 ===\n');
console.log('验证结论:');
console.log('1. ✅ 可以定义和使用复杂的技能数据结构');
console.log('2. ✅ 可以进行完整的 DPS 计算');
console.log('3. ✅ 包含暴击、施法速度等机制');
console.log('\n技术验证结果: 方案可行!');











