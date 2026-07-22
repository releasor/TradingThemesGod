# 后端多阶段构建
# Stage 1: 安装依赖
FROM python:3.12-slim AS builder

WORKDIR /app

# 使用国内镜像加速 apt（腾讯云服务器）
RUN sed -i 's/deb.debian.org/mirrors.tencent.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's/deb.debian.org/mirrors.tencent.com/g' /etc/apt/sources.list

# 仅需 gcc 编译少量 Python 原生扩展（项目使用 MySQL/asyncmy，无需 libpq）
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -i https://mirrors.cloud.tencent.com/pypi/simple .

# Stage 2: 运行时
FROM python:3.12-slim

WORKDIR /app

RUN sed -i 's/deb.debian.org/mirrors.tencent.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's/deb.debian.org/mirrors.tencent.com/g' /etc/apt/sources.list

# 运行时仅需 curl（健康检查）
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# 从 builder 阶段复制已安装的 Python 包
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制应用代码
COPY . .

# 复制启动脚本
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# 使用启动脚本
ENTRYPOINT ["/entrypoint.sh"]
