"""导入机器人知识图谱并清理伪三等分数据。"""

import asyncio

from app.core.database import AsyncSessionLocal
from app.services.concept_graph_importer import (
    import_robotics_graph,
    remove_generated_equal_split_chains,
)


async def main() -> None:
    async with AsyncSessionLocal() as session:
        removed = await remove_generated_equal_split_chains(session)
        result = await import_robotics_graph(session)
        print({"removed_generated_chains": removed, **result})


if __name__ == "__main__":
    asyncio.run(main())
