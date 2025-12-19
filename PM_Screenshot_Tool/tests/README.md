# PM Screenshot Tool 自动化测试框架

## 概述

这是一个全面的自动化测试框架，用于测试 PM Screenshot Tool 的各项功能。

## 安装依赖

```bash
pip install playwright requests
playwright install chromium
```

## 使用方法

### 运行所有测试

```bash
cd PM_Screenshot_Tool/tests
python screenshot_tool_tester.py
```

### 运行指定测试套件

```bash
# 健康检查
python screenshot_tool_tester.py --suite health

# 显示测试（缩略图、预览一致性）
python screenshot_tool_tester.py --suite display

# 文件系统测试
python screenshot_tool_tester.py --suite filesystem

# 操作测试（删除等）
python screenshot_tool_tester.py --suite operation

# 同步测试（刷新一致性）
python screenshot_tool_tester.py --suite sync

# 性能测试
python screenshot_tool_tester.py --suite performance
```

### 常用参数

```bash
# 指定测试项目
python screenshot_tool_tester.py --project "downloads_2024/MyApp"

# 循环测试 5 次
python screenshot_tool_tester.py --loop 5

# 自动修复发现的问题
python screenshot_tool_tester.py --fix

# 无头模式（不显示浏览器）
python screenshot_tool_tester.py --headless

# 组合使用
python screenshot_tool_tester.py --suite display --loop 3 --fix
```

## 测试套件说明

| 套件 | 说明 | 测试内容 |
|------|------|----------|
| `health` | 健康检查 | 服务器是否运行 |
| `project` | 项目管理 | 项目列表、项目选择 |
| `display` | 显示测试 | 缩略图与预览一致性、位置索引连续性 |
| `filesystem` | 文件系统 | API与文件系统一致性、孤立缩略图 |
| `operation` | 操作测试 | 删除功能 |
| `sync` | 同步测试 | 刷新后数据一致性 |
| `navigation` | 导航测试 | 页面导航 |
| `performance` | 性能测试 | 加载时间 |

## 测试报告

测试完成后会生成 JSON 格式的报告：

```
test_reports/report_1702857600.json
```

报告内容示例：

```json
{
  "timestamp": "2024-12-17T23:30:00",
  "config": {
    "project": "downloads_2024/WeightWatchers",
    "loop_count": 1,
    "auto_fix": false
  },
  "results": [
    {
      "name": "服务器健康检查",
      "status": "passed",
      "duration": 0.15,
      "message": "服务器运行正常"
    },
    ...
  ]
}
```

## 扩展测试

### 添加新测试

1. 创建测试类，继承 `BaseTest`：

```python
class TestMyFeature(BaseTest):
    name = "我的功能测试"
    
    async def run(self) -> TestResult:
        # 测试逻辑
        if success:
            return self.passed("测试通过")
        return self.failed("测试失败", fix="修复建议")
```

2. 添加到测试套件：

```python
TestSuite.SUITES["myfeature"] = [TestMyFeature]
TestSuite.ALL_TESTS.append(TestMyFeature)
```

### 助手类

- `PageHelper`: 页面操作（导航、点击、获取信息）
- `APIHelper`: API 调用
- `FileSystemHelper`: 文件系统操作

## 与 AI 调试配合

1. 运行测试发现问题
2. 查看测试报告中的 `fix_suggestion`
3. AI 根据建议修改代码
4. 再次运行测试验证修复
5. 循环直到所有测试通过

```bash
# 自动循环测试直到通过
python screenshot_tool_tester.py --loop 10 --fix
```
