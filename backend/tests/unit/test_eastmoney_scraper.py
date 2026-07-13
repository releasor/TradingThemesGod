"""东方财富题材爬虫单元测试"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.scrapers.eastmoney import EastMoneyScraper


@pytest.fixture
def scraper():
    """创建爬虫实例"""
    return EastMoneyScraper()


@pytest.fixture
def mock_middleware():
    """创建模拟中间件"""
    middleware = AsyncMock()
    return middleware


@pytest.fixture
def sample_theme_list_response():
    """示例题材列表 API 响应"""
    return {
        "data": {
            "diff": [
                {
                    "f3": 2.5,  # 涨跌幅
                    "f8": 85.6,  # 热度指数
                    "f12": "BK0XXX",  # 题材代码
                    "f14": "锂电池",  # 题材名称
                    "f104": 50,  # 关联股票数量
                },
                {
                    "f3": -1.2,
                    "f8": 92.3,
                    "f12": "BK0YYY",
                    "f14": "人工智能",
                    "f104": 30,
                },
            ]
        }
    }


@pytest.fixture
def sample_theme_stocks_response():
    """示例题材股票 API 响应"""
    return {
        "data": {
            "diff": [
                {
                    "f2": 15.68,  # 当前价格
                    "f3": 3.2,  # 涨跌幅
                    "f12": "000001",  # 股票代码
                    "f14": "平安银行",  # 股票名称
                },
                {
                    "f2": 28.95,
                    "f3": -0.8,
                    "f12": "000002",
                    "f14": "万科A",
                },
            ]
        }
    }


class TestParseThemeList:
    """测试题材列表解析"""

    def test_parse_theme_list_success(self, scraper, sample_theme_list_response):
        """测试成功解析题材列表"""
        themes = scraper.parse_theme_list(sample_theme_list_response)

        assert len(themes) == 2
        assert themes[0]["name"] == "锂电池"
        assert themes[0]["code"] == "BK0XXX"
        assert themes[0]["heat_index"] == Decimal("85.6")
        assert themes[0]["rise_fall_pct"] == Decimal("2.5")
        assert themes[0]["stock_count"] == 50

    def test_parse_theme_list_empty(self, scraper):
        """测试空题材列表"""
        themes = scraper.parse_theme_list({"data": {"diff": []}})
        assert themes == []

    def test_parse_theme_list_missing_data(self, scraper):
        """测试缺少数据字段"""
        themes = scraper.parse_theme_list({})
        assert themes == []

    def test_parse_theme_list_invalid_item(self, scraper):
        """测试无效题材数据"""
        data = {
            "data": {
                "diff": [
                    {"f12": "", "f14": ""},  # 缺少必填字段
                    {"f12": "BK0XXX", "f14": "锂电池", "f3": 2.5, "f8": 85.6, "f104": 50},
                ]
            }
        }
        themes = scraper.parse_theme_list(data)
        assert len(themes) == 1  # 只有有效的题材被解析


class TestParseThemeStocks:
    """测试题材股票解析"""

    def test_parse_theme_stocks_success(self, scraper, sample_theme_stocks_response):
        """测试成功解析题材股票"""
        stocks = scraper.parse_theme_stocks(sample_theme_stocks_response, "BK0XXX")

        assert len(stocks) == 2
        assert stocks[0]["code"] == "000001"
        assert stocks[0]["name"] == "平安银行"
        assert stocks[0]["current_price"] == Decimal("15.68")
        assert stocks[0]["rise_fall_pct"] == Decimal("3.2")

    def test_parse_theme_stocks_empty(self, scraper):
        """测试空股票列表"""
        stocks = scraper.parse_theme_stocks({"data": {"diff": []}}, "BK0XXX")
        assert stocks == []

    def test_parse_theme_stocks_missing_data(self, scraper):
        """测试缺少数据字段"""
        stocks = scraper.parse_theme_stocks({}, "BK0XXX")
        assert stocks == []


class TestExtractCategory:
    """测试分类提取"""

    def test_extract_category_new_energy(self, scraper):
        """测试新能源分类"""
        assert scraper._extract_category("锂电池") == "新能源"
        assert scraper._extract_category("光伏概念") == "新能源"
        assert scraper._extract_category("储能") == "新能源"

    def test_extract_category_tech(self, scraper):
        """测试科技分类"""
        assert scraper._extract_category("芯片概念") == "科技"
        assert scraper._extract_category("人工智能") == "科技"
        assert scraper._extract_category("5G概念") == "科技"

    def test_extract_category_medical(self, scraper):
        """测试医药分类"""
        assert scraper._extract_category("医药生物") == "医药"
        assert scraper._extract_category("医疗器械") == "医药"

    def test_extract_category_other(self, scraper):
        """测试其他分类"""
        assert scraper._extract_category("未知题材") == "其他"


class TestEastMoneyScraperRun:
    """测试爬虫主流程"""

    @pytest.mark.asyncio
    async def test_run_success(self, scraper, mock_middleware, sample_theme_list_response, sample_theme_stocks_response):
        """测试成功运行爬虫"""
        # 设置模拟中间件
        scraper.middleware = mock_middleware

        # 模拟 API 响应
        mock_response = MagicMock()
        mock_response.json.return_value = sample_theme_list_response
        mock_middleware.get.return_value = mock_response

        # 模拟数据库操作
        with patch("app.scrapers.eastmoney.AsyncSessionLocal") as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance

            # 模拟查询结果
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session_instance.execute.return_value = mock_result

            # 运行爬虫
            themes, count = await scraper.run()

            # 验证结果
            assert len(themes) == 2
            assert count > 0

    @pytest.mark.asyncio
    async def test_run_network_error(self, scraper, mock_middleware):
        """测试网络错误恢复"""
        # 设置模拟中间件
        scraper.middleware = mock_middleware

        # 模拟网络错误
        mock_middleware.get.side_effect = Exception("Network error")

        # 运行爬虫应该抛出异常
        with pytest.raises(Exception, match="Network error"):
            await scraper.run()

    @pytest.mark.asyncio
    async def test_run_empty_response(self, scraper, mock_middleware):
        """测试空响应处理"""
        # 设置模拟中间件
        scraper.middleware = mock_middleware

        # 模拟空响应
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"diff": []}}
        mock_middleware.get.return_value = mock_response

        # 运行爬虫
        themes, count = await scraper.run()

        # 验证结果
        assert themes == []
        assert count == 0
