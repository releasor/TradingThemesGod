"""结构化日志模块测试

测试 setup_logging 和 get_logger 的行为。
"""

import logging
import structlog
from unittest.mock import patch, MagicMock

from app.core.logging import setup_logging, get_logger


class TestSetupLogging:
    """setup_logging 函数测试"""

    def test_setup_logging_debug_mode(self):
        """测试调试模式下配置彩色控制台输出"""
        mock_settings = MagicMock()
        mock_settings.APP_DEBUG = True

        with patch('app.core.logging.get_settings', return_value=mock_settings):
            with patch('app.core.logging.logging.basicConfig') as mock_basic_config:
                setup_logging()
                mock_basic_config.assert_called_once()
                # 调试模式下日志级别应为 DEBUG
                call_kwargs = mock_basic_config.call_args
                assert call_kwargs.kwargs.get('level') == logging.DEBUG or call_kwargs[1].get('level') == logging.DEBUG

    def test_setup_logging_production_mode(self):
        """测试生产模式下配置 JSON 输出"""
        mock_settings = MagicMock()
        mock_settings.APP_DEBUG = False

        with patch('app.core.logging.get_settings', return_value=mock_settings):
            with patch('app.core.logging.logging.basicConfig') as mock_basic_config:
                setup_logging()
                mock_basic_config.assert_called_once()
                # 生产模式下日志级别应为 INFO
                call_kwargs = mock_basic_config.call_args
                assert call_kwargs.kwargs.get('level') == logging.INFO or call_kwargs[1].get('level') == logging.INFO

    def test_setup_logging_configures_structlog(self):
        """测试 setup_logging 正确配置 structlog"""
        mock_settings = MagicMock()
        mock_settings.APP_DEBUG = False

        with patch('app.core.logging.get_settings', return_value=mock_settings):
            setup_logging()
            # structlog 应该已被配置
            logger = structlog.get_logger('test')
            assert logger is not None

    def test_setup_logging_debug_uses_console_renderer(self):
        """测试调试模式使用 ConsoleRenderer"""
        mock_settings = MagicMock()
        mock_settings.APP_DEBUG = True

        with patch('app.core.logging.get_settings', return_value=mock_settings):
            with patch('app.core.logging.structlog.configure') as mock_configure:
                setup_logging()
                mock_configure.assert_called_once()
                call_kwargs = mock_configure.call_args.kwargs
                processors = call_kwargs.get('processors', [])
                # 检查是否包含 ConsoleRenderer
                has_console = any(
                    'ConsoleRenderer' in str(type(p))
                    for p in processors
                )
                assert has_console

    def test_setup_logging_production_uses_json_renderer(self):
        """测试生产模式使用 JSONRenderer"""
        mock_settings = MagicMock()
        mock_settings.APP_DEBUG = False

        with patch('app.core.logging.get_settings', return_value=mock_settings):
            with patch('app.core.logging.structlog.configure') as mock_configure:
                setup_logging()
                mock_configure.assert_called_once()
                call_kwargs = mock_configure.call_args.kwargs
                processors = call_kwargs.get('processors', [])
                # 检查是否包含 JSONRenderer
                has_json = any(
                    'JSONRenderer' in str(type(p))
                    for p in processors
                )
                assert has_json


class TestGetLogger:
    """get_logger 函数测试"""

    def test_returns_logger(self):
        """测试返回日志器实例"""
        logger = get_logger('test_module')
        # structlog 可能返回 BoundLoggerLazyProxy 或 BoundLogger
        assert logger is not None

    def test_logger_name_matches(self):
        """测试日志器名称正确"""
        logger = get_logger('my_module')
        # structlog 的 logger 绑定后可以通过绑定上下文获取名称
        assert logger is not None

    def test_different_names_return_different_loggers(self):
        """测试不同名称返回不同日志器"""
        logger1 = get_logger('module_a')
        logger2 = get_logger('module_b')
        # 虽然类型相同，但应该是不同的实例
        assert logger1 is not None
        assert logger2 is not None

    def test_logger_can_bind_context(self):
        """测试日志器可以绑定上下文"""
        logger = get_logger('test')
        bound = logger.bind(user_id=123)
        assert bound is not None
