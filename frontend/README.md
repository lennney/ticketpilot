# TicketPilot Frontend

React + TypeScript + Vite 前端，用于 TicketPilot AI 客服 Copilot。

## 快速开始

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 或者一键启动全栈（包含后端）
bash start.sh
```

## 技术栈

- **React 18** - UI 框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具
- **CSS Variables** - 样式系统

## 功能特性

- 💬 **多轮对话** - 支持上下文的客服对话
- 📚 **证据面板** - 实时显示检索到的知识库证据
- ⚠️ **风险标记** - 高风险对话自动标记和提醒
- 🎯 **意图分类** - 自动识别客服意图
- 📊 **置信度** - 显示分类和检索的置信度

## 目录结构

```
frontend/
├── src/
│   ├── App.tsx          # 主应用组件
│   ├── main.tsx         # 入口文件
│   └── index.css        # 全局样式
├── public/
│   └── vite.svg         # 图标
├── index.html           # HTML 模板
├── vite.config.ts       # Vite 配置
├── tsconfig.json        # TypeScript 配置
└── start.sh             # 全栈启动脚本
```

## API 代理

开发模式下，Vite 会自动将 `/api/*` 请求代理到后端 `http://localhost:8000`。

## 构建部署

```bash
# 构建生产版本
npm run build

# 预览构建结果
npm run preview
```

构建产物在 `dist/` 目录，可以部署到任何静态文件服务器。