"""ScraperRunRepository 单元测试

测试爬虫运行记录仓储的数据库操作。
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from app.models.scraper_run import ScraperRun
from app.repositories.scraper_run import ScraperRunRepository


@pytest.fixture
def mock_session():
    """创建模拟的 AsyncSession"""
    session = AsyncMock()
    session.add = MagicMock()  # session.add 是同步方法
    return session


@pytest.fixture
def sample_runs():
    """示例爬虫运行记录数据"""
    return [
        ScraperRun(
            id=1,
            source="eastmoney",
            status="completed",
            started_at=datetime(2025, 3, 15, 10, 0, 0, tzinfo=timezone.utc),
            finished_at=datetime(2025, 3, 15, 10, 5, 0, tzinfo=timezone.utc),
            items_scraped=100,
            error_message=None,
        ),
        ScraperRun(
            id=2,
            source="eastmoney",
            status="failed",
            started_at=datetime(2025, 3, 14, 8, 0, 0, tzinfo=timezone.utc),
            finished_at=datetime(2025, 3, 14, 8, 1, 0, tzinfo=timezone.utc),
            items_scraped=0,
            error_message="连接超时",
        ),
        ScraperRun(
            id=3,
            source="tonghuashun",
            status="running",
            started_at=datetime(2025, 3, 15, 12, 0, 0, tzinfo=timezone.utc),
            finished_at=None,
            items_scraped=0,
            error_message=None,
        ),
    ]


class TestScraperRunRepository:
    """ScraperRunRepository 测试"""

    def test_init(self, mock_session):
        """测试初始化"""
        repo = ScraperRunRepository(mock_session)
        assert repo.session is mock_session

    @pytest.mark.asyncio
    async def test_create(self, mock_session):
        """测试创建运行记录"""
        repo = ScraperRunRepository(mock_session)

        run = await repo.create(source="eastmoney")

        # 验证 session.add 被调用
        mock_session.add.assert_called_once()
        added_run = mock_session.add.call_args[0][0]
        assert added_run.source == "eastmoney"
        assert added_run.status == "running"
        assert added_run.started_at is not None

        # 验证 flush 被调用
        mock_session.flush.assert_awaited_once()

        # 验证返回的对象
        assert run.source == "eastmoney"
        assert run.status == "running"

    @pytest.mark.asyncio
    async def test_get_found(self, mock_session, sample_runs):
        """测试获取运行记录（找到）"""
        repo = ScraperRunRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_runs[0]
        mock_session.execute.return_value = mock_result

        run = await repo.get(run_id=1)

        assert run is not None
        assert run.id == 1
        assert run.source == "eastmoney"
        assert run.status == "completed"

    @pytest.mark.asyncio
    async def test_get_not_found(self, mock_session):
        """测试获取运行记录（未找到）"""
        repo = ScraperRunRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        run = await repo.get(run_id=999)

        assert run is None

    @pytest.mark.asyncio
    async def test_update_status_found(self, mock_session):
        """测试更新状态（找到记录，running 状态不设置 finished_at）"""
        repo = ScraperRunRepository(mock_session)

        # 创建一个可修改的运行记录副本
        run_copy = ScraperRun(
            id=1,
            source="eastmoney",
            status="running",
            started_at=datetime(2025, 3, 15, 10, 0, 0, tzinfo=timezone.utc),
            finished_at=None,
            items_scraped=0,
            error_message=None,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = run_copy
        mock_session.execute.return_value = mock_result

        updated = await repo.update_status(
            run_id=1, status="running", items_scraped=50
        )

        assert updated is not None
        assert updated.status == "running"
        assert updated.items_scraped == 50
        # running 状态不设置 finished_at
        assert updated.finished_at is None
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_status_not_found(self, mock_session):
        """测试更新状态（未找到记录）"""
        repo = ScraperRunRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        updated = await repo.update_status(run_id=999, status="completed")

        assert updated is None

    @pytest.mark.asyncio
    async def test_update_status_completed_sets_finished_at(self, mock_session):
        """测试 completed 状态设置 finished_at"""
        repo = ScraperRunRepository(mock_session)

        run_copy = ScraperRun(
            id=1,
            source="eastmoney",
            status="running",
            started_at=datetime(2025, 3, 15, 10, 0, 0, tzinfo=timezone.utc),
            finished_at=None,
            items_scraped=0,
            error_message=None,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = run_copy
        mock_session.execute.return_value = mock_result

        updated = await repo.update_status(
            run_id=1, status="completed", items_scraped=200
        )

        assert updated is not None
        assert updated.status == "completed"
        assert updated.items_scraped == 200
        assert updated.finished_at is not None
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_status_failed_sets_finished_at(self, mock_session):
        """测试 failed 状态设置 finished_at"""
        repo = ScraperRunRepository(mock_session)

        run_copy = ScraperRun(
            id=1,
            source="eastmoney",
            status="running",
            started_at=datetime(2025, 3, 15, 10, 0, 0, tzinfo=timezone.utc),
            finished_at=None,
            items_scraped=0,
            error_message=None,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = run_copy
        mock_session.execute.return_value = mock_result

        updated = await repo.update_status(
            run_id=1, status="failed", error_message="网络异常"
        )

        assert updated is not None
        assert updated.status == "failed"
        assert updated.error_message == "网络异常"
        assert updated.finished_at is not None
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_by_source_with_filter(self, mock_session, sample_runs):
        """测试按数据源筛选"""
        repo = ScraperRunRepository(mock_session)

        eastmoney_runs = [r for r in sample_runs if r.source == "eastmoney"]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = eastmoney_runs
        mock_session.execute.return_value = mock_result

        runs = await repo.list_by_source(source="eastmoney")

        assert len(runs) == 2
        assert all(r.source == "eastmoney" for r in runs)

    @pytest.mark.asyncio
    async def test_list_by_source_no_filter(self, mock_session, sample_runs):
        """测试不筛选数据源（返回全部）"""
        repo = ScraperRunRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_runs
        mock_session.execute.return_value = mock_result

        runs = await repo.list_by_source()

        assert len(runs) == 3

    @pytest.mark.asyncio
    async def test_list_by_source_empty_result(self, mock_session):
        """测试空结果"""
        repo = ScraperRunRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        runs = await repo.list_by_source(source="nonexistent")

        assert len(runs) == 0
