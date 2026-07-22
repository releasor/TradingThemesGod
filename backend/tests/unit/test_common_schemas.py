"""通用 schemas 工具函数单元测试"""

import pytest
from app.schemas.common import calculate_total_pages


class TestCalculateTotalPages:
    """calculate_total_pages 测试"""

    def test_normal_case(self):
        """正常分页计算"""
        assert calculate_total_pages(100, 20) == 5

    def test_exact_division(self):
        """整除情况"""
        assert calculate_total_pages(100, 10) == 10

    def test_remainder_rounds_up(self):
        """有余数时向上取整"""
        assert calculate_total_pages(101, 20) == 6
        assert calculate_total_pages(21, 20) == 2

    def test_zero_total(self):
        """总数为 0 返回 0"""
        assert calculate_total_pages(0, 20) == 0

    def test_single_item(self):
        """单条记录"""
        assert calculate_total_pages(1, 20) == 1

    def test_total_less_than_page_size(self):
        """总数小于每页数量"""
        assert calculate_total_pages(5, 20) == 1

    def test_page_size_one(self):
        """每页 1 条"""
        assert calculate_total_pages(10, 1) == 10

    def test_large_numbers(self):
        """大数计算"""
        assert calculate_total_pages(1000000, 50) == 20000
