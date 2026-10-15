"""
MiniQMT Share (miniqmt-share) Client Tests
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

# Import the client module
import sys
sys.path.insert(0, '.')
from miniqmt_share.client import (
    XtQuantRemote,
    ReconnectPolicy,
    RemoteModule,
    ConnectionError as XQShareConnectionError,
)


class TestReconnectPolicy:
    """测试重连策略"""
    
    def test_base_delay(self):
        policy = ReconnectPolicy(max_retries=5, base_delay=1, backoff_factor=2)
        assert policy.get_delay(0) == 1
    
    def test_exponential_backoff(self):
        policy = ReconnectPolicy(max_retries=5, base_delay=1, backoff_factor=2)
        assert policy.get_delay(0) == 1
        assert policy.get_delay(1) == 2
        assert policy.get_delay(2) == 4
        assert policy.get_delay(3) == 8
    
    def test_max_delay(self):
        policy = ReconnectPolicy(max_retries=5, base_delay=1, max_delay=10, backoff_factor=2)
        assert policy.get_delay(10) == 10  # cap at max_delay


class TestRemoteModule:
    """测试远程模块代理"""
    
    def test_attribute_access(self):
        mock_client = Mock()
        mock_client._ensure_connected = Mock()
        mock_client._should_reconnect = Mock(return_value=False)
        mock_client._conn = Mock()
        mock_client._token = "test_token"
        
        # Mock the remote module
        mock_module = Mock()
        mock_module.test_func = Mock(return_value="test_result")
        mock_client._conn.root.get_xtdata = Mock(return_value=mock_module)
        
        remote = RemoteModule(mock_client, 'xtdata')
        result = remote.test_func()
        
        assert result == "test_result"
    
    def test_reconnect_on_error(self):
        mock_client = Mock()
        mock_client._ensure_connected = Mock()
        mock_client._should_reconnect = Mock(return_value=True)
        mock_client._conn = Mock()
        mock_client._token = "test_token"
        
        # First call fails, second succeeds
        mock_module = Mock()
        call_count = [0]
        
        def test_func():
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Connection reset")
            return "success"
        
        mock_module.test_func = test_func
        mock_client._conn.root.get_xtdata = Mock(return_value=mock_module)
        
        remote = RemoteModule(mock_client, 'xtdata')
        
        # Should trigger reconnect on first failure
        with pytest.raises(Exception):
            remote.test_func()

    def test_deserializes_wrapped_result(self):
        mock_client = Mock()
        mock_client._ensure_connected = Mock()
        mock_client._should_reconnect = Mock(return_value=False)
        mock_client._conn = Mock()

        mock_module = Mock()
        mock_module.test_func = Mock(return_value={
            "__xqshare_serialized__": "json",
            "data": '{"ok": true}',
        })
        mock_client._conn.root.get_xtdata = Mock(return_value=mock_module)

        remote = RemoteModule(mock_client, 'xtdata')
        result = remote.test_func()

        assert result == {"ok": True}


class TestXtQuantRemote:
    """测试主客户端类"""
    
    @patch('miniqmt_share.client.rpyc.connect')
    def test_connect_without_auth(self, mock_connect):
        mock_conn = Mock()
        mock_conn.root.ping = Mock(return_value="pong")
        mock_connect.return_value = mock_conn
        
        client = XtQuantRemote(host="localhost", port=18812, client_secret="", auto_reconnect=False)
        
        mock_connect.assert_called_once()
        assert client._connected is True

    @patch('miniqmt_share.client.rpyc.connect')
    def test_sync_request_timeout_is_forwarded_to_rpyc(self, mock_connect):
        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        XtQuantRemote(
            host="localhost", client_secret="", auto_reconnect=False,
            sync_request_timeout=5,
        )

        assert mock_connect.call_args.kwargs["config"]["sync_request_timeout"] == 5

    @patch('miniqmt_share.client.rpyc.connect')
    def test_connect_auth_failure_closes_connection(self, mock_connect):
        """认证失败时必须关闭已建立的连接，否则泄漏到进程退出。"""
        mock_conn = Mock()
        mock_conn.root.authenticate = Mock(side_effect=Exception("auth timeout"))
        mock_connect.return_value = mock_conn

        with pytest.raises(XQShareConnectionError):
            XtQuantRemote(host="localhost", client_secret="secret", auto_reconnect=False)

        mock_conn.close.assert_called_once()

    @patch('miniqmt_share.client.rpyc.connect')
    def test_reconnect_does_not_depend_on_removed_subscription_cache(self, mock_connect):
        first, second = Mock(), Mock()
        mock_connect.side_effect = (first, second)
        client = XtQuantRemote(host="localhost", client_secret="", auto_reconnect=True)

        client._connected = False
        client._conn = first
        client._reconnect()

        assert mock_connect.call_count == 2
        assert client._connected is True
    
    @patch('miniqmt_share.client.rpyc.connect')
    def test_connect_with_auth(self, mock_connect):
        mock_conn = Mock()
        mock_conn.root.ping = Mock(return_value="pong")
        mock_conn.root.authenticate = Mock(return_value={"success": True, "level": "standard"})
        mock_connect.return_value = mock_conn
        
        client = XtQuantRemote(
            host="localhost", 
            port=18812, 
            client_secret="my-secret",
            auto_reconnect=False
        )
        
        mock_conn.root.authenticate.assert_called_once()
        assert client._account_level == "standard"
    
    @patch('miniqmt_share.client.rpyc.connect')
    def test_context_manager(self, mock_connect):
        mock_conn = Mock()
        mock_conn.root.ping = Mock(return_value="pong")
        mock_connect.return_value = mock_conn
        
        with XtQuantRemote(host="localhost", auto_reconnect=False) as client:
            assert client._connected is True
        
        assert client._connected is False
    
    @patch('miniqmt_share.client.rpyc.connect')
    def test_should_reconnect(self, mock_connect):
        mock_conn = Mock()
        mock_conn.root.ping = Mock(return_value="pong")
        mock_connect.return_value = mock_conn
        
        client = XtQuantRemote(host="localhost", auto_reconnect=True)
        
        # Connection errors should trigger reconnect
        assert client._should_reconnect(Exception("Connection reset")) is True
        assert client._should_reconnect(Exception("Socket closed")) is True
        assert client._should_reconnect(Exception("Timeout")) is True
        
        # Other errors should not
        assert client._should_reconnect(Exception("ValueError")) is False
        
        client.close()
    
    @patch('miniqmt_share.client.rpyc.connect')
    def test_is_connected(self, mock_connect):
        mock_conn = Mock()
        mock_conn.root.ping = Mock(return_value="pong")
        mock_connect.return_value = mock_conn
        
        client = XtQuantRemote(host="localhost", auto_reconnect=False)
        assert client.is_connected() is True
        
        client.close()
        assert client.is_connected() is False


class TestGlobalFunctions:
    """测试全局便捷函数"""
    
    @patch('miniqmt_share.client.rpyc.connect')
    def test_connect_disconnect(self, mock_connect):
        mock_conn = Mock()
        mock_conn.root.ping = Mock(return_value="pong")
        mock_connect.return_value = mock_conn
        
        from miniqmt_share.client import connect, disconnect, get_client
        
        client = connect(host="localhost", auto_reconnect=False)
        assert client is not None
        
        retrieved = get_client()
        assert retrieved is client
        
        disconnect()
        assert get_client() is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
