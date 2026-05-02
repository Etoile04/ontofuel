#!/usr/bin/env bash
# OntoFuel HTTP Server launchd 管理脚本
# 用法: ./install_http_server.sh [install|uninstall|status|healthcheck]

set -euo pipefail

PLIST_NAME="com.ontofuel.http-server"
PLIST_SRC="$(cd "$(dirname "$0")/.." && pwd)/${PLIST_NAME}.plist"
PLIST_DST="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"
PORT=9999

info()  { echo "ℹ️  $*"; }
ok()    { echo "✅ $*"; }
warn()  { echo "⚠️  $*" >&2; }
die()   { echo "❌ $*" >&2; exit 1; }

check_prereqs() {
    [[ -f "$PLIST_SRC" ]] || die "plist 源文件不存在: $PLIST_SRC"
    command -v launchctl &>/dev/null || die "launchctl 未找到"
}

do_install() {
    check_prereqs

    # 如果已加载，先卸载
    if launchctl list "$PLIST_NAME" &>/dev/null; then
        info "服务已加载，先卸载..."
        do_uninstall_silent
    fi

    # 拷贝 plist
    info "安装 plist → $PLIST_DST"
    cp "$PLIST_SRC" "$PLIST_DST"

    # 修复 WorkingDirectory 为当前工作区路径
    WORKSPACE="$(cd "$(dirname "$0")/.." && pwd)"
    sed -i '' "s|/Users/lwj04/.openclaw/workspace-extractor|${WORKSPACE}|g" "$PLIST_DST"

    # 加载
    launchctl load "$PLIST_DST"
    sleep 1

    # 验证
    if launchctl list "$PLIST_NAME" &>/dev/null; then
        ok "服务已加载: $PLIST_NAME"
    else
        die "服务加载失败"
    fi

    # 健康检查
    do_healthcheck
}

do_uninstall_silent() {
    launchctl unload "$PLIST_DST" 2>/dev/null || true
    rm -f "$PLIST_DST"
}

do_uninstall() {
    if ! launchctl list "$PLIST_NAME" &>/dev/null && [[ ! -f "$PLIST_DST" ]]; then
        warn "服务未安装"
        return
    fi

    do_uninstall_silent
    ok "服务已卸载: $PLIST_NAME"
}

do_status() {
    if launchctl list "$PLIST_NAME" &>/dev/null; then
        info "服务状态: 已加载"
        local pid
        pid=$(launchctl list "$PLIST_NAME" 2>/dev/null | grep PID | awk '{print $NF}')
        [[ -n "$pid" && "$pid" != "-" ]] && info "PID: $pid"
    else
        info "服务状态: 未加载"
    fi

    if curl -s -o /dev/null -w "%{http_code}" "http://localhost:${PORT}" 2>/dev/null | grep -q "200"; then
        ok "HTTP 服务可访问: http://localhost:${PORT}"
    else
        warn "HTTP 服务不可访问: http://localhost:${PORT}"
    fi
}

do_healthcheck() {
    local retries=5
    local i
    for ((i = 1; i <= retries; i++)); do
        if curl -s -o /dev/null -w "%{http_code}" "http://localhost:${PORT}" 2>/dev/null | grep -q "200"; then
            ok "健康检查通过: http://localhost:${PORT} (尝试 ${i}/${retries})"
            return 0
        fi
        info "等待服务启动... (${i}/${retries})"
        sleep 1
    done
    warn "健康检查失败: http://localhost:${PORT} 无响应"
    return 1
}

case "${1:-status}" in
    install|i)   do_install ;;
    uninstall|u) do_uninstall ;;
    status|s)    do_status ;;
    healthcheck|h) do_healthcheck ;;
    *)
        echo "用法: $0 {install|uninstall|status|healthcheck}"
        echo ""
        echo "  install      安装并启动 HTTP 服务"
        echo "  uninstall    停止并卸载 HTTP 服务"
        echo "  status       查看服务状态"
        echo "  healthcheck  检查 HTTP 服务可访问性"
        exit 1
        ;;
esac
