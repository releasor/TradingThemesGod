"""东方财富题材爬虫单元测试"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.scrapers.eastmoney import (
    DEFAULT_PARAMS,
    EASTMONEY_API_BASE,
    EASTMONEY_API_FALLBACK_BASE,
    EastMoneyScraper,
)


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
                    {
                        "f12": "BK0XXX",
                        "f14": "锂电池",
                        "f3": 2.5,
                        "f8": 85.6,
                        "f104": 50,
                    },
                ]
            }
        }
        themes = scraper.parse_theme_list(data)
        assert len(themes) == 1  # 只有有效的题材被解析

    def test_parse_theme_list_preserves_missing_market_values(self, scraper):
        """来源缺失的行情字段应标记为空，不能伪装成真实的零值。"""
        themes = scraper.parse_theme_list(
            {
                "data": {
                    "diff": [
                        {
                            "f3": "-",
                            "f8": None,
                            "f12": "BK0XXX",
                            "f14": "测试题材",
                            "f104": "-",
                        }
                    ]
                }
            }
        )

        assert themes[0]["heat_index"] is None
        assert themes[0]["rise_fall_pct"] is None
        assert themes[0]["stock_count"] is None


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

    def test_parse_theme_stocks_handles_missing_market_values(self, scraper):
        """停牌或缺失行情不应导致整个题材的成分股解析失败"""
        data = {
            "data": {
                "diff": [
                    {
                        "f2": "-",
                        "f3": None,
                        "f12": "000003",
                        "f14": "测试股票",
                    }
                ]
            }
        }

        stocks = scraper.parse_theme_stocks(data, "BK0XXX")

        assert stocks == [
            {
                "code": "000003",
                "name": "测试股票",
                "rise_fall_pct": None,
                "current_price": None,
            }
        ]

    def test_parse_theme_stocks_maps_industry_and_market_cap(self, scraper):
        data = {
            "data": {
                "diff": [
                    {
                        "f2": 10.5,
                        "f3": 1.2,
                        "f12": "600000",
                        "f14": "浦发银行",
                        "f20": 297088000000,
                        "f100": "银行",
                    }
                ]
            }
        }

        stocks = scraper.parse_theme_stocks(data, "BK0000")

        assert stocks[0]["market_cap"] == Decimal("297088000000")
        assert stocks[0]["industry"] == "银行"


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
    async def test_save_theme_stocks_updates_actual_stock_count(self, scraper):
        """题材股票数量应以实际采集到的成分股为准"""
        theme = MagicMock()
        theme.id = 1
        theme.stock_count = 99

        theme_result = MagicMock()
        theme_result.scalar_one_or_none.return_value = theme
        stocks_result = MagicMock()
        stocks_result.scalars.return_value.all.return_value = []

        session = AsyncMock()
        session.execute.side_effect = [theme_result, stocks_result]
        session.add = MagicMock()

        with patch("app.scrapers.eastmoney.AsyncSessionLocal") as session_factory:
            session_factory.return_value.__aenter__.return_value = session
            saved_count = await scraper._save_theme_stocks(
                "BK0XXX",
                [
                    {
                        "code": "000001",
                        "name": "测试股票一",
                        "rise_fall_pct": Decimal("1.2"),
                        "current_price": Decimal("10.5"),
                    },
                    {
                        "code": "000002",
                        "name": "测试股票二",
                        "rise_fall_pct": Decimal("-0.5"),
                        "current_price": Decimal("8.8"),
                    },
                ],
            )

        assert saved_count == 2
        assert theme.stock_count == 2
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_save_theme_stocks_clears_stale_quote_when_snapshot_is_missing(
        self, scraper
    ):
        """本轮停牌或行情缺失时，不得沿用上一轮涨跌幅参与市场统计。"""
        theme = MagicMock(id=1, stock_count=1)
        stock = MagicMock(
            id=2,
            code="000001",
            current_price=Decimal("10.5"),
            rise_fall_pct=Decimal("2.1"),
        )
        theme_result = MagicMock()
        theme_result.scalar_one_or_none.return_value = theme
        stock_result = MagicMock()
        stock_result.scalars.return_value.all.return_value = [stock]
        relation_result = MagicMock()
        relation_result.scalars.return_value.all.return_value = []
        session = AsyncMock()
        session.execute.side_effect = [theme_result, stock_result, relation_result]
        session.add = MagicMock()

        with patch("app.scrapers.eastmoney.AsyncSessionLocal") as session_factory:
            session_factory.return_value.__aenter__.return_value = session
            await scraper._save_theme_stocks(
                "BK0XXX",
                [
                    {
                        "code": "000001",
                        "name": "测试股票",
                        "rise_fall_pct": None,
                        "current_price": None,
                    }
                ],
            )

        assert stock.current_price is None
        assert stock.rise_fall_pct is None

    @pytest.mark.asyncio
    async def test_save_themes_updates_existing_theme_by_code(self, scraper):
        """题材名称变化时仍应按稳定代码更新已有记录"""
        existing_theme = MagicMock()
        existing_theme.code = "BK1183"
        existing_theme.name = "旧名称"

        result = MagicMock()
        result.scalars.return_value.all.return_value = [existing_theme]
        session = AsyncMock()
        session.execute.return_value = result
        session.add = MagicMock()

        with patch("app.scrapers.eastmoney.AsyncSessionLocal") as session_factory:
            session_factory.return_value.__aenter__.return_value = session
            saved_count = await scraper._save_themes(
                [
                    {
                        "name": "谷子经济",
                        "code": "BK1183",
                        "heat_index": Decimal("1.43"),
                        "rise_fall_pct": Decimal("2.01"),
                        "stock_count": 64,
                        "category": "其他",
                        "source": "eastmoney",
                    }
                ]
            )

        assert saved_count == 1
        assert existing_theme.name == "谷子经济"
        session.add.assert_not_called()
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_save_themes_does_not_overwrite_valid_values_with_missing_data(
        self, scraper
    ):
        """不完整快照不得把数据库中的有效行情和股票数覆盖为空或零。"""
        existing_theme = MagicMock()
        existing_theme.code = "BK0XXX"
        existing_theme.heat_index = Decimal("88.5")
        existing_theme.rise_fall_pct = Decimal("2.3")
        existing_theme.stock_count = 42

        result = MagicMock()
        result.scalars.return_value.all.return_value = [existing_theme]
        session = AsyncMock()
        session.execute.return_value = result
        session.add = MagicMock()

        with patch("app.scrapers.eastmoney.AsyncSessionLocal") as session_factory:
            session_factory.return_value.__aenter__.return_value = session
            await scraper._save_themes(
                [
                    {
                        "name": "测试题材",
                        "code": "BK0XXX",
                        "heat_index": None,
                        "rise_fall_pct": None,
                        "stock_count": None,
                        "category": "其他",
                        "source": "eastmoney",
                    }
                ]
            )

        assert existing_theme.heat_index == Decimal("88.5")
        assert existing_theme.rise_fall_pct == Decimal("2.3")
        assert existing_theme.stock_count == 42

    @pytest.mark.asyncio
    async def test_fetch_all_pages_uses_total_and_merges_results(
        self, scraper, mock_middleware
    ):
        """API 有多页数据时应抓取全部页面"""
        scraper.middleware = mock_middleware

        responses = []
        for page, item_count in ((1, 5), (2, 5), (3, 2)):
            response = MagicMock()
            response.raise_for_status.return_value = None
            response.json.return_value = {
                "data": {
                    "total": 12,
                    "diff": [
                        {
                            "f3": index,
                            "f8": index,
                            "f12": f"BK{page}{index}",
                            "f14": f"题材{page}-{index}",
                            "f104": index,
                        }
                        for index in range(item_count)
                    ],
                }
            }
            responses.append(response)

        mock_middleware.get.side_effect = responses

        result = await scraper.fetch_all_pages(
            EASTMONEY_API_BASE,
            {**DEFAULT_PARAMS, "pz": "5", "fs": "m:90+t:3+f:!50"},
        )

        assert result["data"]["total"] == 12
        assert len(result["data"]["diff"]) == 12
        assert [
            call.kwargs["params"]["pn"] for call in mock_middleware.get.await_args_list
        ] == ["1", "2", "3"]

    @pytest.mark.asyncio
    async def test_fetch_all_pages_deduplicates_items_by_code(
        self, scraper, mock_middleware
    ):
        """实时数据跨页重复时应按证券代码去重"""
        scraper.middleware = mock_middleware
        responses = []
        for codes in (["BK0001", "BK0002"], ["BK0002", "BK0003"], []):
            response = MagicMock()
            response.raise_for_status.return_value = None
            response.json.return_value = {
                "data": {
                    "total": 4,
                    "diff": [{"f12": code} for code in codes],
                }
            }
            responses.append(response)
        mock_middleware.get.side_effect = responses

        result = await scraper.fetch_all_pages(
            EASTMONEY_API_BASE,
            {**DEFAULT_PARAMS, "pz": "2"},
        )

        assert [item["f12"] for item in result["data"]["diff"]] == [
            "BK0001",
            "BK0002",
            "BK0003",
        ]

    @pytest.mark.asyncio
    async def test_fetch_all_pages_falls_back_when_primary_api_disconnects(
        self, scraper, mock_middleware
    ):
        """主域名断开连接时，应切换到延迟行情域名继续采集。"""
        scraper.middleware = mock_middleware
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "data": {
                "total": 1,
                "diff": [{"f12": "BK0001", "f14": "测试题材"}],
            }
        }
        mock_middleware.get.side_effect = [
            httpx.RemoteProtocolError("Server disconnected"),
            response,
        ]

        result = await scraper.fetch_all_pages(
            EASTMONEY_API_BASE,
            {**DEFAULT_PARAMS, "pz": "5"},
        )

        assert result["data"]["diff"][0]["f12"] == "BK0001"
        assert mock_middleware.get.await_args_list[0].args[0] == EASTMONEY_API_BASE
        assert (
            mock_middleware.get.await_args_list[1].args[0]
            == EASTMONEY_API_FALLBACK_BASE
        )

    @pytest.mark.asyncio
    async def test_run_success(
        self,
        scraper,
        mock_middleware,
        sample_theme_list_response,
        sample_theme_stocks_response,
    ):
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
