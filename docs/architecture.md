# FindableX 架构文档

## 系统概述

FindableX 是一个垂直行业 GEO（Generative Engine Optimization）体检型 SaaS 平台，同时支持科研实验功能。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Next.js 14, React, TailwindCSS |
| 后端 | FastAPI (Python 3.11+) |
| 数据库 | PostgreSQL 16 |
| 缓存/队列 | Redis 7 |
| 任务队列 | Celery 5 |
| 爬虫 | Playwright |
| AI | CrewAI, LangChain |
| 反向代理 | Caddy 2 |

## 目录结构

```
findablex/
├── packages/
│   ├── api/          # FastAPI 后端
│   ├── worker/       # Celery 异步任务
│   ├── crawler/      # Playwright 爬虫
│   ├── web/          # Next.js 前端
│   └── shared/       # 共享类型和常量
├── infra/            # 基础设施配置
├── docker/           # Dockerfile
└── docs/             # 文档
```

## 数据流

```
输入 → 解析 → 提取引用 → 计算指标 → 诊断 → 生成报告
```

## API 端点

### 认证
- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/login` - 用户登录
- `GET /api/v1/auth/me` - 获取当前用户

### 工作区
- `GET /api/v1/workspaces` - 列出工作区
- `POST /api/v1/workspaces` - 创建工作区

### 项目
- `GET /api/v1/projects` - 列出项目
- `POST /api/v1/projects` - 创建项目

### 运行
- `GET /api/v1/runs` - 列出运行
- `POST /api/v1/runs/import` - 导入数据运行

### 报告
- `GET /api/v1/reports/{id}` - 获取报告
- `POST /api/v1/reports/{id}/share` - 创建分享链接

## 部署

使用 Docker Compose 部署：

```bash
make up        # 启动开发环境
make migrate   # 运行数据库迁移
make seed      # 填充测试数据
```
