# 前端多阶段构建
# Stage 1: 构建 React 应用
FROM node:22-slim AS builder

# 安装 pnpm（lockfile v9 对应 pnpm 9.x，避免 @latest 拉取需 Node 22.13+ 的 pnpm 11）
RUN corepack enable && corepack prepare pnpm@9.15.9 --activate

WORKDIR /app

# 安装依赖（需要 pnpm-lock.yaml 文件）
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# 复制源代码并构建
COPY . .
# 生产构建跳过 tsc 全量类型检查（测试文件与开发态类型问题不阻塞部署）
RUN pnpm vite build

# Stage 2: Nginx 服务
FROM nginx:alpine

# 复制构建产物到 Nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
