# MySQL 迁移设计

## 目标

将 TradingThemesGod 的唯一数据库从 PostgreSQL 切换到本机 MySQL 8.0，同时保持现有 API、数据模型和前端行为不变。当前没有需要保留的数据，因此通过空库重新执行 Alembic 迁移建表，不提供 PostgreSQL 数据搬运工具。

## 范围

- 后端使用 SQLAlchemy 异步引擎和 `asyncmy` 驱动连接 MySQL。
- SQLAlchemy 模型中的 PostgreSQL `JSONB` 改为通用 `JSON`。
- 标签筛选从 PostgreSQL JSONB contains 改为 MySQL `JSON_CONTAINS`。
- Alembic 迁移改为 MySQL 8 可执行的 DDL 和索引。
- 本地环境示例、Docker Compose、Makefile 和后端依赖统一切换到 MySQL。
- 数据库和表使用 `utf8mb4` 字符集及 `utf8mb4_0900_ai_ci` 排序规则。
- 保留现有分页、排序、软删除、关键词搜索和 JSON 字段的 API 语义。

不在本次范围内：

- PostgreSQL 与 MySQL 双数据库兼容。
- PostgreSQL 历史数据迁移。
- 将 JSON 标签拆分为关系表。
- 引入 MySQL FULLTEXT 中文分词。现有名称和描述搜索继续使用包含式 `LIKE` 语义。

## 数据库连接

配置项继续使用现有 `DB_HOST`、`DB_PORT`、`DB_NAME`、`DB_USER` 和 `DB_PASSWORD`，默认值改为本机 MySQL：

- Host: `localhost`
- Port: `3306`
- Database: `trading_themes`
- User: `root`
- Charset: `utf8mb4`

运行时 URL 为 `mysql+asyncmy://.../trading_themes?charset=utf8mb4`。用户名和密码必须通过 SQLAlchemy URL 构造 API 编码，确保密码中的 `@`、`:` 等字符不会破坏连接字符串。

Alembic 继续使用异步迁移环境和同一个 `asyncmy` URL，避免额外引入同步 MySQL 驱动。

MySQL 驱动的连接参数与 asyncpg 不同。引擎保留连接池预检、回收和容量配置，移除 `command_timeout` 等 asyncpg 专用参数，使用 asyncmy 支持的连接超时参数。

## 模型与查询

`themes.tags` 和 `industry_chains.representative_companies` 使用 SQLAlchemy `JSON` 类型。Python 层继续接受当前已有的列表或对象值，不改变响应 Schema。

标签筛选要求请求中的每个标签都存在于 `themes.tags` JSON 数组中。每个标签生成一个 MySQL `JSON_CONTAINS(tags, JSON_QUOTE(:tag))` 条件，多个条件使用 AND 组合，与当前 PostgreSQL 行为一致。值通过绑定参数传入，不拼接 SQL。

关键词搜索保持名称或描述包含关键词的行为。MySQL 8 的 `utf8mb4_0900_ai_ci` 默认不区分大小写，因此使用转义后的 `LIKE` 即可维持预期语义。`%`、`_` 和反斜杠仍需转义。

## Schema 与索引

现有迁移历史直接改写为 MySQL 版本，因为没有已部署数据或需要延续的 PostgreSQL Alembic 状态：

- `JSONB` 列改为 `JSON`。
- 删除 GIN 标签索引。
- PostgreSQL 部分索引改为普通 `deleted_at` 索引。
- 排名、事件时间和抓取任务索引保留为 MySQL 普通或复合 B-tree 索引。
- 删除 `postgresql_using`、`postgresql_ops`、`CREATE EXTENSION pg_trgm` 和 trigram GIN DDL。
- 原 `005` 迁移保留 revision 链，但调整为 MySQL 可执行的名称/描述索引迁移，避免迁移编号断裂。

不会为 JSON 数组建立普通索引，因为 MySQL 普通 B-tree 不能直接加速任意 JSON 数组成员查询。当前数据规模未知，先保持正确性；出现可测量的性能瓶颈后，再评估多值索引或标签关系表。

所有表通过迁移设置 `mysql_charset=utf8mb4` 和 `mysql_collate=utf8mb4_0900_ai_ci`。主键和外键结构保持不变，继续使用 InnoDB。

## 运行与部署配置

后端依赖删除 `asyncpg`，增加 `asyncmy`。根目录和后端 `.env.example` 改为 MySQL 默认项。

Docker Compose 的数据库服务同步改为 MySQL 8，使用 MySQL 环境变量、3306 端口、健康检查和 MySQL 数据卷。Makefile 的数据库 shell 命令改为 `mysql` 客户端。虽然本次目标是本机直接运行，但同步维护这些入口可防止仓库存在两套相互冲突的数据库定义。

本地启动流程为：创建 `trading_themes` 空库，填写 `backend/.env`，执行 `alembic upgrade head`，再启动 Uvicorn。前端启动方式不变。

## 错误处理

- 数据库不可达或凭据错误时，由 SQLAlchemy/asyncmy 抛出连接错误，应用健康检查返回数据库异常状态。
- Alembic 建表失败时立即停止，不继续启动应用。
- JSON 标签查询只接受现有 Schema 验证后的标签字符串，并使用绑定参数防止注入。
- 不自动删除或覆盖用户已有的 MySQL 数据库；用户创建空库后再执行迁移。

## 测试与验证

测试按以下层次覆盖：

1. 配置单元测试验证默认 MySQL 参数、URL 方言、字符集和特殊字符编码。
2. SQL 编译测试验证标签条件编译为 MySQL `JSON_CONTAINS`，且标签值使用绑定参数。
3. 模型和现有服务、仓储、API 单元测试验证行为没有回归。
4. Alembic 使用本机 MySQL 空库执行 `upgrade head`，确认全部表和索引可创建。
5. 启动后端并访问 `/api/v1/health` 与 `/docs`，确认应用连接数据库并正常提供接口。

如本机 MySQL root 密码无法从环境中获得，自动化验证会完成不依赖真实连接的测试，并提供需要用户执行的建库、迁移和启动命令。

## 回滚

代码回滚通过恢复迁移前提交完成。由于没有 PostgreSQL 历史数据，本次不提供跨数据库回滚脚本。MySQL 中若已产生测试数据，回滚代码前应先备份；任何删除数据库或清空数据的操作必须由用户明确执行。
