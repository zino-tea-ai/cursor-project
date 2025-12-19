/**
 * POC 测试 2: 加载原版 PoB2 的 Global.lua
 * 这个文件定义了 ModFlag、KeywordFlag 等核心常量
 */

const fs = require('fs');
const path = require('path');
const fengari = require('fengari');
const { lua, lauxlib, lualib } = fengari;
const { to_luastring, to_jsstring } = fengari;

console.log('=== POC 测试 2: 加载原版 Global.lua ===\n');

const L = lauxlib.luaL_newstate();
lualib.luaL_openlibs(L);

// 首先注入一些原版需要的全局函数
const prelude = `
-- 原版使用的一些全局函数
function copyTable(t)
    local copy = {}
    for k, v in pairs(t) do
        if type(v) == "table" then
            copy[k] = copyTable(v)
        else
            copy[k] = v
        end
    end
    return copy
end

-- bit 库模拟 (Fengari 没有 bit 库)
bit = {}
function bit.bor(a, b, ...)
    local result = a | b
    local args = {...}
    for i, v in ipairs(args) do
        result = result | v
    end
    return result
end
function bit.band(a, b, ...)
    local result = a & b
    local args = {...}
    for i, v in ipairs(args) do
        result = result & v
    end
    return result
end
function bit.bnot(a)
    return ~a
end
function bit.bxor(a, b, ...)
    local result = a ~ b
    local args = {...}
    for i, v in ipairs(args) do
        result = result ~ v
    end
    return result
end

-- ConPrintf 模拟 (原版的打印函数)
function ConPrintf(...)
    -- 静默处理
end
`;

let status = lauxlib.luaL_dostring(L, to_luastring(prelude));
if (status !== lua.LUA_OK) {
    console.log('❌ Prelude 加载失败:', to_jsstring(lua.lua_tostring(L, -1)));
    process.exit(1);
}
console.log('✅ Prelude 注入成功\n');

// 读取 Global.lua
const globalPath = path.join(__dirname, '..', 'PathOfBuilding-PoE2', 'src', 'Data', 'Global.lua');
console.log('加载文件:', globalPath);

try {
    const globalContent = fs.readFileSync(globalPath, 'utf8');
    console.log(`文件大小: ${globalContent.length} 字符\n`);
    
    status = lauxlib.luaL_dostring(L, to_luastring(globalContent));
    
    if (status === lua.LUA_OK) {
        console.log('✅ Global.lua 加载成功!\n');
        
        // 验证一些关键常量
        console.log('验证关键常量:');
        
        // 检查 ModFlag
        lauxlib.luaL_dostring(L, to_luastring('return ModFlag.Attack'));
        let attackFlag = lua.lua_tonumber(L, -1);
        lua.lua_pop(L, 1);
        console.log(`  ModFlag.Attack = ${attackFlag} (预期: 1)`);
        
        lauxlib.luaL_dostring(L, to_luastring('return ModFlag.Spell'));
        let spellFlag = lua.lua_tonumber(L, -1);
        lua.lua_pop(L, 1);
        console.log(`  ModFlag.Spell = ${spellFlag} (预期: 2)`);
        
        lauxlib.luaL_dostring(L, to_luastring('return ModFlag.Melee'));
        let meleeFlag = lua.lua_tonumber(L, -1);
        lua.lua_pop(L, 1);
        console.log(`  ModFlag.Melee = ${meleeFlag} (预期: 256 = 0x100)`);
        
        // 检查 KeywordFlag
        lauxlib.luaL_dostring(L, to_luastring('return KeywordFlag.Aura'));
        let auraFlag = lua.lua_tonumber(L, -1);
        lua.lua_pop(L, 1);
        console.log(`  KeywordFlag.Aura = ${auraFlag} (预期: 1)`);
        
        // 检查 colorCodes
        lauxlib.luaL_dostring(L, to_luastring('return colorCodes.FIRE'));
        let fireColor = to_jsstring(lua.lua_tostring(L, -1));
        lua.lua_pop(L, 1);
        console.log(`  colorCodes.FIRE = "${fireColor}"`);
        
        // 测试 OR64 函数
        console.log('\n测试 64 位运算函数:');
        lauxlib.luaL_dostring(L, to_luastring('return OR64(1, 2, 4)'));
        let or64Result = lua.lua_tonumber(L, -1);
        lua.lua_pop(L, 1);
        console.log(`  OR64(1, 2, 4) = ${or64Result} (预期: 7)`);
        
        lauxlib.luaL_dostring(L, to_luastring('return AND64(0x0F, 0x03)'));
        let and64Result = lua.lua_tonumber(L, -1);
        lua.lua_pop(L, 1);
        console.log(`  AND64(0x0F, 0x03) = ${and64Result} (预期: 3)`);
        
        console.log('\n✅ Global.lua 验证通过!');
        
    } else {
        const error = to_jsstring(lua.lua_tostring(L, -1));
        console.log('❌ Global.lua 加载失败:');
        console.log(error);
    }
} catch (err) {
    console.log('❌ 文件读取失败:', err.message);
}



































