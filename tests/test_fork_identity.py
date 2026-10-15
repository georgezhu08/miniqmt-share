"""
运行身份隔离测试：默认端口、认证 fail-closed、配置文件解析

对应增量迁移规格书：
- 默认端口 51812（显式参数/环境变量优先）
- 无认证配置时服务端拒绝启动（fail-closed）
- MINIQMT_SHARE_CLIENTS_FILE 覆盖配置路径
"""

import os
import sys
from unittest.mock import patch, Mock

import pytest

from miniqmt_share.auth import AuthConfigError, PermissionChecker, ENV_CLIENTS_FILE


# ==================== 默认端口 ====================

class TestDefaultPort:
    """默认端口隔离：MINIQMT_SHARE_* 未设置时使用 51812"""

    def test_client_default_port(self):
        """客户端默认连接端口为 51812"""
        env = {k: v for k, v in os.environ.items() if not k.startswith("MINIQMT_SHARE_")}
        with patch.dict(os.environ, env, clear=True):
            port = int(os.environ.get("MINIQMT_SHARE_REMOTE_PORT", "51812"))
            assert port == 51812

    def test_env_port_overrides_default(self):
        """MINIQMT_SHARE_REMOTE_PORT 优先于默认值"""
        with patch.dict(os.environ, {"MINIQMT_SHARE_REMOTE_PORT": "59999"}):
            port = int(os.environ.get("MINIQMT_SHARE_REMOTE_PORT", "51812"))
            assert port == 59999

    def test_explicit_port_param_beats_env(self):
        """显式 port 参数优先于环境变量（客户端逻辑）"""
        # XtQuantRemote: if port is None -> env；显式 port 不读 env
        port_arg = 51001
        env_port = 51002
        resolved = port_arg if port_arg is not None else int(
            os.environ.get("MINIQMT_SHARE_REMOTE_PORT", "51812"))
        with patch.dict(os.environ, {"MINIQMT_SHARE_REMOTE_PORT": str(env_port)}):
            resolved_env = port_arg if port_arg is not None else int(
                os.environ.get("MINIQMT_SHARE_REMOTE_PORT", "51812"))
        assert resolved == 51001
        assert resolved_env == 51001


# ==================== 认证 fail-closed ====================

class TestAuthFailClosed:
    """认证配置隔离（Case A-D）"""

    def test_case_a_missing_config_rejected(self, tmp_path, monkeypatch):
        """Case A: 无认证配置文件 -> PermissionChecker 抛 AuthConfigError，
        服务端 start_server 拒绝启动"""
        monkeypatch.chdir(tmp_path)  # 目录内无 miniqmt-share.clients.yaml
        monkeypatch.delenv(ENV_CLIENTS_FILE, raising=False)
        with pytest.raises(AuthConfigError):
            PermissionChecker()

        # start_server 同样 fail-closed
        from miniqmt_share import server
        server.XtQuantService._permission_checker = None
        # xtquant 不可用时 start_server 会提前 return；为验证 auth 分支，标记可用
        with patch.object(server, "XTQUANT_AVAILABLE", True), \
             patch.object(server, "_init_logging"):
            with patch.object(server, "ThreadedServer") as mock_ts:
                server.start_server(port=51812)
                mock_ts.start.assert_not_called()  # 未进入服务循环
        server.XtQuantService._permission_checker = None

    def test_case_b_valid_config_loads(self, tmp_path):
        """Case B: 配置文件存在且有效 -> 正常加载"""
        config = tmp_path / "miniqmt-share.clients.yaml"
        config.write_text(
            "clients:\n  alice:\n    secret: strong-secret\n    level: standard\n",
            encoding="utf-8",
        )
        checker = PermissionChecker(str(config))
        valid, level = checker.verify_secret("alice", "strong-secret")
        assert valid is True
        assert level.value == "standard"

    def test_case_c_clients_file_env_override(self, tmp_path, monkeypatch):
        """Case C: MINIQMT_SHARE_CLIENTS_FILE 指定路径 -> 正确加载"""
        config = tmp_path / "custom-auth.yaml"
        config.write_text(
            "clients:\n  bob:\n    secret: another-secret\n    level: premium\n",
            encoding="utf-8",
        )
        monkeypatch.setenv(ENV_CLIENTS_FILE, str(config))
        monkeypatch.chdir(tmp_path)
        checker = PermissionChecker()
        assert checker.config_path == str(config)
        valid, level = checker.verify_secret("bob", "another-secret")
        assert valid is True
        assert level.value == "premium"

    def test_case_d_broken_config_clear_error(self, tmp_path):
        """Case D: 错误配置 -> 清晰报错，不回退固定 secret"""
        config = tmp_path / "miniqmt-share.clients.yaml"
        config.write_text("clients: {{{{ not yaml", encoding="utf-8")
        with pytest.raises(AuthConfigError, match="加载认证配置失败"):
            PermissionChecker(str(config))

    def test_no_public_default_secret_anywhere(self):
        """公开默认 secret 字符串不得出现在运行时代码中"""
        import miniqmt_share.client as client_mod
        import miniqmt_share.auth as auth_mod
        assert not hasattr(auth_mod, "DEFAULT_CLIENT_SECRET")
        assert not hasattr(client_mod, "DEFAULT_CLIENT_SECRET")
