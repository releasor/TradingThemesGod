"""基于真实网页证据和用户模型配置增量刷新题材图谱。"""

from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal
from typing import Any

import httpx
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.concept_node import ConceptNode
from app.models.concept_node_stock import ConceptNodeStock
from app.models.stock import Stock
from app.models.theme import Theme
from app.models.theme_stock import ThemeStock
from app.schemas.concept_refresh import (
    ConceptGraphRefreshResponse,
    ExtractedConceptGraph,
    ExtractedConceptNode,
)
from app.services.model_provider import ModelProviderService
from app.services.web_research import ResearchSource, WebResearchService

MAX_GRAPH_NODES = 24

SYSTEM_PROMPT = f"""你是严谨的中国 A 股产业研究员。只能依据用户提供的网页正文抽取信息，禁止使用未提供的记忆补充事实。
返回一个 JSON 对象且不要输出解释。结构为 {{"nodes": [...]}}。nodes 支持 children 任意递归层级。
每个节点必须包含 name、sources；可包含 node_type、description、chain_level、market_logic、catalysts、risks、confidence、stocks、children。
confidence 和 relevance_score 必须是 0 到 1 的数字，禁止输出 high、medium、low 等文字。
chain_level 只能是 upstream、midstream、downstream 或 null。sources 必须是输入中完整 URL。
stocks 中每项必须包含 code、relation_type、rationale、sources；只能使用输入允许的股票代码。
优先深入拆解技术、材料、设备、零部件、工艺和应用。例如一个部件应继续拆到驱动、传动、传感，再拆到有证据支持的具体技术。
所有层级合计最多输出 {MAX_GRAPH_NODES} 个节点；描述、市场逻辑、催化剂和风险必须简洁，避免重复来源正文。
证据不足就省略节点或股票，不得猜测，不得为了形式平均分配上中下游。"""


MAX_RESEARCH_CHARS = 9_000
MAX_SOURCE_CHARS = 1_500
MIN_GRAPH_TOKENS = 8_192
MIN_GRAPH_TIMEOUT_SECONDS = 120


def model_error_message(exc: Exception) -> str:
    """将模型协议异常转换为用户可执行的中文提示。"""
    if isinstance(exc, httpx.RemoteProtocolError):
        return "模型中转站在返回结果前断开连接，请稍后重试或更换模型"
    if isinstance(exc, httpx.TimeoutException):
        return "模型响应超时，请调高超时时间或更换响应更快的模型"
    if isinstance(exc, httpx.HTTPStatusError):
        return f"模型服务返回 HTTP {exc.response.status_code}"
    message = str(exc).strip()
    return message[:300] if message else type(exc).__name__


def parse_model_json(text: str) -> dict[str, Any]:
    """从纯 JSON 或 Markdown 代码块中提取首个 JSON 对象。"""
    candidates = re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.I | re.S)
    candidates.append(text)
    decoder = json.JSONDecoder()
    for candidate in candidates:
        start = candidate.find("{")
        while start >= 0:
            try:
                value, _ = decoder.raw_decode(candidate[start:])
                if isinstance(value, dict):
                    return value
            except json.JSONDecodeError:
                pass
            start = candidate.find("{", start + 1)
    raise ValueError("模型未返回有效 JSON 对象")


def validate_extracted_graph(
    graph: ExtractedConceptGraph,
    fetched_urls: set[str],
    allowed_stock_codes: set[str],
) -> ExtractedConceptGraph:
    """校验证据 URL，并移除非当前题材成分股关联。"""

    def validate_node(node: ExtractedConceptNode) -> None:
        if not node.sources or any(url not in fetched_urls for url in node.sources):
            raise ValueError(f"节点“{node.name}”引用了未抓取的来源")
        node.stocks = [
            stock
            for stock in node.stocks
            if stock.code in allowed_stock_codes
            and stock.sources
            and all(url in fetched_urls for url in stock.sources)
        ]
        for child in node.children:
            validate_node(child)

    for root in graph.nodes:
        validate_node(root)
    return graph


def _source_payload(
    urls: list[str], source_map: dict[str, ResearchSource]
) -> list[dict]:
    return [
        {
            "title": source_map[url].title,
            "url": url,
            "publisher": source_map[url].publisher,
            "published_at": None,
        }
        for url in urls
    ]


def _path_segment(name: str) -> str:
    normalized = " ".join(name.casefold().split())
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]


class ConceptGraphRefreshService:
    def __init__(
        self,
        session: AsyncSession,
        research: WebResearchService | None = None,
        providers: ModelProviderService | None = None,
    ):
        self.session = session
        self.research = research or WebResearchService()
        if providers is None:
            raise ValueError("ModelProviderService is required")
        self.providers = providers

    async def _theme_context(self, theme_id: int) -> tuple[Theme, dict[str, Stock]]:
        theme = await self.session.get(Theme, theme_id)
        if theme is None or theme.deleted_at is not None:
            raise HTTPException(404, "题材不存在")
        result = await self.session.execute(
            select(Stock)
            .join(ThemeStock, ThemeStock.stock_id == Stock.id)
            .where(ThemeStock.theme_id == theme_id)
        )
        stocks = {stock.code: stock for stock in result.scalars().all()}
        return theme, stocks

    @staticmethod
    def _user_prompt(
        theme: Theme, stocks: dict[str, Stock], sources: list[ResearchSource]
    ) -> str:
        stock_text = "、".join(f"{code} {stock.name}" for code, stock in stocks.items())
        source_parts: list[str] = []
        remaining = MAX_RESEARCH_CHARS
        for index, source in enumerate(sources, 1):
            body = source.text[: min(MAX_SOURCE_CHARS, remaining)]
            remaining -= len(body)
            source_parts.append(
                f"\n[来源 {index}]\n标题：{source.title}\nURL：{source.url}\n正文：\n{body}"
            )
            if remaining <= 0:
                break
        return (
            f"题材：{theme.name}\n描述：{theme.description or '无'}\n"
            f"标签：{json.dumps(theme.tags or [], ensure_ascii=False)}\n"
            f"允许关联的当前题材成分股：{stock_text or '无'}\n"
            "请依据以下来源构建尽可能深入但证据充分的递归细分图谱：\n"
            + "".join(source_parts)
        )

    async def _extract(
        self, theme: Theme, stocks: dict[str, Stock], sources: list[ResearchSource]
    ) -> ExtractedConceptGraph:
        provider = await self.providers.get_default()
        try:
            adapter = self.providers.adapter(provider)
            adapter.max_tokens = max(adapter.max_tokens, MIN_GRAPH_TOKENS)
            adapter.timeout_seconds = max(
                adapter.timeout_seconds, MIN_GRAPH_TIMEOUT_SECONDS
            )
            text = await adapter.complete(
                SYSTEM_PROMPT,
                self._user_prompt(theme, stocks, sources),
                reasoning=False,
            )
            raw = parse_model_json(text)
            graph = ExtractedConceptGraph.model_validate(raw)
        except (
            httpx.HTTPError,
            KeyError,
            TypeError,
            ValidationError,
            ValueError,
        ) as exc:
            raise HTTPException(
                502, f"模型抽取图谱失败：{model_error_message(exc)}"
            ) from exc
        return validate_extracted_graph(
            graph, {source.url for source in sources}, set(stocks)
        )

    async def _merge(
        self,
        theme: Theme,
        stocks: dict[str, Stock],
        sources: list[ResearchSource],
        graph: ExtractedConceptGraph,
    ) -> tuple[int, int, int]:
        existing_result = await self.session.execute(
            select(ConceptNode).where(ConceptNode.theme_id == theme.id)
        )
        existing = list(existing_result.scalars().all())
        by_parent_name = {
            (node.parent_id, node.name.casefold()): node for node in existing
        }
        source_map = {source.url: source for source in sources}
        added = updated = linked = 0

        async def merge_node(
            payload: ExtractedConceptNode,
            parent: ConceptNode | None,
            parent_path: str,
            depth: int,
            order: int,
        ) -> None:
            nonlocal added, updated, linked
            parent_id = parent.id if parent else None
            node = by_parent_name.get((parent_id, payload.name.casefold()))
            if node is None:
                segment = _path_segment(payload.name)
                path = f"{parent_path}/{segment}" if parent_path else segment
                node = ConceptNode(
                    theme_id=theme.id,
                    parent_id=parent_id,
                    name=payload.name,
                    slug=segment,
                    path_key=path,
                )
                self.session.add(node)
                await self.session.flush()
                by_parent_name[(parent_id, payload.name.casefold())] = node
                added += 1
            else:
                updated += 1
            node.node_type = payload.node_type
            node.description = payload.description
            node.chain_level = payload.chain_level
            node.market_logic = payload.market_logic
            node.catalysts = payload.catalysts
            node.risks = payload.risks
            node.sources = _source_payload(payload.sources, source_map)
            node.confidence = Decimal(str(payload.confidence))
            node.depth = depth
            node.sort_order = order
            self.session.add(node)

            for stock_payload in payload.stocks:
                stock = stocks[stock_payload.code]
                link = await self.session.get(ConceptNodeStock, (node.id, stock.id))
                if link is None:
                    link = ConceptNodeStock(node_id=node.id, stock_id=stock.id)
                link.relation_type = stock_payload.relation_type
                link.rationale = stock_payload.rationale
                link.relevance_score = Decimal(str(stock_payload.relevance_score))
                link.is_core = stock_payload.is_core
                link.sources = _source_payload(stock_payload.sources, source_map)
                self.session.add(link)
                linked += 1
            for child_order, child in enumerate(payload.children):
                await merge_node(child, node, node.path_key, depth + 1, child_order)

        for root_order, root in enumerate(graph.nodes):
            await merge_node(root, None, "", 0, root_order)
        await self.session.commit()
        return added, updated, linked

    async def refresh(self, theme_id: int) -> ConceptGraphRefreshResponse:
        theme, stocks = await self._theme_context(theme_id)
        try:
            sources = await self.research.research_theme(theme.name)
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"公开资料抓取失败：{str(exc)[:300]}") from exc
        if not sources:
            raise HTTPException(502, "未抓取到可验证的公开资料，原图谱已保留")
        graph = await self._extract(theme, stocks, sources)
        if not graph.nodes:
            raise HTTPException(502, "模型未提取到有效节点，原图谱已保留")
        try:
            added, updated, linked = await self._merge(theme, stocks, sources, graph)
        except Exception:
            await self.session.rollback()
            raise
        return ConceptGraphRefreshResponse(
            theme_id=theme.id,
            theme_name=theme.name,
            source_count=len(sources),
            added_nodes=added,
            updated_nodes=updated,
            stock_links=linked,
            message="图谱已根据公开资料增量更新",
        )
