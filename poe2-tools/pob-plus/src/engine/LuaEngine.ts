/**
 * Lua 引擎封装
 * 使用 Fengari-Web 在浏览器中运行 Lua 代码
 */

import { lua, lauxlib, lualib, to_luastring, to_jsstring } from 'fengari-web';

export class LuaEngine {
  private L: any;
  private initialized: boolean = false;

  constructor() {
    this.L = lauxlib.luaL_newstate();
    lualib.luaL_openlibs(this.L);
  }

  /**
   * 初始化引擎，加载核心定义
   */
  async initialize(): Promise<void> {
    if (this.initialized) return;

    // 加载核心定义
    const coreCode = this.getCoreDefinitions();
    const status = lauxlib.luaL_dostring(this.L, to_luastring(coreCode));
    
    if (status !== lua.LUA_OK) {
      const error = to_jsstring(lua.lua_tostring(this.L, -1));
      throw new Error(`Lua 初始化失败: ${error}`);
    }

    this.initialized = true;
    console.log('✅ Lua 引擎初始化成功');
  }

  /**
   * 执行 Lua 代码
   */
  execute(code: string): any {
    const status = lauxlib.luaL_dostring(this.L, to_luastring(code));
    
    if (status !== lua.LUA_OK) {
      const error = to_jsstring(lua.lua_tostring(this.L, -1));
      lua.lua_pop(this.L, 1);
      throw new Error(`Lua 执行错误: ${error}`);
    }

    // 获取返回值
    const result = this.getReturnValue();
    return result;
  }

  /**
   * 调用 Lua 函数
   */
  callFunction(funcName: string, ...args: any[]): any {
    // 获取函数
    lua.lua_getglobal(this.L, to_luastring(funcName));
    
    // 压入参数
    for (const arg of args) {
      this.pushValue(arg);
    }

    // 调用函数
    const status = lua.lua_pcall(this.L, args.length, 1, 0);
    
    if (status !== lua.LUA_OK) {
      const error = to_jsstring(lua.lua_tostring(this.L, -1));
      lua.lua_pop(this.L, 1);
      throw new Error(`调用 ${funcName} 失败: ${error}`);
    }

    return this.getReturnValue();
  }

  /**
   * 设置全局变量
   */
  setGlobal(name: string, value: any): void {
    this.pushValue(value);
    lua.lua_setglobal(this.L, to_luastring(name));
  }

  /**
   * 获取全局变量
   */
  getGlobal(name: string): any {
    lua.lua_getglobal(this.L, to_luastring(name));
    const result = this.getReturnValue();
    return result;
  }

  private pushValue(value: any): void {
    if (value === null || value === undefined) {
      lua.lua_pushnil(this.L);
    } else if (typeof value === 'boolean') {
      lua.lua_pushboolean(this.L, value);
    } else if (typeof value === 'number') {
      lua.lua_pushnumber(this.L, value);
    } else if (typeof value === 'string') {
      lua.lua_pushstring(this.L, to_luastring(value));
    } else if (typeof value === 'object') {
      // 简单对象转换为 Lua 表
      lua.lua_newtable(this.L);
      for (const [k, v] of Object.entries(value)) {
        lua.lua_pushstring(this.L, to_luastring(k));
        this.pushValue(v);
        lua.lua_settable(this.L, -3);
      }
    }
  }

  private getReturnValue(): any {
    const type = lua.lua_type(this.L, -1);
    let result: any;

    switch (type) {
      case lua.LUA_TNIL:
        result = null;
        break;
      case lua.LUA_TBOOLEAN:
        result = lua.lua_toboolean(this.L, -1);
        break;
      case lua.LUA_TNUMBER:
        result = lua.lua_tonumber(this.L, -1);
        break;
      case lua.LUA_TSTRING:
        result = to_jsstring(lua.lua_tostring(this.L, -1));
        break;
      case lua.LUA_TTABLE:
        result = this.tableToObject();
        break;
      default:
        result = null;
    }

    lua.lua_pop(this.L, 1);
    return result;
  }

  private tableToObject(): Record<string, any> {
    const result: Record<string, any> = {};
    lua.lua_pushnil(this.L);
    
    while (lua.lua_next(this.L, -2) !== 0) {
      const keyType = lua.lua_type(this.L, -2);
      let key: string;
      
      if (keyType === lua.LUA_TSTRING) {
        key = to_jsstring(lua.lua_tostring(this.L, -2));
      } else if (keyType === lua.LUA_TNUMBER) {
        key = String(lua.lua_tonumber(this.L, -2));
      } else {
        lua.lua_pop(this.L, 1);
        continue;
      }

      const valueType = lua.lua_type(this.L, -1);
      let value: any;

      switch (valueType) {
        case lua.LUA_TBOOLEAN:
          value = lua.lua_toboolean(this.L, -1);
          break;
        case lua.LUA_TNUMBER:
          value = lua.lua_tonumber(this.L, -1);
          break;
        case lua.LUA_TSTRING:
          value = to_jsstring(lua.lua_tostring(this.L, -1));
          break;
        default:
          value = null;
      }

      result[key] = value;
      lua.lua_pop(this.L, 1);
    }

    return result;
  }

  /**
   * 核心 Lua 定义（移植自原版）
   */
  private getCoreDefinitions(): string {
    return `
-- PoB2 Plus 核心定义
-- 移植自 Path of Building 2

-- 64 位位运算
function OR64(a, b)
    if not a then return b or 0 end
    if not b then return a or 0 end
    return a | b
end

function AND64(a, b)
    if not a then return 0 end
    if not b then return 0 end
    return a & b
end

function NOT64(a)
    if not a then return 0 end
    return ~a & 0x1FFFFFFFFFFFFF
end

-- ModFlag 定义
ModFlag = {}
ModFlag.Attack = 0x0000000000000001
ModFlag.Spell = 0x0000000000000002
ModFlag.Hit = 0x0000000000000004
ModFlag.Dot = 0x0000000000000008
ModFlag.Cast = 0x0000000000000010
ModFlag.Melee = 0x0000000000000100
ModFlag.Area = 0x0000000000000200
ModFlag.Projectile = 0x0000000000000400
ModFlag.Ailment = 0x0000000000000800
ModFlag.Weapon = 0x0000000000002000

-- KeywordFlag 定义
KeywordFlag = {}
KeywordFlag.Aura = 0x00000001
KeywordFlag.Curse = 0x00000002
KeywordFlag.Physical = 0x00000010
KeywordFlag.Fire = 0x00000020
KeywordFlag.Cold = 0x00000040
KeywordFlag.Lightning = 0x00000080
KeywordFlag.Chaos = 0x00000100
KeywordFlag.Attack = 0x00010000
KeywordFlag.Spell = 0x00020000

-- 伤害类型列表
dmgTypeList = {"Physical", "Lightning", "Cold", "Fire", "Chaos"}

-- ModDB 类
local ModDBClass = {}
ModDBClass.__index = ModDBClass

function ModDBClass.new()
    local self = setmetatable({}, ModDBClass)
    self.mods = {}
    return self
end

function ModDBClass:AddMod(mod)
    local name = mod.name
    if not self.mods[name] then
        self.mods[name] = {}
    end
    table.insert(self.mods[name], mod)
end

function ModDBClass:Sum(modType, ...)
    local result = 0
    for i = 1, select('#', ...) do
        local modName = select(i, ...)
        local modList = self.mods[modName]
        if modList then
            for _, mod in ipairs(modList) do
                if mod.type == modType then
                    result = result + mod.value
                end
            end
        end
    end
    return result
end

function ModDBClass:More(...)
    local result = 1
    for i = 1, select('#', ...) do
        local modName = select(i, ...)
        local modList = self.mods[modName]
        if modList then
            for _, mod in ipairs(modList) do
                if mod.type == "MORE" then
                    result = result * (1 + mod.value / 100)
                end
            end
        end
    end
    return result
end

function ModDBClass:Clear()
    self.mods = {}
end

ModDB = ModDBClass

-- 伤害计算函数
function calculateDamage(skill, modDB, config)
    config = config or {}
    
    local baseDamageMin = skill.minDamage or 0
    local baseDamageMax = skill.maxDamage or 0
    local damageType = skill.damageType or "Physical"
    
    -- 获取增加和更多修正
    local incMods = {"Damage", damageType .. "Damage"}
    if skill.isSpell then
        table.insert(incMods, "SpellDamage")
    end
    if skill.isAttack then
        table.insert(incMods, "AttackDamage")
    end
    
    local incTotal = 1 + modDB:Sum("INC", table.unpack(incMods)) / 100
    local moreTotal = modDB:More(table.unpack(incMods))
    
    -- 暴击计算
    local baseCrit = skill.critChance or 5
    local critInc = modDB:Sum("INC", "CritChance", damageType .. "CritChance") or 0
    local effectiveCrit = math.min(100, baseCrit * (1 + critInc / 100))
    
    local baseCritMulti = 150
    local critMultiInc = modDB:Sum("BASE", "CritMultiplier") or 0
    local critMulti = (baseCritMulti + critMultiInc) / 100
    
    -- 计算伤害
    local minDamage = baseDamageMin * incTotal * moreTotal
    local maxDamage = baseDamageMax * incTotal * moreTotal
    local avgDamage = (minDamage + maxDamage) / 2
    
    -- 考虑暴击的平均伤害
    local nonCritDamage = avgDamage * (1 - effectiveCrit / 100)
    local critDamage = avgDamage * critMulti * (effectiveCrit / 100)
    local avgDamageWithCrit = nonCritDamage + critDamage
    
    -- 攻击/施法速度
    local baseSpeed = 1 / (skill.castTime or 1)
    local speedInc = modDB:Sum("INC", "Speed", "CastSpeed", "AttackSpeed") or 0
    local effectiveSpeed = baseSpeed * (1 + speedInc / 100)
    
    -- DPS
    local dps = avgDamageWithCrit * effectiveSpeed
    
    return {
        minDamage = minDamage,
        maxDamage = maxDamage,
        averageDamage = avgDamage,
        averageWithCrit = avgDamageWithCrit,
        dps = dps,
        critChance = effectiveCrit,
        critMultiplier = critMulti * 100,
        speed = effectiveSpeed,
        breakdown = {
            baseDamageMin = baseDamageMin,
            baseDamageMax = baseDamageMax,
            increased = incTotal,
            more = moreTotal
        }
    }
end

print("✅ PoB2 Plus Lua 核心加载完成")
`;
  }
}

// 单例
let engineInstance: LuaEngine | null = null;

export function getLuaEngine(): LuaEngine {
  if (!engineInstance) {
    engineInstance = new LuaEngine();
  }
  return engineInstance;
}































































