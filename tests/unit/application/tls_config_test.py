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
    def test_loads_off_mode_from_env(self, monkeypatch):
        monkeypatch.setenv("STRANDS_TLS_MODE", "off")
        config = load_tls_config()
        assert config.tls_mode == TlsMode.OFF

    def test_exits_on_removed_platform_value(self, monkeypatch):
        monkeypatch.setenv("STRANDS_TLS_MODE", "platform")
        with pytest.raises(SystemExit) as exc_info:
            load_tls_config()
        assert exc_info.value.code == 1

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

    def test_loads_ca_certfile_from_env(self, monkeypatch):
        monkeypatch.setenv("STRANDS_TLS_MODE", "native")
        monkeypatch.setenv("STRANDS_TLS_KEYFILE", "/tmp/key.pem")
        monkeypatch.setenv("STRANDS_TLS_CERTFILE", "/tmp/cert.pem")
        monkeypatch.setenv("STRANDS_TLS_CA_CERTFILE", "/tmp/ca.pem")
        config = load_tls_config()
        assert config.tls_ca_certfile == "/tmp/ca.pem"

    def test_ca_certfile_none_when_unset(self, monkeypatch):
        monkeypatch.setenv("STRANDS_TLS_MODE", "native")
        monkeypatch.setenv("STRANDS_TLS_KEYFILE", "/tmp/key.pem")
        monkeypatch.setenv("STRANDS_TLS_CERTFILE", "/tmp/cert.pem")
        monkeypatch.delenv("STRANDS_TLS_CA_CERTFILE", raising=False)
        config = load_tls_config()
        assert config.tls_ca_certfile is None


class TestValidateTlsConfig:
    def test_fails_when_tls_mode_unset(self):
        config = TlsConfig(tls_mode=None)
        with pytest.raises(SystemExit) as exc_info:
            validate_tls_config(config)
        assert exc_info.value.code == 1

    def test_succeeds_with_off_mode(self):
        config = TlsConfig(tls_mode=TlsMode.OFF)
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

    def test_fails_native_mode_ca_certfile_not_found(self, tmp_path):
        keyfile = tmp_path / "key.pem"
        certfile = tmp_path / "cert.pem"
        keyfile.write_text("key-content")
        certfile.write_text("cert-content")
        config = TlsConfig(
            tls_mode=TlsMode.NATIVE,
            tls_keyfile=str(keyfile),
            tls_certfile=str(certfile),
            tls_ca_certfile="/nonexistent/ca.pem",
        )
        with pytest.raises(SystemExit) as exc_info:
            validate_tls_config(config)
        assert exc_info.value.code == 1

    def test_succeeds_native_mode_valid_ca_certfile(self, tmp_path):
        keyfile = tmp_path / "key.pem"
        certfile = tmp_path / "cert.pem"
        ca_certfile = tmp_path / "ca.pem"
        keyfile.write_text("key-content")
        certfile.write_text("cert-content")
        ca_certfile.write_text("ca-content")
        config = TlsConfig(
            tls_mode=TlsMode.NATIVE,
            tls_keyfile=str(keyfile),
            tls_certfile=str(certfile),
            tls_ca_certfile=str(ca_certfile),
        )
        validate_tls_config(config)

    def test_succeeds_native_mode_no_ca_certfile_backward_compat(self, tmp_path):
        keyfile = tmp_path / "key.pem"
        certfile = tmp_path / "cert.pem"
        keyfile.write_text("key-content")
        certfile.write_text("cert-content")
        config = TlsConfig(
            tls_mode=TlsMode.NATIVE,
            tls_keyfile=str(keyfile),
            tls_certfile=str(certfile),
            tls_ca_certfile=None,
        )
        validate_tls_config(config)
