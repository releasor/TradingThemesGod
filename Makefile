.PHONY: up down logs build migrate clean restart status

# 启动所有服务
up:
	docker compose up -d

# 停止所有服务
down:
	docker compose down

# 查看日志
logs:
	docker compose logs -f

# 查看指定服务日志
logs-backend:
	docker compose logs -f backend

logs-frontend:
	docker compose logs -f frontend

logs-db:
	docker compose logs -f db

# 构建镜像
build:
	docker compose build

# 运行数据库迁移
migrate:
	docker compose exec backend alembic upgrade head

# 创建新的迁移文件
migrate-create:
	docker compose exec backend alembic revision --autogenerate -m "$(name)"

# 停止并清理所有数据
clean:
	docker compose down -v

# 重启服务
restart:
	docker compose restart

# 查看服务状态
status:
	docker compose ps

# 进入后端容器
shell-backend:
	docker compose exec backend bash

# 进入数据库容器
shell-db:
	docker compose exec db mysql -u root -p$${MYSQL_ROOT_PASSWORD:-mysql} $${MYSQL_DATABASE:-trading_themes}
