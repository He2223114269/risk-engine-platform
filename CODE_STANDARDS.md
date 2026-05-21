# 代码规范标准

## 文件头模板

### Python 文件头

```python
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : [module_name]
功能描述 : [模块功能的一句话描述]
创建日期 : YYYY-MM-DD
开发者   : Jingluo
版本     : v0.1.0
更新历史 :
  2026-05-21, Jingluo, v0.1.0 — 初始创建
  YYYY-MM-DD, [Name], vX.Y.Z — [修改内容]
============================================================================
"""

from __future__ import annotations

__all__ = [
    "ClassName1",
    "ClassName2",
]
```

### TypeScript 文件头

```typescript
/**
 * ============================================================================
 * 模块名称 : [module_name]
 * 功能描述 : [模块功能的一句话描述]
 * 创建日期 : YYYY-MM-DD
 * 开发者   : Jingluo
 * 版本     : v0.1.0
 * 更新历史 :
 *   2026-05-21, Jingluo, v0.1.0 — 初始创建
 *   YYYY-MM-DD, [Name], vX.Y.Z — [修改内容]
 * ============================================================================
 */

// ===== Dependencies =====
// ===== Types / Interfaces =====
// ===== Implementation =====
// ===== Exports =====
```

## 提交信息规范

```
<type>: <简短描述>

<详细描述（可选）>

- 变更列表项
- 变更列表项
```

### type 类型

| type | 说明 |
|------|------|
| feat | 新功能 |
| fix | 修复 |
| refactor | 重构 |
| docs | 文档 |
| style | 代码格式 |
| test | 测试 |
| chore | 构建/CI |
| perf | 性能优化 |

### 示例

```
feat(feature_store): 实现特征注册中心基础功能

- 新增 FeatureRegistry 类，支持特征定义注册/查询
- 新增特征 Schema 校验（名称、类型、来源、版本）
- 实现特征元数据持久化（SQLite）

Closes #12
```

## 命名规范

| 语言 | 类型 | 规范 |
|------|------|------|
| Python | 模块/包 | snake_case |
| Python | 类 | PascalCase |
| Python | 函数/方法 | snake_case |
| Python | 变量 | snake_case |
| Python | 常量 | UPPER_CASE |
| TS | 文件 | camelCase.tsx |
| TS | 组件 | PascalCase.tsx |
| TS | 函数 | camelCase |
| TS | 类型/接口 | PascalCase |

## 版本号规范

遵循 Semantic Versioning 2.0.0: `MAJOR.MINOR.PATCH`

- MAJOR: 不兼容的 API 变更
- MINOR: 向下兼容的功能新增
- PATCH: 向下兼容的 bug 修复
