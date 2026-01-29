#!/bin/bash
#===============================================================================
# FindableX 一键部署脚本
# 适用于: Ubuntu 24.04 LTS / Debian 12+
# 用法: bash deploy.sh [install|update|start|stop|logs|backup|status]
#===============================================================================

set -euo pipefail

# ============ 配置 ============
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="findablex"
DEPLOY_DIR="/opt/${PROJECT_NAME}"
DATA_DIR="/var/lib/${PROJECT_NAME}"
BACKUP_DIR="/var/backups/${PROJECT_NAME}"
LOG_FILE="/var/log/${PROJECT_NAME}/deploy.log"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============ 工具函数 ============
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $1" >> "$LOG_FILE" 2>/dev/null || true
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARN] $1" >> "$LOG_FILE" 2>/dev/null || true
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $1" >> "$LOG_FILE" 2>/dev/null || true
}

log_step() {
    echo -e "${BLUE}==>${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要 root 权限运行"
        log_info "请使用: sudo bash $0"
        exit 1
    fi
}

check_os() {
    if [[ ! -f /etc/os-release ]]; then
        log_error "无法检测操作系统版本"
        exit 1
    fi
    
    . /etc/os-release
    
    if [[ "$ID" != "ubuntu" && "$ID" != "debian" ]]; then
        log_warn "此脚本针对 Ubuntu/Debian 优化，其他系统可能需要调整"
    fi
    
    log_info "检测到系统: $PRETTY_NAME"
}

# ============ 配置阿里云 apt 镜像源 ============
configure_apt_mirror() {
    log_step "配置阿里云 apt 镜像源..."
    
    # 备份原有源
    if [[ -f /etc/apt/sources.list ]] && [[ ! -f /etc/apt/sources.list.bak ]]; then
        cp /etc/apt/sources.list /etc/apt/sources.list.bak
    fi
    
    # 检测 Ubuntu 版本
    . /etc/os-release
    
    if [[ "$ID" == "ubuntu" ]]; then
        cat > /etc/apt/sources.list << EOF
# 阿里云 Ubuntu 镜像源
deb https://mirrors.aliyun.com/ubuntu/ ${VERSION_CODENAME} main restricted universe multiverse
deb https://mirrors.aliyun.com/ubuntu/ ${VERSION_CODENAME}-updates main restricted universe multiverse
deb https://mirrors.aliyun.com/ubuntu/ ${VERSION_CODENAME}-backports main restricted universe multiverse
deb https://mirrors.aliyun.com/ubuntu/ ${VERSION_CODENAME}-security main restricted universe multiverse
EOF
        log_info "Ubuntu apt 源已切换为阿里云镜像"
    elif [[ "$ID" == "debian" ]]; then
        cat > /etc/apt/sources.list << EOF
# 阿里云 Debian 镜像源
deb https://mirrors.aliyun.com/debian/ ${VERSION_CODENAME} main contrib non-free non-free-firmware
deb https://mirrors.aliyun.com/debian/ ${VERSION_CODENAME}-updates main contrib non-free non-free-firmware
deb https://mirrors.aliyun.com/debian-security ${VERSION_CODENAME}-security main contrib non-free non-free-firmware
EOF
        log_info "Debian apt 源已切换为阿里云镜像"
    fi
}

# ============ 安装依赖 ============
install_dependencies() {
    log_step "安装系统依赖..."
    
    # 先配置国内镜像源
    configure_apt_mirror
    
    apt-get update
    apt-get install -y \
        curl \
        wget \
        git \
        ca-certificates \
        gnupg \
        lsb-release \
        software-properties-common \
        ufw \
        fail2ban \
        htop \
        unzip
    
    log_info "系统依赖安装完成"
}

install_docker() {
    log_step "安装 Docker..."
    
    if command -v docker &> /dev/null; then
        log_info "Docker 已安装: $(docker --version)"
        # 确保镜像加速已配置
        configure_docker_mirror
        return 0
    fi
    
    # 使用阿里云 Docker CE 镜像安装
    log_info "使用阿里云镜像安装 Docker..."
    
    # 添加阿里云 Docker GPG 密钥
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    
    # 添加阿里云 Docker 仓库
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://mirrors.aliyun.com/docker-ce/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # 安装 Docker
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # 配置镜像加速
    configure_docker_mirror
    
    # 启动 Docker
    systemctl enable docker
    systemctl start docker
    
    log_info "Docker 安装完成: $(docker --version)"
}

# ============ 配置 Docker 镜像加速 ============
configure_docker_mirror() {
    log_step "配置 Docker 镜像加速..."
    
    mkdir -p /etc/docker
    
    # 配置阿里云镜像加速器
    cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://registry.cn-hangzhou.aliyuncs.com",
    "https://mirror.ccs.tencentyun.com",
    "https://docker.mirrors.ustc.edu.cn"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  }
}
EOF
    
    # 重新加载 Docker 配置
    if systemctl is-active --quiet docker; then
        systemctl daemon-reload
        systemctl restart docker
        log_info "Docker 镜像加速已配置并重启"
    else
        log_info "Docker 镜像加速已配置"
    fi
}

# ============ 配置防火墙 ============
configure_firewall() {
    log_step "配置防火墙..."
    
    # 基本规则
    ufw default deny incoming
    ufw default allow outgoing
    
    # 允许 SSH
    ufw allow 22/tcp comment 'SSH'
    
    # 允许 HTTP/HTTPS
    ufw allow 80/tcp comment 'HTTP'
    ufw allow 443/tcp comment 'HTTPS'
    
    # 启用防火墙
    echo "y" | ufw enable
    
    log_info "防火墙配置完成"
    ufw status
}

# ============ 创建目录结构 ============
create_directories() {
    log_step "创建目录结构..."
    
    mkdir -p "${DEPLOY_DIR}"
    mkdir -p "${DATA_DIR}/postgres"
    mkdir -p "${DATA_DIR}/redis"
    mkdir -p "${DATA_DIR}/api"
    mkdir -p "${DATA_DIR}/uploads"
    mkdir -p "${DATA_DIR}/ssl"
    mkdir -p "${BACKUP_DIR}"
    mkdir -p "$(dirname "$LOG_FILE")"
    
    log_info "目录创建完成"
}

# ============ 部署应用 ============
deploy_app() {
    log_step "部署应用..."
    
    # 获取项目根目录 (deploy 目录的父目录)
    PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
    
    # 检查是否已经在完整项目目录中运行（通过 git clone 到 /opt/findablex）
    if [[ "${PROJECT_ROOT}" == "${DEPLOY_DIR}" ]] || [[ "$(realpath "${PROJECT_ROOT}")" == "$(realpath "${DEPLOY_DIR}")" ]]; then
        log_info "检测到已在项目目录中运行，跳过文件复制"
        
        # 确保 deploy 目录下的文件可被访问
        if [[ ! -f "${DEPLOY_DIR}/docker-compose.yml" ]] && [[ -f "${SCRIPT_DIR}/docker-compose.yml" ]]; then
            # 创建软链接或复制 deploy 目录内容到根目录
            cp "${SCRIPT_DIR}"/*.yml "${DEPLOY_DIR}/" 2>/dev/null || true
            cp "${SCRIPT_DIR}"/*.conf "${DEPLOY_DIR}/" 2>/dev/null || true
            cp "${SCRIPT_DIR}"/Dockerfile.* "${DEPLOY_DIR}/" 2>/dev/null || true
        fi
    # 复制整个项目（Docker 构建需要访问 packages 目录）
    elif [[ -d "${PROJECT_ROOT}/packages" ]]; then
        log_info "复制项目文件到 ${DEPLOY_DIR}..."
        
        # 复制必要的目录和文件
        cp -r "${PROJECT_ROOT}/packages" "${DEPLOY_DIR}/"
        cp -r "${PROJECT_ROOT}/docker" "${DEPLOY_DIR}/" 2>/dev/null || true
        cp -r "${SCRIPT_DIR}"/* "${DEPLOY_DIR}/"
        
        # 复制根目录配置文件
        cp "${PROJECT_ROOT}/env.example" "${DEPLOY_DIR}/" 2>/dev/null || true
        
        log_info "项目文件复制完成"
    elif [[ -d "${SCRIPT_DIR}" ]]; then
        # 如果没有 packages 目录，可能是单独上传的 deploy 目录
        log_warn "未找到 packages 目录，尝试使用当前目录结构"
        cp -r "${SCRIPT_DIR}"/* "${DEPLOY_DIR}/"
    else
        log_error "找不到部署文件目录"
        exit 1
    fi
    
    # 检查环境变量文件（在 deploy 子目录或根目录）
    ENV_FILE="${DEPLOY_DIR}/.env"
    if [[ ! -f "${ENV_FILE}" ]]; then
        # 也检查 deploy 子目录
        if [[ -f "${DEPLOY_DIR}/deploy/.env" ]]; then
            ENV_FILE="${DEPLOY_DIR}/deploy/.env"
        elif [[ -f "${DEPLOY_DIR}/.env.example" ]]; then
            cp "${DEPLOY_DIR}/.env.example" "${ENV_FILE}"
            log_warn "已创建 .env 文件，请编辑配置: ${ENV_FILE}"
        elif [[ -f "${DEPLOY_DIR}/deploy/.env.example" ]]; then
            cp "${DEPLOY_DIR}/deploy/.env.example" "${ENV_FILE}"
            log_warn "已创建 .env 文件，请编辑配置: ${ENV_FILE}"
        else
            create_env_file
        fi
    fi
    
    cd "${DEPLOY_DIR}"
    
    log_info "应用部署完成"
}

# ============ 创建环境变量文件 ============
create_env_file() {
    log_step "创建环境变量配置..."
    
    # 生成随机密码和密钥
    DB_PASSWORD=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)
    JWT_SECRET=$(openssl rand -base64 64 | tr -dc 'a-zA-Z0-9' | head -c 64)
    
    cat > "${DEPLOY_DIR}/.env" << EOF
# FindableX 生产环境配置
# 生成时间: $(date '+%Y-%m-%d %H:%M:%S')

# ============ 数据库配置 ============
DB_USER=findablex
DB_PASSWORD=${DB_PASSWORD}
DB_NAME=findablex

# ============ 安全配置 ============
JWT_SECRET=${JWT_SECRET}

# ============ 域名配置 ============
DOMAIN=findablex.com
ALLOWED_ORIGINS=https://findablex.com,https://www.findablex.com

# ============ API 配置 ============
NEXT_PUBLIC_API_URL=/api

# ============ 可选: AI API 密钥 ============
OPENAI_API_KEY=
QWEN_API_KEY=

# ============ 版本 ============
VERSION=latest
EOF
    
    chmod 600 "${DEPLOY_DIR}/.env"
    log_warn "请编辑配置文件: ${DEPLOY_DIR}/.env"
}

# ============ 获取 docker-compose 文件路径 ============
get_compose_file() {
    if [[ -f "${DEPLOY_DIR}/docker-compose.yml" ]]; then
        echo "${DEPLOY_DIR}/docker-compose.yml"
    elif [[ -f "${DEPLOY_DIR}/deploy/docker-compose.yml" ]]; then
        echo "${DEPLOY_DIR}/deploy/docker-compose.yml"
    else
        log_error "找不到 docker-compose.yml 文件"
        exit 1
    fi
}

# ============ 构建镜像 ============
build_images() {
    log_step "构建 Docker 镜像..."
    
    COMPOSE_FILE=$(get_compose_file)
    COMPOSE_DIR=$(dirname "${COMPOSE_FILE}")
    
    cd "${COMPOSE_DIR}"
    
    # 构建镜像
    docker compose build --no-cache
    
    log_info "镜像构建完成"
}

# ============ 启动服务 ============
start_services() {
    log_step "启动服务..."
    
    COMPOSE_FILE=$(get_compose_file)
    COMPOSE_DIR=$(dirname "${COMPOSE_FILE}")
    
    cd "${COMPOSE_DIR}"
    
    # 启动所有服务
    docker compose up -d
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 10
    
    # 检查服务状态
    docker compose ps
    
    log_info "服务启动完成"
}

# ============ 停止服务 ============
stop_services() {
    log_step "停止服务..."
    
    COMPOSE_FILE=$(get_compose_file)
    COMPOSE_DIR=$(dirname "${COMPOSE_FILE}")
    
    cd "${COMPOSE_DIR}"
    docker compose down
    
    log_info "服务已停止"
}

# ============ 查看日志 ============
view_logs() {
    COMPOSE_FILE=$(get_compose_file)
    COMPOSE_DIR=$(dirname "${COMPOSE_FILE}")
    
    cd "${COMPOSE_DIR}"
    
    if [[ -n "${1:-}" ]]; then
        docker compose logs -f "$1"
    else
        docker compose logs -f
    fi
}

# ============ 备份数据 ============
backup_data() {
    log_step "备份数据..."
    
    BACKUP_FILE="${BACKUP_DIR}/findablex_$(date '+%Y%m%d_%H%M%S').tar.gz"
    
    COMPOSE_FILE=$(get_compose_file)
    COMPOSE_DIR=$(dirname "${COMPOSE_FILE}")
    
    cd "${COMPOSE_DIR}"
    
    # 备份数据库
    docker compose exec -T postgres pg_dump -U findablex findablex > "${BACKUP_DIR}/db_backup.sql"
    
    # 打包备份
    tar -czf "$BACKUP_FILE" \
        -C "${DATA_DIR}" postgres redis api uploads \
        -C "${BACKUP_DIR}" db_backup.sql
    
    rm -f "${BACKUP_DIR}/db_backup.sql"
    
    # 保留最近 7 个备份
    ls -t "${BACKUP_DIR}"/findablex_*.tar.gz | tail -n +8 | xargs -r rm
    
    log_info "备份完成: $BACKUP_FILE"
}

# ============ 显示状态 ============
show_status() {
    log_step "服务状态..."
    
    COMPOSE_FILE=$(get_compose_file)
    COMPOSE_DIR=$(dirname "${COMPOSE_FILE}")
    
    cd "${COMPOSE_DIR}"
    docker compose ps
    
    echo ""
    log_step "资源使用..."
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
}

# ============ 更新应用 ============
update_app() {
    log_step "更新应用..."
    
    # 备份
    backup_data
    
    # 停止服务
    stop_services
    
    # 拉取最新代码（如果是 git 仓库）
    if [[ -d "${DEPLOY_DIR}/.git" ]]; then
        cd "${DEPLOY_DIR}"
        git pull
    fi
    
    # 重新构建
    build_images
    
    # 启动服务
    start_services
    
    log_info "更新完成"
}

# ============ 清理并重新部署 ============
clean_deploy() {
    log_step "清理并重新部署..."
    
    # 停止服务
    stop_services 2>/dev/null || true
    
    # 清理旧镜像
    docker system prune -f
    
    # 重新构建
    build_images
    
    # 启动服务
    start_services
    
    log_info "重新部署完成"
}

# ============ 初始化数据库 ============
init_database() {
    log_step "初始化数据库..."
    
    COMPOSE_FILE=$(get_compose_file)
    COMPOSE_DIR=$(dirname "${COMPOSE_FILE}")
    
    cd "${COMPOSE_DIR}"
    
    # 等待数据库就绪
    log_info "等待数据库就绪..."
    sleep 5
    
    # 运行数据库迁移
    docker compose exec api python -c "
from app.db.database import engine
from app.db.models import Base
Base.metadata.create_all(bind=engine)
print('Database tables created successfully')
"
    
    log_info "数据库初始化完成"
}

# ============ 安装 SSL 证书 ============
install_ssl() {
    log_step "安装 SSL 证书..."
    
    COMPOSE_FILE=$(get_compose_file)
    COMPOSE_DIR=$(dirname "${COMPOSE_FILE}")
    
    if ! command -v certbot &> /dev/null; then
        apt-get install -y certbot
    fi
    
    read -p "请输入域名: " DOMAIN
    
    cd "${COMPOSE_DIR}"
    
    # 停止 nginx 以释放 80 端口
    docker compose stop nginx 2>/dev/null || true
    
    # 获取证书
    certbot certonly --standalone -d "$DOMAIN" --non-interactive --agree-tos --email "admin@${DOMAIN}"
    
    # 复制证书
    cp /etc/letsencrypt/live/"$DOMAIN"/fullchain.pem "${DATA_DIR}/ssl/"
    cp /etc/letsencrypt/live/"$DOMAIN"/privkey.pem "${DATA_DIR}/ssl/"
    
    # 设置自动续期
    echo "0 0 1 * * root certbot renew --quiet && cp /etc/letsencrypt/live/$DOMAIN/*.pem ${DATA_DIR}/ssl/ && docker compose -f ${COMPOSE_FILE} restart nginx" > /etc/cron.d/certbot-renewal
    
    # 重启 nginx
    docker compose start nginx
    
    log_info "SSL 证书安装完成"
}

# ============ 完整安装 ============
full_install() {
    log_info "开始 FindableX 完整安装..."
    echo ""
    
    check_root
    check_os
    
    install_dependencies
    install_docker
    configure_firewall
    create_directories
    deploy_app
    
    # 提示用户配置
    echo ""
    log_warn "=========================================="
    log_warn "请先编辑配置文件: ${DEPLOY_DIR}/.env"
    log_warn "配置完成后运行: bash $0 start"
    log_warn "=========================================="
    echo ""
    
    read -p "是否现在编辑配置文件? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ${EDITOR:-nano} "${DEPLOY_DIR}/.env"
    fi
    
    read -p "是否现在构建并启动服务? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        build_images
        start_services
        init_database
        
        echo ""
        log_info "=========================================="
        log_info "FindableX 安装完成!"
        log_info "访问地址: http://$(hostname -I | awk '{print $1}')"
        log_info "=========================================="
    fi
}

# ============ 帮助信息 ============
show_help() {
    cat << EOF
FindableX 部署管理脚本

用法: $0 <命令>

命令:
  install     完整安装 (首次部署使用)
  update      更新应用 (保留数据)
  start       启动所有服务
  stop        停止所有服务
  restart     重启所有服务
  logs [服务] 查看日志 (可选指定服务名)
  status      显示服务状态
  backup      备份数据
  ssl         安装 SSL 证书
  build       重新构建镜像
  help        显示此帮助信息

示例:
  sudo bash $0 install     # 首次安装
  sudo bash $0 start       # 启动服务
  sudo bash $0 logs api    # 查看 API 日志
  sudo bash $0 backup      # 备份数据

目录:
  部署目录: ${DEPLOY_DIR}
  数据目录: ${DATA_DIR}
  备份目录: ${BACKUP_DIR}
  日志文件: ${LOG_FILE}

EOF
}

# ============ 主入口 ============
main() {
    case "${1:-help}" in
        install)
            full_install
            ;;
        update)
            check_root
            update_app
            ;;
        start)
            check_root
            start_services
            ;;
        stop)
            check_root
            stop_services
            ;;
        restart)
            check_root
            stop_services
            start_services
            ;;
        logs)
            view_logs "${2:-}"
            ;;
        status)
            show_status
            ;;
        backup)
            check_root
            backup_data
            ;;
        ssl)
            check_root
            install_ssl
            ;;
        build)
            check_root
            build_images
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
