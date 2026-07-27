"""个股 AI 研判报告 API / 抽取契约。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

DISCLAIMER = "本报告由模型根据系统聚合数据生成，仅供参考，不构成投资建议。"

Verdict = Literal["buy", "watch", "avoid"]
HorizonFit = Literal["suitable", "neutral", "unsuitable"]


class HorizonSlot(BaseModel):
    fit: HorizonFit
    note: str = Field(min_length=1)


class StockAiReportHorizon(BaseModel):
    short: HorizonSlot
    swing: HorizonSlot
    medium_long: HorizonSlot


class StockAiReportSections(BaseModel):
    trend: str = ""
    emotion_rotation: str = ""
    themes_catalysts: str = ""
    stock_position: str = ""
    scenarios_actions: str = ""
    risks: str = ""


class ExtractedStockAiReport(BaseModel):
    """模型返回的结构化研判。"""

    verdict: Verdict
    horizon: StockAiReportHorizon
    confidence: int = Field(ge=0, le=100)
    summary: str = Field(min_length=1)
    sections: StockAiReportSections
    full_report: str = Field(min_length=1)

    @field_validator("summary", "full_report")
    @classmethod
    def strip_nonempty(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("不能为空")
        return text


class StockAiReportGenerateRequest(BaseModel):
    force: bool = False


class StockAiReportResponse(BaseModel):
    code: str
    stock_name: str | None = None
    verdict: Verdict
    horizon: StockAiReportHorizon
    confidence: int
    summary: str
    sections: StockAiReportSections
    full_report: str
    model_name: str | None = None
    generated_at: datetime
    elapsed_ms: int = 0
    disclaimer: str = DISCLAIMER
