# FindableX 部署指南

一键部署 FindableX GEO 平台到阿里云 ECS (Ubuntu 24.04 LTS)

## 目录

- [系统要求](#系统要求)
- [快速部署](#快速部署)
- [镜像加速](#镜像加速)
- [配置说明](#配置说明)
- [爬虫部署方案](#爬虫部署方案)
- [SSL 证书配置](#ssl-证书配置)
- [运维命令](#运维命令)
- [故障排除](#故障排除)

## 系统要求

### 服务器配置 (阿里云 ECS 推荐)

| 组件 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 硬盘 | 40 GB SSD | 100 GB SSD |
| 系统 | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |

### 阿里云实例推荐

- **轻量应用服务器**: 2核4G (适合测试)
- **ECS 计算型 c7**: ecs.c7.large (适合生产)

## 快速部署

### 第一步：准备服务器

1. 购买阿里云 ECS 实例，选择 Ubuntu 24.04 LTS 系统
2. 在安全组中开放端口：22 (SSH), 80 (HTTP), 443 (HTTPS)
3. SSH 连接到服务器

```bash
ssh root@your-server-ip
```

### 第二步：下载部署脚本

```bash
# 方式一：从 Git 仓库克隆
git clone https://github.com/your-org/findablex.git
cd findablex/deploy

# 方式二：直接上传部署文件夹
# 使用 scp 或 sftp 上传 deploy 目录到服务器
```

### 第三步：运行一键部署

```bash
# 添加执行权限
chmod +x deploy.sh

# 运行安装脚本
sudo bash deploy.sh install
```

脚本会自动：
- 配置阿里云 apt 镜像源
- 安装 Docker 和必要依赖
- 配置 Docker 镜像加速（阿里云）
- 配置防火墙
- 创建目录结构
- 生成配置文件

## 镜像加速

部署脚本已自动配置国内镜像加速，无需手动设置：

### 已配置的镜像源

| 类型 | 镜像源 |
|------|--------|
| **apt (Ubuntu/Debian)** | mirrors.aliyun.com |
| **Docker CE** | mirrors.aliyun.com/docker-ce |
| **Docker Registry** | registry.cn-hangzhou.aliyuncs.com |
| **pip (Python)** | mirrors.aliyun.com/pypi |
| **npm (Node.js)** | registry.npmmirror.com |

### 手动验证镜像配置

```bash
# 检查 Docker 镜像加速
docker info | grep -A 5 "Registry Mirrors"

# 测试 Docker 拉取速度
time docker pull nginx:alpine
```

### 第四步：配置环境变量

```bash
# 编辑配置文件
nano /opt/findablex/.env
```

必须修改的配置：

```env
# 数据库密码 (已自动生成，可保持不变)
DB_PASSWORD=xxxxxx

# JWT 密钥 (已自动生成，可保持不变)
JWT_SECRET=xxxxxx

# 域名配置 (必须修改)
DOMAIN=your-domain.com
ALLOWED_ORIGINS=https://your-domain.com
```

### 第五步：启动服务

```bash
# 构建并启动
sudo bash deploy.sh build
sudo bash deploy.sh start
```

### 第六步：初始化数据库

服务首次启动会自动创建数据库表。如需手动初始化：

```bash
cd /opt/findablex
docker compose exec api python -c "
from app.db.database import engine
from app.db.models import Base
Base.metadata.create_all(bind=engine)
"
```

### 第七步：访问系统

- HTTP: `http://your-server-ip`
- HTTPS: 配置 SSL 后访问 `https://your-domain.com`

## 配置说明

### 环境变量详解

```env
# ============ 数据库 ============
DB_USER=findablex          # 数据库用户名
DB_PASSWORD=xxx            # 数据库密码 (安装时自动生成)
DB_NAME=findablex          # 数据库名

# ============ 安全 ============
JWT_SECRET=xxx             # JWT 签名密钥 (安装时自动生成)

# ============ 域名 ============
DOMAIN=findablex.com       # 你的域名
ALLOWED_ORIGINS=https://findablex.com  # CORS 允许的源

# ============ API ============
NEXT_PUBLIC_API_URL=/api   # 前端调用后端的路径

# ============ AI 密钥 (可选) ============
OPENAI_API_KEY=            # OpenAI API 密钥
QWEN_API_KEY=              # 通义千问 API 密钥

# ============ 爬虫代理 (可选) ============
CRAWLER_AGENT_ENABLED=false    # 启用远程爬虫代理
CRAWLER_AGENT_TOKEN=           # 代理认证令牌
```

### 目录结构

```
/opt/findablex/           # 部署目录
├── docker-compose.yml    # Docker 编排文件
├── .env                  # 环境配置
├── nginx.conf           # Nginx 配置
└── ssl/                 # SSL 证书

/var/lib/findablex/      # 数据目录
├── postgres/            # 数据库文件
├── redis/               # Redis 持久化
├── api/                 # API 数据
├── uploads/             # 用户上传
└── ssl/                 # SSL 证书

/var/backups/findablex/  # 备份目录
└── findablex_*.tar.gz   # 自动备份文件
```

## 爬虫部署方案

### 方案一：服务器端无头浏览器 (默认)

爬虫在服务器上以无头模式运行。

**优点**：
- 无需额外配置
- 全自动运行

**缺点**：
- 可能被 AI 平台检测和阻止
- 无法使用登录态

**配置**：默认启用，无需额外配置

### 方案二：远程浏览器代理 (推荐)

在本地电脑或带 GUI 的服务器上运行爬虫代理，使用真实浏览器。

**优点**：
- 不容易被检测
- 可以使用登录态
- 支持手动处理验证码

**缺点**：
- 需要保持代理运行
- 需要额外的机器

**架构**：

```
┌────────────────────────────────────┐
│         Aliyun ECS Server          │
│  ┌──────────────────────────────┐  │
│  │  API + Web + DB (容器化)      │  │
│  └───────────────┬──────────────┘  │
└──────────────────┼─────────────────┘
                   │ HTTPS
┌──────────────────┼─────────────────┐
│   Local Machine  │                 │
│  ┌───────────────┴──────────────┐  │
│  │     Crawler Agent            │  │
│  │  (Playwright + Chrome)       │  │
│  └──────────────────────────────┘  │
└────────────────────────────────────┘
```

**配置步骤**：

1. 在服务器上启用代理功能：

```env
# /opt/findablex/.env
CRAWLER_AGENT_ENABLED=true
CRAWLER_AGENT_TOKEN=your-secure-token-here
```

2. 在本地电脑上运行代理：

```bash
# 安装依赖
cd packages/crawler-agent
pip install -r requirements.txt
playwright install chromium

# 配置
cp .env.example .env
nano .env  # 填写 API_URL 和 AGENT_TOKEN

# 运行
python agent.py
```

详细说明参见 [Crawler Agent README](../packages/crawler-agent/README.md)

### 方案三：VNC 远程桌面 (高级)

在云服务器上安装桌面环境，通过 VNC 远程操作。

```bash
# 安装桌面环境
sudo apt install ubuntu-desktop tigervnc-standalone-server

# 配置 VNC
vncserver -localhost no -geometry 1920x1080

# 通过 VNC 客户端连接后运行 Agent
python agent.py
```

## SSL 证书配置

### 使用 Let's Encrypt (免费)

```bash
# 安装证书
sudo bash deploy.sh ssl

# 按提示输入域名
# 证书会自动续期
```

### 使用阿里云 SSL 证书

1. 在阿里云申请 SSL 证书
2. 下载 Nginx 格式证书
3. 上传到服务器：

```bash
# 上传证书
scp your-domain.com.pem root@server:/var/lib/findablex/ssl/fullchain.pem
scp your-domain.com.key root@server:/var/lib/findablex/ssl/privkey.pem

# 重启 Nginx
cd /opt/findablex
docker compose restart nginx
```

4. 取消 nginx.conf 中 HTTPS 部分的注释

## 运维命令

```bash
# 查看状态
sudo bash deploy.sh status

# 查看日志
sudo bash deploy.sh logs        # 所有日志
sudo bash deploy.sh logs api    # API 日志
sudo bash deploy.sh logs web    # 前端日志

# 服务管理
sudo bash deploy.sh start       # 启动
sudo bash deploy.sh stop        # 停止
sudo bash deploy.sh restart     # 重启

# 更新应用
sudo bash deploy.sh update      # 拉取最新代码并重建

# 备份数据
sudo bash deploy.sh backup

# 重新构建镜像
sudo bash deploy.sh build
```

### 手动 Docker 命令

```bash
cd /opt/findablex

# 查看容器状态
docker compose ps

# 进入容器
docker compose exec api bash
docker compose exec postgres psql -U findablex

# 查看日志
docker compose logs -f api --tail 100

# 重启单个服务
docker compose restart api
```

## 故障排除

### 服务无法启动

```bash
# 检查 Docker 状态
systemctl status docker

# 查看容器日志
docker compose logs

# 检查端口占用
netstat -tlnp | grep -E '80|443|8000|3000'
```

### 数据库连接失败

```bash
# 检查 PostgreSQL 容器
docker compose ps postgres
docker compose logs postgres

# 手动测试连接
docker compose exec postgres psql -U findablex -d findablex -c "SELECT 1"
```

### 网页打不开

```bash
# 检查 Nginx
docker compose logs nginx

# 检查防火墙
ufw status

# 检查阿里云安全组是否开放 80/443 端口
```

### 爬虫任务失败

1. 检查服务器端日志：
```bash
docker compose logs api | grep -i crawler
```

2. 如果使用远程代理，检查代理日志：
```bash
# 在运行代理的机器上
cat agent.log
```

3. 常见原因：
   - AI 平台检测到自动化操作
   - 网络问题
   - 需要登录/验证码

### 内存不足

```bash
# 查看内存使用
docker stats

# 如果内存不足，可以调整限制
# 编辑 docker-compose.yml 中的 deploy.resources.limits.memory
```

## 支持

- 文档: https://docs.findablex.com
- Issues: https://github.com/your-org/findablex/issues
- Email: support@findablex.com
