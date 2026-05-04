# OntoFuel 部署指南

## 概述

OntoFuel 提供三种部署方式：

| 方式 | 适用场景 | 复杂度 |
|------|---------|--------|
| **Docker Compose** | 开发、测试、快速上手 | ⭐ 低 |
| **源码部署** | 本地开发、定制需求 | ⭐⭐ 中 |
| **生产部署** | 正式环境、团队协作 | ⭐⭐⭐ 高 |

推荐新用户从 Docker Compose 开始。

---

## 1. Docker 部署

### 1.1 前置条件

- [Docker](https://docs.docker.com/get-docker/) >= 24.0
- [Docker Compose](https://docs.docker.com/compose/install/) >= 2.20（或内置 Compose 的 Docker Desktop）
- 至少 4GB 可用磁盘空间
- 端口 5432、8000、3000 未被占用

### 1.2 快速启动

```bash
# 克隆仓库
git clone https://github.com/your-org/ontofuel.git
cd ontofuel

# 一键启动所有服务
docker compose -f docker/docker-compose.yml up -d
```

启动后等待约 30 秒，所有服务就绪后即可访问：

| 服务 | 地址 | 说明 |
|------|------|------|
| Web 前端 | http://localhost:3000 | 材料数据浏览界面 |
| API 服务 | http://localhost:8000 | REST API |
| 数据库 | localhost:5432 | PostgreSQL |

验证服务状态：

```bash
# 检查 API 健康
curl http://localhost:8000/health

# 检查所有容器状态
docker compose -f docker/docker-compose.yml ps
```

### 1.3 服务说明

`docker-compose.yml` 定义了三个核心服务：

#### `db` — 数据库服务

- **镜像**: `supabase/postgres:15.6.1`
- **端口**: 5432
- **数据持久化**: Docker volume `db-data`
- **初始化**: 自动执行 `docker/supabase/init/` 目录下的 SQL 脚本
- **健康检查**: `pg_isready -U postgres`

#### `api` — API 服务

- **构建**: `docker/api/Dockerfile`
- **端口**: 8000
- **依赖**: `db` 服务健康后才启动
- **健康检查**: `curl -f http://localhost:8000/health`

#### `web` — 前端服务

- **构建**: `docker/web/Dockerfile`
- **端口**: 3000
- **依赖**: `api` 服务健康后才启动

### 1.4 环境变量配置

在项目根目录创建 `.env` 文件（或参考 `.env.example`）：

```bash
# 数据库配置
POSTGRES_PASSWORD=postgres
POSTGRES_DB=ontofuel

# Supabase 配置（可选）
SUPABASE_SERVICE_KEY=your-service-key

# API 连接（Docker 内部自动配置，一般无需修改）
DATABASE_URL=postgres://postgres:postgres@db:5432/ontofuel

# 数据恢复脚本配置
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=ontofuel
```

> **⚠️ 安全提示**: 生产环境务必修改 `POSTGRES_PASSWORD`，不要使用默认值。

### 1.5 数据恢复

使用 `restore.sh` 脚本从 JSON 文件恢复本体数据：

```bash
# 恢复默认数据
bash docker/scripts/restore.sh

# 指定自定义 JSON 文件
bash docker/scripts/restore.sh /path/to/custom_ontology.json
```

脚本执行流程：
1. 等待 PostgreSQL 就绪（最长 60 秒）
2. 执行 Schema 初始化 SQL
3. 从 JSON 文件导入本体数据

也可使用环境变量覆盖数据库连接参数：

```bash
DB_HOST=remote-host DB_PORT=5433 bash docker/scripts/restore.sh
```

### 1.6 常用运维命令

```bash
# 查看日志
docker compose -f docker/docker-compose.yml logs -f

# 仅查看 API 日志
docker compose -f docker/docker-compose.yml logs -f api

# 重启单个服务
docker compose -f docker/docker-compose.yml restart api

# 停止所有服务
docker compose -f docker/docker-compose.yml down

# 停止并删除数据卷（⚠️ 清空所有数据）
docker compose -f docker/docker-compose.yml down -v

# 重新构建镜像（代码更新后）
docker compose -f docker/docker-compose.yml up -d --build
```

---

## 2. 源码部署

### 2.1 环境要求

- **Python**: >= 3.10（推荐 3.11 或 3.12）
- **PostgreSQL**: >= 14（或 Supabase 实例）
- **pip** 或 **uv** 包管理器

### 2.2 安装步骤

```bash
# 克隆仓库
git clone https://github.com/your-org/ontofuel.git
cd ontofuel

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 安装（开发模式，包含测试依赖）
pip install -e ".[dev]"

# 或安装全部可选依赖
pip install -e ".[all]"
```

### 2.3 数据库配置

#### 方案 A: 使用 Docker 仅运行数据库

```bash
# 仅启动数据库容器
docker compose -f docker/docker-compose.yml up -d db

# 设置环境变量
export DATABASE_URL="postgres://postgres:postgres@localhost:5432/ontofuel"
```

#### 方案 B: 连接 Supabase 云实例

```bash
# 设置 Supabase 连接信息
export DATABASE_URL="postgres://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres"
export SUPABASE_SERVICE_KEY="your-service-key"
```

#### 方案 C: 本地 PostgreSQL

```bash
# macOS (Homebrew)
brew install postgresql@15
brew services start postgresql@15

# 创建数据库
createdb ontofuel

# 执行 Schema 初始化
psql -d ontofuel -f docker/supabase/init/01_schema.sql
```

### 2.4 验证安装

```bash
# 运行测试
pytest

# 运行 CLI
ontofuel --help
```

---

## 3. 生产环境注意事项

### 3.1 安全配置

```bash
# .env — 生产环境最小配置
POSTGRES_PASSWORD=<strong-random-password>
SUPABASE_SERVICE_KEY=<your-key>

# 禁用调试模式
DEBUG=false
```

安全检查清单：
- [ ] 修改默认数据库密码
- [ ] 限制数据库端口仅内网访问（不暴露 5432）
- [ ] API 服务启用认证
- [ ] 定期更新依赖（`pip audit`）
- [ ] 使用密钥管理服务（如 AWS Secrets Manager）

### 3.2 反向代理（Nginx）

推荐使用 Nginx 作为反向代理：

```nginx
server {
    listen 80;
    server_name ontofuel.example.com;

    # API 服务
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Web 前端
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 3.3 HTTPS

使用 Let's Encrypt 获取免费 SSL 证书：

```bash
# 安装 Certbot
apt install certbot python3-certbot-nginx  # Debian/Ubuntu

# 获取证书并自动配置 Nginx
certbot --nginx -d ontofuel.example.com

# 自动续期（Certbot 会自动添加 cron）
certbot renew --dry-run
```

### 3.4 备份策略

```bash
# PostgreSQL 逻辑备份
pg_dump -h localhost -U postgres ontofuel > backup_$(date +%Y%m%d).sql

# 使用自定义格式（推荐，支持并行恢复）
pg_dump -h localhost -U postgres -Fc ontofuel > backup_$(date +%Y%m%d).dump

# 定时备份（crontab）
# 每天凌晨 3 点备份
0 3 * * * pg_dump -h localhost -U postgres -Fc ontofuel > /backups/ontofuel_$(date +\%Y\%m\%d).dump

# 恢复备份
pg_restore -h localhost -U postgres -d ontofuel backup_20260503.dump
```

JSON 数据备份（适用于本体数据）：

```bash
# 导出当前数据为 JSON
python3 -c "import json; from ontofuel.exporter import export_ontology; export_ontology('backup.json')"
```

---

## 4. 故障排除

### 常见问题

#### 数据库连接失败

```
psycopg.OperationalError: connection refused
```

**解决方案**：
1. 检查 PostgreSQL 是否运行：`docker compose -f docker/docker-compose.yml ps db`
2. 检查端口是否被占用：`lsof -i :5432`
3. 确认 `DATABASE_URL` 环境变量正确
4. 检查 `pg_hba.conf` 允许连接

#### Docker 容器启动失败

```
ERROR: for db  Cannot start service db
```

**解决方案**：
1. 查看详细日志：`docker compose -f docker/docker-compose.yml logs db`
2. 清理旧容器和卷：`docker compose -f docker/docker-compose.yml down -v`
3. 检查 Docker 磁盘空间：`docker system df`
4. 重新拉取镜像：`docker compose -f docker/docker-compose.yml pull`

#### API 健康检查失败

```
curl: (7) Failed to connect to localhost port 8000
```

**解决方案**：
1. 确认 API 容器已启动：`docker compose -f docker/docker-compose.yml ps api`
2. 检查 API 日志：`docker compose -f docker/docker-compose.yml logs api`
3. 确认数据库已就绪（API 依赖数据库健康检查通过）
4. 手动进入容器调试：`docker compose -f docker/docker-compose.yml exec api bash`

#### 数据恢复脚本报错

```
ERROR: PostgreSQL not ready after 60 seconds
```

**解决方案**：
1. 确认数据库容器运行中：`docker compose -f docker/docker-compose.yml ps db`
2. 手动检查连接：`pg_isready -h localhost -p 5432 -U postgres`
3. 增加等待时间（修改 `restore.sh` 中的超时值）
4. 检查数据库初始化日志：`docker compose -f docker/docker-compose.yml logs db`

#### 端口冲突

```
Error: bind: address already in use
```

**解决方案**：
1. 查找占用进程：`lsof -i :5432`（或 8000、3000）
2. 修改 `.env` 或 `docker-compose.yml` 中的端口映射
3. 停止占用服务：`kill <PID>`

### 获取帮助

- 查看 [README.md](../README.md) 获取项目概览
- 查看 [用户手册](user_manual.md) 获取使用说明
- 提交 Issue 到 GitHub 仓库
