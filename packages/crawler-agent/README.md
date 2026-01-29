# FindableX Crawler Agent

爬虫代理服务 - 在本地机器上运行，使用本地浏览器执行爬虫任务。

## 为什么需要 Crawler Agent?

在服务器上运行无头浏览器存在以下问题：
1. **容易被检测** - AI 平台可能检测并阻止无头浏览器
2. **无法使用登录态** - 某些 AI 平台需要登录
3. **验证码问题** - 服务器环境难以处理验证码

Crawler Agent 解决这些问题：
- 在你的本地电脑或有 GUI 的服务器上运行
- 使用真实的浏览器（支持已登录的 session）
- 可以手动处理验证码
- 通过 API 与主服务器通信

## 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                       Aliyun ECS Server                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  PostgreSQL │  │    Redis    │  │        API Server       │  │
│  │  (Database) │  │   (Cache)   │  │  - 任务管理             │  │
│  └─────────────┘  └─────────────┘  │  - 结果存储             │  │
│                                     │  - 用户界面后端         │  │
│                                     └───────────┬─────────────┘  │
│                                                 │                │
│  ┌─────────────────────────────────────────────┼──────────────┐  │
│  │                    Nginx                     │              │  │
│  │              (Reverse Proxy)                 │              │  │
│  └─────────────────────────────────────────────┼──────────────┘  │
└─────────────────────────────────────────────────┼────────────────┘
                                                  │
                                    HTTPS (Poll/Report)
                                                  │
┌─────────────────────────────────────────────────┼────────────────┐
│                  Local Machine (你的电脑)        │                │
│  ┌──────────────────────────────────────────────┴─────────────┐  │
│  │                    Crawler Agent                           │  │
│  │  ┌─────────────────┐  ┌─────────────────────────────────┐  │  │
│  │  │  Task Poller    │  │     Browser Controller          │  │  │
│  │  │  (轮询任务队列)  │  │  (Playwright + 本地 Chrome)      │  │  │
│  │  └─────────────────┘  └─────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────┴───────────────────────────────┐   │
│  │                    Chrome Browser                          │   │
│  │              (带登录态、支持手动验证码)                     │   │
│  └────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

## 快速开始

### 1. 安装依赖

```bash
# 确保已安装 Python 3.11+
python --version

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

### 2. 配置

```bash
# 复制配置文件
cp .env.example .env

# 编辑配置
nano .env
```

配置内容：
```env
# 服务器地址
API_URL=https://your-findablex-server.com/api

# Agent 令牌 (从服务器后台获取)
AGENT_TOKEN=your_agent_token_here

# 浏览器设置
HEADLESS=false  # 设为 false 以看到浏览器操作
BROWSER_USER_DATA=/path/to/chrome/profile  # 可选：使用已有的 Chrome 配置
```

### 3. 运行

```bash
# 启动 Agent
python agent.py

# 或使用 nohup 后台运行
nohup python agent.py > agent.log 2>&1 &
```

## 使用场景

### 场景 1: 桌面电脑 (推荐)

在你的 Windows/Mac 电脑上运行 Agent：
- 优点：可以手动处理验证码、使用已登录的浏览器
- 缺点：需要保持电脑开机

### 场景 2: 带 GUI 的云服务器

在阿里云/腾讯云上开一台带桌面环境的服务器：
```bash
# Ubuntu Server 安装桌面环境
sudo apt install ubuntu-desktop
sudo apt install tigervnc-standalone-server

# 通过 VNC 连接后运行 Agent
```

### 场景 3: Docker + VNC

使用 Docker 容器运行带 VNC 的浏览器：
```bash
docker run -d \
  -p 5900:5900 \
  -e VNC_PASSWORD=yourpassword \
  --name crawler-agent \
  findablex/crawler-agent:vnc
```

## API 协议

Agent 与服务器通过 REST API 通信：

### 获取任务
```
GET /api/v1/crawler/agent/tasks
Authorization: Bearer {agent_token}

Response:
{
  "tasks": [
    {
      "id": "task-123",
      "engine": "deepseek",
      "query": "工业网络安全",
      "config": {
        "enable_web_search": true
      }
    }
  ]
}
```

### 报告结果
```
POST /api/v1/crawler/agent/results
Authorization: Bearer {agent_token}
Content-Type: application/json

{
  "task_id": "task-123",
  "success": true,
  "response_text": "...",
  "citations": [...],
  "screenshot_base64": "..."
}
```

## 安全注意事项

1. **Agent Token 保密** - 不要泄露你的 Agent Token
2. **网络安全** - 建议使用 HTTPS
3. **权限最小化** - Agent 只能执行爬虫任务，无法访问其他数据

## 故障排除

### Agent 无法连接服务器
- 检查 API_URL 是否正确
- 检查网络是否可以访问服务器
- 检查 Agent Token 是否有效

### 浏览器无法启动
- 确保 Playwright 浏览器已安装: `playwright install chromium`
- 检查是否有其他程序占用浏览器

### 任务执行失败
- 查看 agent.log 日志
- 确认网站是否可以正常访问
- 检查是否需要登录或验证码
