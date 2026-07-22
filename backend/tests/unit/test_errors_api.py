"""前端错误上报 API 端点测试

测试 POST /api/v1/errors 端点。
"""

import pytest


class TestReportError:
    """POST /api/v1/errors 测试"""

    @pytest.mark.asyncio
    async def test_report_error_with_full_data(self, client):
        """验证完整错误数据上报成功"""
        error_data = {
            "message": "TypeError: Cannot read property 'x' of undefined",
            "stack": "TypeError: Cannot read property...\n    at Component.render",
            "componentStack": "at App\n    at ErrorBoundary",
            "url": "http://localhost:3000/themes/1",
            "userAgent": "Mozilla/5.0",
            "timestamp": "2026-01-15T10:00:00Z",
        }
        response = await client.post("/api/v1/errors", json=error_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "错误已记录" in data["message"]

    @pytest.mark.asyncio
    async def test_report_error_with_minimal_data(self, client):
        """验证仅必填字段的错误上报"""
        error_data = {
            "message": "Something went wrong",
        }
        response = await client.post("/api/v1/errors", json=error_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_report_error_rejects_empty_message(self, client):
        """验证缺少必填字段返回 422"""
        error_data = {}
        response = await client.post("/api/v1/errors", json=error_data)

        assert response.status_code == 422
