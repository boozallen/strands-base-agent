# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for TLS posture configuration and validation."""

import pytest

from strands_base_agent.application.tls_config import (
    TlsConfig,
    TlsMode,
    load_tls_config,
    validate_tls_config,
)


class TestLoadTlsConfig:
    def test_loads_platform_mode_from_env(self, monkeypatch):
        monkeypatch.setenv("STRANDS_TLS_MODE", "platform")
        config = load_tls_config()
        assert config.tls_mode == TlsMode.PLATFORM

    def test_loads_native_mode_from_env(self, monkeypatch):
        monkeypatch.setenv("STRANDS_TLS_MODE", "native")
        monkeypatch.setenv("STRANDS_TLS_KEYFILE", "/tmp/key.pem")
        monkeypatch.setenv("STRANDS_TLS_CERTFILE", "/tmp/cert.pem")
        config = load_tls_config()
        assert config.tls_mode == TlsMode.NATIVE
        assert config.tls_keyfile == "/tmp/key.pem"
        assert config.tls_certfile == "/tmp/cert.pem"

    def test_returns_none_mode_when_unset(self, monkeypatch):
        monkeypatch.delenv("STRANDS_TLS_MODE", raising=False)
        config = load_tls_config()
        assert config.tls_mode is None

    def test_exits_on_invalid_mode(self, monkeypatch):
        monkeypatch.setenv("STRANDS_TLS_MODE", "invalid")
        with pytest.raises(SystemExit) as exc_info:
            load_tls_config()
        assert exc_info.value.code == 1

    def test_env_var_overrides_yaml_value(self, monkeypatch):
        monkeypatch.setenv("STRANDS_TLS_MODE", "native")
        config = load_tls_config()
        assert config.tls_mode == TlsMode.NATIVE


class TestValidateTlsConfig:
    def test_fails_when_tls_mode_unset(self):
        config = TlsConfig(tls_mode=None)
        with pytest.raises(SystemExit) as exc_info:
            validate_tls_config(config)
        assert exc_info.value.code == 1

    def test_succeeds_with_platform_mode(self):
        config = TlsConfig(tls_mode=TlsMode.PLATFORM)
        validate_tls_config(config)

    def test_fails_native_mode_missing_keyfile(self):
        config = TlsConfig(
            tls_mode=TlsMode.NATIVE,
            tls_keyfile=None,
            tls_certfile="/tmp/cert.pem",
        )
        with pytest.raises(SystemExit) as exc_info:
            validate_tls_config(config)
        assert exc_info.value.code == 1

    def test_fails_native_mode_missing_certfile(self):
        config = TlsConfig(
            tls_mode=TlsMode.NATIVE,
            tls_keyfile="/tmp/key.pem",
            tls_certfile=None,
        )
        with pytest.raises(SystemExit) as exc_info:
            validate_tls_config(config)
        assert exc_info.value.code == 1

    def test_fails_native_mode_keyfile_not_found(self, tmp_path):
        certfile = tmp_path / "cert.pem"
        certfile.write_text("cert")
        config = TlsConfig(
            tls_mode=TlsMode.NATIVE,
            tls_keyfile="/nonexistent/key.pem",
            tls_certfile=str(certfile),
        )
        with pytest.raises(SystemExit) as exc_info:
            validate_tls_config(config)
        assert exc_info.value.code == 1

    def test_fails_native_mode_certfile_not_found(self, tmp_path):
        keyfile = tmp_path / "key.pem"
        keyfile.write_text("key")
        config = TlsConfig(
            tls_mode=TlsMode.NATIVE,
            tls_keyfile=str(keyfile),
            tls_certfile="/nonexistent/cert.pem",
        )
        with pytest.raises(SystemExit) as exc_info:
            validate_tls_config(config)
        assert exc_info.value.code == 1

    def test_succeeds_native_mode_valid_files(self, tmp_path):
        keyfile = tmp_path / "key.pem"
        certfile = tmp_path / "cert.pem"
        keyfile.write_text("key-content")
        certfile.write_text("cert-content")
        config = TlsConfig(
            tls_mode=TlsMode.NATIVE,
            tls_keyfile=str(keyfile),
            tls_certfile=str(certfile),
        )
        validate_tls_config(config)
