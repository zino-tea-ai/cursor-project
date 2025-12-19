/**
 * POC 测试 1: Fengari 基本功能测试
 * 验证 Fengari 能否正常运行 Lua 代码
 */

const fengari = require('fengari');
const { lua, lauxlib, lualib } = fengari;
const { to_luastring, to_jsstring } = fengari;

console.log('=== POC 测试 1: Fengari 基本功能 ===\n');

// 创建 Lua 状态机
const L = lauxlib.luaL_newstate();
lualib.luaL_openlibs(L);

// 测试 1: 简单的 Lua 计算
console.log('测试 1.1: 简单数学计算');
let code = `
    local a = 100
    local b = 50
    local inc = 1 + (a / 100)  -- 1 + 100% = 2
    local more = 1 + (b / 100) -- 1 + 50% = 1.5
    local base = 1000
    local result = base * inc * more
    return result
`;

let status = lauxlib.luaL_dostring(L, to_luastring(code));
if (status === lua.LUA_OK) {
    let result = lua.lua_tonumber(L, -1);
    console.log(`  基础伤害: 1000`);
    console.log(`  增加 100%: x2`);
    console.log(`  更多 50%: x1.5`);
    console.log(`  计算结果: ${result}`);
    console.log(`  预期结果: 3000`);
    console.log(`  ✅ 测试通过: ${result === 3000}\n`);
} else {
    console.log(`  ❌ 错误: ${to_jsstring(lua.lua_tostring(L, -1))}\n`);
}
lua.lua_pop(L, 1);

// 测试 2: 表操作
console.log('测试 1.2: Lua 表操作');
code = `
    local mods = {}
    mods["PhysicalDamage"] = 100
    mods["FireDamage"] = 50
    mods["ColdDamage"] = 30
    
    local total = 0
    for k, v in pairs(mods) do
        total = total + v
    end
    return total
`;

status = lauxlib.luaL_dostring(L, to_luastring(code));
if (status === lua.LUA_OK) {
    let result = lua.lua_tonumber(L, -1);
    console.log(`  物理伤害: 100, 火焰: 50, 冰霜: 30`);
    console.log(`  总计: ${result}`);
    console.log(`  ✅ 测试通过: ${result === 180}\n`);
} else {
    console.log(`  ❌ 错误: ${to_jsstring(lua.lua_tostring(L, -1))}\n`);
}
lua.lua_pop(L, 1);

// 测试 3: 64位位运算 (这是原版的关键部分)
console.log('测试 1.3: 位运算 (Lua 5.3 bit32)');
code = `
    -- 检查是否有 bit32 库
    if bit32 then
        local a = bit32.bor(0x01, 0x02)  -- 1 | 2 = 3
        local b = bit32.band(0x0F, 0x03) -- 15 & 3 = 3
        return a, b
    else
        return -1, -1
    end
`;

status = lauxlib.luaL_dostring(L, to_luastring(code));
if (status === lua.LUA_OK) {
    let a = lua.lua_tonumber(L, -2);
    let b = lua.lua_tonumber(L, -1);
    if (a === -1) {
        console.log(`  ⚠️ bit32 库不可用，需要自定义实现`);
    } else {
        console.log(`  bor(0x01, 0x02) = ${a} (预期: 3)`);
        console.log(`  band(0x0F, 0x03) = ${b} (预期: 3)`);
        console.log(`  ✅ bit32 可用\n`);
    }
} else {
    console.log(`  ❌ 错误: ${to_jsstring(lua.lua_tostring(L, -1))}\n`);
}
lua.lua_pop(L, 2);

// 测试 4: 类模拟 (PoB 使用 newClass)
console.log('测试 1.4: 类/元表模拟');
code = `
    -- 简单的类实现
    local function newClass(name, constructor)
        local class = {}
        class.__index = class
        class.new = function(...)
            local self = setmetatable({}, class)
            if constructor then
                constructor(self, ...)
            end
            return self
        end
        return class
    end
    
    -- 创建一个简单的 ModDB 类
    local ModDB = newClass("ModDB", function(self)
        self.mods = {}
    end)
    
    function ModDB:AddMod(name, value)
        self.mods[name] = (self.mods[name] or 0) + value
    end
    
    function ModDB:Sum(name)
        return self.mods[name] or 0
    end
    
    -- 测试
    local db = ModDB.new()
    db:AddMod("PhysicalDamage", 100)
    db:AddMod("PhysicalDamage", 50)
    return db:Sum("PhysicalDamage")
`;

status = lauxlib.luaL_dostring(L, to_luastring(code));
if (status === lua.LUA_OK) {
    let result = lua.lua_tonumber(L, -1);
    console.log(`  创建 ModDB 类`);
    console.log(`  添加 PhysicalDamage: 100 + 50`);
    console.log(`  Sum 结果: ${result}`);
    console.log(`  ✅ 测试通过: ${result === 150}\n`);
} else {
    console.log(`  ❌ 错误: ${to_jsstring(lua.lua_tostring(L, -1))}\n`);
}
lua.lua_pop(L, 1);

console.log('=== 基础测试完成 ===');
console.log('如果以上测试都通过，说明 Fengari 基本功能正常。');
console.log('下一步: 尝试加载原版 PoB2 的 Lua 文件。');



































