# Concept Knowledge Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为题材增加可递归下钻、可追溯并能关联真实股票的深度概念图谱，先完整落地机器人样板。

**Architecture:** 使用自关联 `concept_nodes` 表表达任意深度概念树，使用 `concept_node_stocks` 表记录股票关联理由。后端批量加载后构树，前端用递归组件展示；旧产业链接口保持兼容但停用本地均分生成器。

**Tech Stack:** FastAPI、SQLAlchemy 2、Alembic、MySQL、Pydantic 2、React、TanStack Query、Tailwind CSS、Vitest。

---

### Task 1: 数据模型与迁移

**Files:**
- Create: `backend/app/models/concept_node.py`
- Create: `backend/app/models/concept_node_stock.py`
- Create: `backend/alembic/versions/007_create_concept_graph.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/unit/test_concept_graph_models.py`

- [ ] 先编写模型元数据测试，断言自关联外键、复合主键和索引存在。
- [ ] 运行模型测试并确认因模型不存在而失败。
- [ ] 实现两个模型与迁移，字段严格匹配设计文档。
- [ ] 运行模型测试并确认通过。

### Task 2: 图谱查询与 API 契约

**Files:**
- Create: `backend/app/repositories/concept_graph.py`
- Create: `backend/app/schemas/concept_graph.py`
- Create: `backend/app/services/concept_graph.py`
- Modify: `backend/app/schemas/theme.py`
- Modify: `backend/app/services/theme.py`
- Test: `backend/tests/unit/test_concept_graph_service.py`

- [ ] 编写乱序扁平节点构建递归树、空图谱和关联股票的失败测试。
- [ ] 实现批量查询和 `build_concept_tree`，按 `sort_order`、`id` 稳定排序。
- [ ] 在题材详情响应增加 `concept_graph`，无数据时返回空结构。
- [ ] 运行服务和题材 API 测试。

### Task 3: 机器人版本化知识包

**Files:**
- Create: `backend/app/knowledge/__init__.py`
- Create: `backend/app/knowledge/robotics.py`
- Create: `backend/app/services/concept_graph_importer.py`
- Create: `backend/scripts/seed_concept_graph.py`
- Test: `backend/tests/unit/test_concept_graph_importer.py`

- [ ] 编写路径 `机器人 > 灵巧手 > 传感 > 电子皮肤` 和股票代码幂等关联测试。
- [ ] 定义机器人多层节点、描述、逻辑、催化、风险、来源及股票关联理由。
- [ ] 实现按稳定路径 upsert 节点、按股票代码 upsert 关联；缺失股票记录警告并跳过。
- [ ] 运行导入器测试并执行真实数据库导入。

### Task 4: 清理本地均分数据

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/scrapers/registry.py`
- Modify: `backend/app/scrapers/local_chain.py`
- Test: `backend/tests/unit/test_scraper_registry.py`

- [ ] 编写默认注册与启动流程不运行 `local_chain` 的失败测试。
- [ ] 移除启动调用和默认注册，保留模块仅供识别旧数据。
- [ ] 在导入脚本中仅删除 `source=local_chain` 或明确本地推导描述的记录，并清空相应均分标签。
- [ ] 验证外部可信产业链记录不受影响。

### Task 5: 前端递归图谱

**Files:**
- Create: `frontend/src/components/ConceptGraphSection.tsx`
- Create: `frontend/src/components/ConceptTreeNode.tsx`
- Modify: `frontend/src/types/theme.ts`
- Modify: `frontend/src/features/themes/ThemeDetail.tsx`
- Test: `frontend/src/components/ConceptGraphSection.test.tsx`

- [ ] 编写多层展开、全部展开、过滤和股票理由展示测试。
- [ ] 增加与后端一致的递归 TypeScript 类型。
- [ ] 实现紧凑、工作台式递归树，使用图标按钮和可访问的展开状态。
- [ ] 将图谱放到成分股之前；只在真实链路数据存在时显示旧饼图和三列区。
- [ ] 运行前端组件与题材详情测试。

### Task 6: 全链路验证

**Files:**
- Test: `backend/tests/integration/test_theme_api.py`
- Test: `frontend/src/features/themes/ThemeDetail.test.tsx`

- [ ] 运行 Alembic 升级并导入机器人知识包。
- [ ] 验证 API 返回至少四层机器人路径、电子皮肤和福莱新材关联理由。
- [ ] 运行后端 Ruff、相关 Pytest、前端 ESLint、Vitest 和生产构建。
- [ ] 使用 Playwright 检查桌面和移动端展开、过滤、股票跳转及无重叠。
