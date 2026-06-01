#!/bin/bash
# TicketPilot 全栈启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 启动 TicketPilot AI 客服 Copilot"
echo "===================================="

# 检查 Python 虚拟环境
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo "❌ Python 虚拟环境不存在，请先运行 uv sync"
    exit 1
fi

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安装"
    exit 1
fi

# 检查前端依赖
if [ ! -d "$SCRIPT_DIR/node_modules" ]; then
    echo "📦 安装前端依赖..."
    cd "$SCRIPT_DIR" && npm install
fi

# 启动后端 API
echo "🔧 启动 FastAPI 后端 (端口 8000)..."
cd "$PROJECT_DIR"
PYTHONPATH=src:$PYTHONPATH python3 -m uvicorn ticketpilot.api:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload &
BACKEND_PID=$!

# 等待后端启动
sleep 3

# 启动前端
echo "🎨 启动 React 前端 (端口 3000)..."
cd "$SCRIPT_DIR"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "===================================="
echo "✅ TicketPilot 已启动"
echo "===================================="
echo ""
echo "📍 前端: http://localhost:3000"
echo "📍 API:  http://localhost:8000"
echo "📍 文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo ""

# 捕获退出信号
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

# 等待
wait