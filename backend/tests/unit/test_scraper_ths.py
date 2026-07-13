"""同花顺产业链爬虫单元测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.scrapers.ths import TongHuaShunScraper


@pytest.fixture
def scraper():
    """创建爬虫实例"""
    return TongHuaShunScraper()


@pytest.fixture
def sample_html():
    """示例 HTML 内容"""
    return """
    <html>
    <body>
        <div class="chain-block">
            <h3>上游</h3>
            <a href="#">原材料供应商</a>
            <p>提供基础原材料</p>
            <a href="#">公司A</a>
            <a href="#">公司B</a>
        </div>
        <div class="chain-block">
            <h3>中游</h3>
            <a href="#">制造商</a>
            <p>负责产品生产</p>
            <a href="#">公司C</a>
        </div>
        <div class="chain-block">
            <h3>下游</h3>
            <a href="#">销售渠道</a>
            <p>产品分销和零售</p>
            <a href="#">公司D</a>
        </div>
    </body>
    </html>
    """


def test_parse_returns_list(scraper, sample_html):
    """测试 parse 方法返回列表"""
    result = scraper.parse(sample_html)
    assert isinstance(result, list)


def test_parse_extracts_chains(scraper, sample_html):
    """测试 parse 方法提取产业链数据"""
    result = scraper.parse(sample_html)
    # 应该提取到产业链环节
    assert len(result) > 0


def test_parse_handles_empty_html(scraper):
    """测试 parse 方法处理空 HTML"""
    result = scraper.parse("")
    assert result == []


def test_parse_handles_none_html(scraper):
    """测试 parse 方法处理 None"""
    result = scraper.parse(None)
    assert result == []


def test_chain_level_mapping(scraper):
    """测试产业链层级映射"""
    from app.scrapers.ths import CHAIN_LEVEL_MAP

    assert CHAIN_LEVEL_MAP["上游"] == "upstream"
    assert CHAIN_LEVEL_MAP["中游"] == "midstream"
    assert CHAIN_LEVEL_MAP["下游"] == "downstream"


def test_extract_chain_blocks(scraper, sample_html):
    """测试提取产业链区块"""
    blocks = scraper._extract_chain_blocks(sample_html)
    assert isinstance(blocks, list)


def test_source_name(scraper):
    """测试数据源名称"""
    assert scraper.source_name == "ths"


@pytest.mark.asyncio
async def test_save_with_valid_data(scraper):
    """测试保存有效数据"""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

    with patch("app.scrapers.ths.AsyncSessionLocal") as mock_local:
        mock_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_local.return_value.__aexit__ = AsyncMock(return_value=None)

        data = [
            {
                "theme_id": 1,
                "level": "upstream",
                "name": "原材料",
                "description": "提供基础材料",
                "representative_companies": ["公司A"],
            }
        ]

        result = await scraper.save(data)
        assert result == 1


@pytest.mark.asyncio
async def test_save_with_empty_data(scraper):
    """测试保存空数据"""
    mock_session = AsyncMock()

    with patch("app.scrapers.ths.AsyncSessionLocal") as mock_local:
        mock_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_local.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await scraper.save([])
        assert result == 0
