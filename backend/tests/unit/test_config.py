"""配置模块测试

测试 Settings 类的默认值、属性方法和环境变量覆盖。
"""

from app.core.config import Settings, get_settings


class TestSettings:
    """Settings 类测试"""

    def test_default_values(self):
        """测试默认配置值"""
        settings = Settings(
            _env_file=None,  # 不加载 .env 文件
        )
        assert settings.APP_HOST == "0.0.0.0"
        assert settings.APP_PORT == 8000
        assert settings.APP_ENV == "development"
        assert settings.APP_DEBUG is False

    def test_database_defaults(self):
        """测试数据库默认配置"""
        settings = Settings(_env_file=None)
        assert settings.DB_HOST == "localhost"
        assert settings.DB_PORT == 3306
        assert settings.DB_NAME == "trading_themes"
        assert settings.DB_USER == "root"
        assert settings.DB_PASSWORD == ""

    def test_cors_defaults(self):
        """测试 CORS 默认配置"""
        settings = Settings(_env_file=None)
        assert "http://localhost:5173" in settings.CORS_ORIGINS
        assert "http://localhost:3000" in settings.CORS_ORIGINS

    def test_proxy_defaults(self):
        """测试代理默认配置"""
        settings = Settings(_env_file=None)
        assert settings.PROXY_ENABLED is False
        assert settings.PROXY_URL == ""

    def test_database_url_property(self):
        """测试 database_url 属性构建"""
        settings = Settings(
            DB_USER="testuser",
            DB_PASSWORD="testpass",
            DB_HOST="dbhost",
            DB_PORT=3307,
            DB_NAME="testdb",
            _env_file=None,
        )
        url = settings.database_url
        assert url == (
            "mysql+asyncmy://testuser:testpass@dbhost:3307/testdb?charset=utf8mb4"
        )

    def test_database_url_with_special_chars_in_password(self):
        """测试密码包含特殊字符时的 URL 构建"""
        settings = Settings(
            DB_USER="user",
            DB_PASSWORD="p@ss:wrd!",
            DB_HOST="localhost",
            DB_PORT=3306,
            DB_NAME="db",
            _env_file=None,
        )
        url = settings.database_url
        assert "p%40ss%3Awrd%21" in url
        assert "p@ss:wrd!" not in url

    def test_env_override(self, monkeypatch):
        """测试环境变量覆盖"""
        monkeypatch.setenv("APP_PORT", "9000")
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("APP_DEBUG", "true")

        settings = Settings(_env_file=None)
        assert settings.APP_PORT == 9000
        assert settings.APP_ENV == "production"
        assert settings.APP_DEBUG is True

    def test_env_override_database(self, monkeypatch):
        """测试数据库环境变量覆盖"""
        monkeypatch.setenv("DB_HOST", "remotehost")
        monkeypatch.setenv("DB_PORT", "3307")

        settings = Settings(_env_file=None)
        assert settings.DB_HOST == "remotehost"
        assert settings.DB_PORT == 3307

    def test_env_override_proxy(self, monkeypatch):
        """测试代理环境变量覆盖"""
        monkeypatch.setenv("PROXY_ENABLED", "true")
        monkeypatch.setenv("PROXY_URL", "http://proxy:8080")

        settings = Settings(_env_file=None)
        assert settings.PROXY_ENABLED is True
        assert settings.PROXY_URL == "http://proxy:8080"


class TestGetSettings:
    """get_settings 函数测试"""

    def test_returns_settings_instance(self):
        """测试返回 Settings 实例"""
        # 清除缓存以确保干净测试
        get_settings.cache_clear()
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_returns_same_instance(self):
        """测试缓存返回同一实例（单例模式）"""
        get_settings.cache_clear()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_cache_clear(self):
        """测试缓存清除后返回新实例"""
        get_settings.cache_clear()
        s1 = get_settings()
        get_settings.cache_clear()
        s2 = get_settings()
        # 清除缓存后，新实例的值相同但不是同一对象
        assert s1.APP_PORT == s2.APP_PORT
