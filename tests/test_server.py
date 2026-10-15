"""
MiniQMT Share (miniqmt-share) Server Tests
"""

import pytest
from unittest.mock import Mock, patch
import time

# Import the server module
import sys
sys.path.insert(0, '.')


# Initialize logging before importing server
from miniqmt_share.server import _init_logging
_init_logging("WARNING")  # Quiet logs for tests

from miniqmt_share.server import (
    XtQuantService,
    AuthError,
    LoggingProxy,
    _summarize_result,
    create_ssl_context,
)
from miniqmt_share.auth import PermissionChecker


class TestSummarizeResult:
    """测试返回值摘要函数"""
    
    def test_none(self):
        assert _summarize_result(None) == "None"
    
    def test_int(self):
        assert _summarize_result(42) == "42"
    
    def test_float(self):
        assert _summarize_result(3.14) == "3.14"
    
    def test_bool(self):
        assert _summarize_result(True) == "True"
    
    def test_string_short(self):
        assert _summarize_result("hello") == "hello"
    
    def test_string_long(self):
        long_str = "x" * 300
        result = _summarize_result(long_str)
        assert len(result) <= 203  # max_len + "..."
    
    def test_list(self):
        assert _summarize_result([1, 2, 3]) == "list[len=3]"
    
    def test_dict(self):
        result = _summarize_result({"a": 1, "b": 2})
        assert "dict" in result
        assert "a" in result or "b" in result


class TestXtQuantService:
    """测试服务类"""

    def test_on_connect(self):
        service = XtQuantService()
        mock_conn = Mock()
        mock_conn.peer = "192.168.1.100:12345"
        
        service.on_connect(mock_conn)
        
        assert service._authenticated is False
        assert service._client_id is None
        assert service._account_level.value == "free"
    
    def test_on_disconnect(self):
        service = XtQuantService()
        service._conn = Mock()
        service._conn.peer = "192.168.1.100:12345"
        service._client_info = "test_client@192.168.1.100:12345"

        service.on_disconnect(service._conn)

    def test_require_auth_rejects_unauthenticated_access(self):
        service = XtQuantService()
        service._conn = Mock()
        service._client_info = "192.168.1.100:12345"
        service._authenticated = False

        with patch.object(service, "_delayed_disconnect") as mock_disconnect:
            with pytest.raises(AuthError):
                service.exposed_get_service_status()

        mock_disconnect.assert_called_once()


class TestSSLContext:
    """测试 SSL 上下文创建"""
    
    def test_create_ssl_context_no_files(self):
        ctx = create_ssl_context(None, None)
        assert ctx is None
    
    @patch('miniqmt_share.server.ssl.SSLContext')
    def test_create_ssl_context_with_files(self, mock_ssl_context):
        mock_ctx = Mock()
        mock_ssl_context.return_value = mock_ctx

        ctx = create_ssl_context("cert.pem", "key.pem")

        assert ctx is mock_ctx
        mock_ctx.load_cert_chain.assert_called_once_with("cert.pem", "key.pem")


class TestAuthService:
    """测试认证服务"""

    def _write_config(self, tmp_path):
        config = tmp_path / "clients.yaml"
        config.write_text(
            """
clients:
  test_client:
    secret: "test-secret"
    level: standard
  app1:
    secret: "secret-app1"
    level: plus
  app2:
    secret: "secret-app2"
    level: premium
""",
            encoding="utf-8",
        )
        return config

    def _create_service(self, tmp_path):
        XtQuantService._permission_checker = PermissionChecker(str(self._write_config(tmp_path)))
        service = XtQuantService()
        service._conn = Mock()
        service._conn.peer = "192.168.1.100:12345"
        service.on_connect(service._conn)
        return service
    
    def test_authenticate_success(self, tmp_path):
        service = self._create_service(tmp_path)
        
        result = service.exposed_authenticate("test_client", "test-secret")
        
        assert result == {"success": True, "level": "standard"}
        assert service._authenticated is True
    
    def test_authenticate_failure(self, tmp_path):
        service = self._create_service(tmp_path)
        
        with pytest.raises(AuthError):
            service.exposed_authenticate("test_client", "wrong-secret")
    
    def test_multi_client_auth(self, tmp_path):
        service = self._create_service(tmp_path)
        
        # App1 with correct secret
        result1 = service.exposed_authenticate("app1", "secret-app1")
        assert result1["level"] == "plus"
        
        # App2 with correct secret
        result2 = service.exposed_authenticate("app2", "secret-app2")
        assert result2["level"] == "premium"
        
        # App1 with wrong secret
        with pytest.raises(AuthError):
            service.exposed_authenticate("app1", "secret-app2")


class TestAuthenticatedServiceMethods:
    """测试认证后的服务端接口"""

    def _write_config(self, tmp_path):
        config = tmp_path / "clients.yaml"
        config.write_text(
            """
clients:
  standard-user:
    secret: "standard-secret"
    level: standard
""",
            encoding="utf-8",
        )
        return config

    def _create_authenticated_service(self, tmp_path):
        XtQuantService._permission_checker = PermissionChecker(str(self._write_config(tmp_path)))
        service = XtQuantService()
        service._conn = Mock()
        service._conn.peer = "192.168.1.100:12345"
        service.on_connect(service._conn)
        service.exposed_authenticate("standard-user", "standard-secret")
        return service

    def test_get_service_status(self, tmp_path):
        service = self._create_authenticated_service(tmp_path)
        service._start_time = time.time() - 5

        status = service.exposed_get_service_status()

        assert status["uptime"] >= 0
        assert status["client_id"] == "standard-user"

    def test_ping_does_not_require_auth(self):
        service = XtQuantService()

        assert service.exposed_ping() == "pong"

    def test_get_xtdata_returns_logging_proxy(self, tmp_path):
        service = self._create_authenticated_service(tmp_path)

        proxy = service.exposed_get_xtdata()

        assert isinstance(proxy, LoggingProxy)

    def test_get_all_stocks_delegates_to_xtdata(self, tmp_path):
        service = self._create_authenticated_service(tmp_path)
        service._xtdata = Mock()
        service._xtdata.get_stock_list_in_sector.return_value = ["000001.SZ"]

        result = service.exposed_get_all_stocks()

        assert result == ["000001.SZ"]
        service._xtdata.get_stock_list_in_sector.assert_called_once_with("沪深A股")

    def test_get_xtview_unavailable(self, tmp_path):
        service = self._create_authenticated_service(tmp_path)
        service._xtview = None

        with pytest.raises(RuntimeError, match="xtview"):
            service.exposed_get_xtview()

    def test_async_callback_invokes_callback(self, tmp_path):
        service = self._create_authenticated_service(tmp_path)
        callback = Mock(return_value="ok")

        result = service.exposed_test_async_callback(callback, delay=0.01, count=2)

        assert "已启动异步回调" in result
        deadline = time.time() + 1
        while callback.call_count < 2 and time.time() < deadline:
            time.sleep(0.01)
        assert callback.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
