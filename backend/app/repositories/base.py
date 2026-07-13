"""仓储基类

提供通用的数据库查询辅助方法，减少重复代码。
"""

from sqlalchemy import Select, func, desc, asc, select
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
        default_sort_column=None,
        sort_column=None,
        sort_order: str = "desc",
    ) -> tuple[list, int]:
        """通用分页查询

        将 count + sort + offset/limit + execute 封装为一个方法，
        消除各仓储中重复的分页逻辑。

        Args:
            query: 基础 SELECT 查询（已包含 WHERE 条件）
            page: 页码（从 1 开始）
            page_size: 每页数量
            default_sort_column: 默认排序列（当 sort_column 为 None 时使用）
            sort_column: 实际排序列
            sort_order: 排序方向 "asc" 或 "desc"

        Returns:
            (数据列表, 总数) 元组
        """
        # 计算总数
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_query)).scalar() or 0

        # 应用排序
        order_col = sort_column or default_sort_column
        if order_col is not None:
            if sort_order == "desc":
                query = query.order_by(desc(order_col))
            else:
                query = query.order_by(asc(order_col))

        # 应用分页
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # 执行查询
        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return items, total
