"""复盘日报可选盘后调度（默认关闭，未接入 main lifespan）。

启用条件：Settings.REVIEW_REPORT_SCHEDULER_ENABLED=True。
首期以前端 ensure 为主；本模块仅占位，避免误启后台批写。
"""

from __future__ import annotations

from app.core.logging import get_logger

logger = get_logger(__name__)


class ReviewReportScheduler:
    """交易日 16:00 后对「昨日」写全局规则摘要的占位调度器。"""

    def __init__(self) -> None:
        self._started = False

    def start(self) -> None:
        """未实现：仅记录日志，不启动循环。"""
        if self._started:
            return
        self._started = True
        logger.info(
            "review_report_scheduler_stub",
            message=(
                "REVIEW_REPORT_SCHEDULER_ENABLED 为 True 时仍不自动跑批；"
                "请后续实现盘后 ensure"
            ),
        )

    async def stop(self) -> None:
        self._started = False


review_report_scheduler = ReviewReportScheduler()
