"""AI 题材图谱刷新核心校验测试。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException

from app.schemas.concept_refresh import ExtractedConceptGraph
from app.services.concept_graph_refresh import (
    MAX_GRAPH_NODES,
    MAX_RESEARCH_CHARS,
    MAX_SOURCE_CHARS,
    MIN_GRAPH_TIMEOUT_SECONDS,
    MIN_GRAPH_TOKENS,
    SYSTEM_PROMPT,
    ConceptGraphRefreshService,
    model_error_message,
    parse_model_json,
    validate_extracted_graph,
)
from app.services.web_research import ResearchSource


def test_model_error_message_explains_read_timeout():
    error = httpx.ReadTimeout("", request=httpx.Request("POST", "http://model.local"))

    assert (
        model_error_message(error) == "模型响应超时，请调高超时时间或更换响应更快的模型"
    )


def test_model_error_message_explains_remote_disconnect():
    error = httpx.RemoteProtocolError(
        "Server disconnected without sending a response.",
        request=httpx.Request("POST", "https://api.example.com/chat/completions"),
    )

    assert model_error_message(error) == (
        "模型中转站在返回结果前断开连接，请稍后重试或更换模型"
    )


def test_graph_output_budget_leaves_room_for_reasoning_models():
    assert MIN_GRAPH_TOKENS == 8_192


def test_graph_request_timeout_allows_long_reasoning_responses():
    assert MIN_GRAPH_TIMEOUT_SECONDS == 120


def test_graph_prompt_bounds_total_node_count():
    assert str(MAX_GRAPH_NODES) in SYSTEM_PROMPT


def test_user_prompt_limits_each_source_and_total_research_text():
    theme = type("ThemeStub", (), {"name": "机器人", "description": None, "tags": []})()
    sources = [
        ResearchSource(
            title=f"来源 {index}",
            url=f"https://example.com/{index}",
            text=str(index) * (MAX_SOURCE_CHARS + 1_000),
        )
        for index in range(1, 7)
    ]

    prompt = ConceptGraphRefreshService._user_prompt(theme, {}, sources)

    assert all(source.url in prompt for source in sources)
    assert all(
        prompt.count(str(index) * MAX_SOURCE_CHARS) == 1 for index in range(1, 7)
    )
    assert (
        sum(min(len(source.text), MAX_SOURCE_CHARS) for source in sources)
        == MAX_RESEARCH_CHARS
    )


def test_parse_model_json_accepts_fenced_json():
    result = parse_model_json(
        '说明如下：\n```json\n{"nodes":[{"name":"灵巧手","sources":["https://a.example/x"]}]}\n```'
    )

    assert result["nodes"][0]["name"] == "灵巧手"


@pytest.mark.asyncio
async def test_refresh_reports_empty_model_graph_without_validation_details():
    """模型返回空节点时应保留原图谱并返回稳定的中文提示。"""
    source = ResearchSource(
        title="公开资料",
        url="https://example.com/source",
        text="资料正文",
    )
    research = SimpleNamespace(research_theme=AsyncMock(return_value=[source]))
    service = ConceptGraphRefreshService(AsyncMock(), research=research)
    theme = SimpleNamespace(id=1, name="机器人")
    service._theme_context = AsyncMock(return_value=(theme, {}))
    service._extract = AsyncMock(
        return_value=ExtractedConceptGraph.model_validate({"nodes": []})
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.refresh(1)

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "模型未提取到有效节点，原图谱已保留"


def test_extracted_graph_normalizes_model_score_labels_and_ranges():
    graph = ExtractedConceptGraph.model_validate(
        {
            "nodes": [
                {
                    "name": "robotics",
                    "confidence": "high",
                    "sources": ["https://example.com/root"],
                    "stocks": [
                        {
                            "code": "605488",
                            "relation_type": "supplier",
                            "rationale": "evidence",
                            "relevance_score": "85%",
                            "sources": ["https://example.com/stock"],
                        }
                    ],
                    "children": [
                        {
                            "name": "sensor",
                            "confidence": "medium",
                            "sources": ["https://example.com/child"],
                            "children": [
                                {
                                    "name": "skin",
                                    "confidence": "unexpected-label",
                                    "sources": ["https://example.com/leaf"],
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    )

    assert graph.nodes[0].confidence == 0.9
    assert graph.nodes[0].stocks[0].relevance_score == 0.85
    assert graph.nodes[0].children[0].confidence == 0.5
    assert graph.nodes[0].children[0].children[0].confidence == 0.5


def test_extracted_graph_normalizes_text_catalysts_and_risks_to_lists():
    graph = ExtractedConceptGraph.model_validate(
        {
            "nodes": [
                {
                    "name": "储能",
                    "sources": ["https://example.com/root"],
                    "catalysts": "新能源新基建拉动需求。",
                    "risks": "原材料价格波动。",
                    "children": [
                        {
                            "name": "电池材料",
                            "sources": ["https://example.com/child"],
                            "catalysts": "  ",
                            "risks": "供应链扰动。",
                        }
                    ],
                }
            ]
        }
    )

    assert graph.nodes[0].catalysts == ["新能源新基建拉动需求。"]
    assert graph.nodes[0].risks == ["原材料价格波动。"]
    assert graph.nodes[0].children[0].catalysts == []
    assert graph.nodes[0].children[0].risks == ["供应链扰动。"]


def test_validation_rejects_node_without_fetched_source():
    graph = ExtractedConceptGraph.model_validate(
        {"nodes": [{"name": "电子皮肤", "sources": ["https://fake.example/x"]}]}
    )

    with pytest.raises(ValueError, match="来源"):
        validate_extracted_graph(graph, {"https://real.example/x"}, {"605488"})


def test_validation_drops_stock_outside_current_theme():
    graph = ExtractedConceptGraph.model_validate(
        {
            "nodes": [
                {
                    "name": "电子皮肤",
                    "sources": ["https://real.example/x"],
                    "stocks": [
                        {
                            "code": "000001",
                            "relation_type": "供应商",
                            "rationale": "不属于当前题材",
                            "sources": ["https://real.example/x"],
                        }
                    ],
                }
            ]
        }
    )

    validated = validate_extracted_graph(graph, {"https://real.example/x"}, {"605488"})

    assert validated.nodes[0].stocks == []
