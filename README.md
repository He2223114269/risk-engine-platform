# 风控引擎决策分析平台 🛡️

> 淘顺实时授信风控引擎 — 生产级 · 模块化 · 可观测 · 可灰度

## 快速开始

```bash
# 1. 安装依赖
make install

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入数据库连接信息

# 3. 启动开发服务器
make run-dev

# 4. 打开浏览器
# http://localhost:8000/docs  — Swagger API 文档
# http://localhost:3000       — 前端页面
```

## 项目结构

```
├── risk_engine/      风控引擎 — 特征存储 / 模型注册 / 决策引擎 / 模型工程 / 工具包
├── backend/          后端服务 — API / 服务层 / 数据库 / 缓存 / 消息队列 / 可观测性
├── frontend/         前端网站 — Dashboard / 监控 / 分析 / 报表
├── docs/             文档
├── tests/            测试
├── docker/           容器化部署
└── k8s/              K8s 部署配置
```

## 核心架构

详见 [ARCHITECTURE.md](ARCHITECTURE.md)

## 开发规范

详见 [CODE_STANDARDS.md](CODE_STANDARDS.md)

## 版本

当前版本：v0.1.0（架构骨架阶段）
