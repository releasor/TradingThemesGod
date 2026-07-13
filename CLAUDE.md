### Project Conventions

- 语言：代码用英文命名，注释和文档用中文
- 代码格式化：Python 用 Black + Ruff，React 用 ESLint + Prettier
- 错误处理：统一错误响应格式，全局异常处理，用户友好的中文错误提示
- 测试：核心功能有单元测试，覆盖率适中
- API 风格：RESTful API，标准 HTTP 方法
- 前端状态管理：Zustand
- 图表库：ECharts
- 爬虫策略：完善的反爬机制（IP 轮换、UA 轮换、自动重试、降级策略）
- 数据更新：增量更新，避免重复抓取
- 部署：本地/自建服务器

### Infrastructure

#### Database
- **Type**: PostgreSQL
- **ORM**: SQLAlchemy
- **Table naming**: snake_case，无前缀
- **Field naming**: snake_case；通用字段：created_at, updated_at
- **Primary key**: 自增整数
- **Migration directory**: alembic/versions/
- **Migration naming**: 序号前缀（如 001_create_themes）
- **Index naming**: idx_{table}_{column}
- **Environment separation**: .env 文件管理（dev/test/prod）

#### Deployment
- **Target**: 本地/自建服务器，Docker 部署
- **AI-assisted deploy**: 否
- **Domain**: 未配置
- **SSL**: 未配置
- **CI/CD**: 未配置
- **Env var management**: .env 文件

#### Cloud Services
- **Vendors**: 无
<!-- cloud-services: none -->

@./CLAUDE.private.md
