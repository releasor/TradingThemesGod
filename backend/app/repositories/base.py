"""仓储基类

提供通用的数据库查询辅助方法，减少重复代码。
"""

from sqlalchemy import Select, asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    """仓储基类"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _paginate(
        self,
        query: Select,
        page: int = 1,
        page_size: int = 20,
        sort_column=None,
        sort_order: str = "desc",
    ) -> tuple[list, int]:
        """通用分页查询

        将 count + sort + offset/limit + execute 封装为一个方法，
        消除各仓储中重复的分页逻辑。
        同一个 AsyncSession 不支持并发查询，因此顺序执行 count 和数据查询。

        Args:
            query: 基础 SELECT 查询（已包含 WHERE 条件）
            page: 页码（从 1 开始）
            page_size: 每页数量
            sort_column: 排序列
            sort_order: 排序方向 "asc" 或 "desc"

        Returns:
            (数据列表, 总数) 元组
        """
        # 构建 count 查询
        count_query = select(func.count()).select_from(query.subquery())

        # 应用排序
        if sort_column is not None:
            if sort_order == "desc":
                data_query = query.order_by(desc(sort_column))
            else:
                data_query = query.order_by(asc(sort_column))
        else:
            data_query = query

        # 应用分页
        offset = (page - 1) * page_size
        data_query = data_query.offset(offset).limit(page_size)

        # 同一会话必须顺序执行，避免 SQLAlchemy 并发状态异常
        count_result = await self.session.execute(count_query)
        data_result = await self.session.execute(data_query)

        total = count_result.scalar() or 0
        items = list(data_result.scalars().all())

        return items, total
