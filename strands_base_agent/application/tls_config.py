# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""TLS posture configuration for the uvicorn server.

Supports two modes:
- off: TLS terminated externally (ingress/service mesh)
- native: TLS terminated by uvicorn with cert/key files
"""

import logging
import os
import sys
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class TlsMode(StrEnum):
    OFF = "off"
    NATIVE = "native"


class TlsConfig(BaseModel):
    """TLS posture configuration loaded from config.yaml / env vars."""

    model_config = {"frozen": True}

    tls_mode: TlsMode | None = None
    tls_keyfile: str | None = None
    tls_certfile: str | None = None
    tls_ca_certfile: str | None = None


def load_tls_config() -> TlsConfig:
    """Load TLS config from environment."""
    tls_mode_raw = os.environ.get("STRANDS_TLS_MODE")
    tls_keyfile = os.environ.get("STRANDS_TLS_KEYFILE")
    tls_certfile = os.environ.get("STRANDS_TLS_CERTFILE")
    tls_ca_certfile = os.environ.get("STRANDS_TLS_CA_CERTFILE")

    mode: TlsMode | None = None
    if tls_mode_raw:
        if tls_mode_raw.lower() == "platform":
            logger.error("STRANDS_TLS_MODE=platform is no longer accepted. Use STRANDS_TLS_MODE=off instead.")
            sys.exit(1)
        try:
            mode = TlsMode(tls_mode_raw.lower())
        except ValueError:
            logger.error(
                "Invalid STRANDS_TLS_MODE value: %s. Accepted values: off, native",
                tls_mode_raw,
            )
            sys.exit(1)

    return TlsConfig(
        tls_mode=mode,
        tls_keyfile=tls_keyfile,
        tls_certfile=tls_certfile,
        tls_ca_certfile=tls_ca_certfile,
    )


def validate_tls_config(config: TlsConfig) -> None:
    """Validate TLS configuration. Exits the process if invalid."""
    if config.tls_mode is None:
        logger.error(
            "STRANDS_TLS_MODE is not set. The server requires an explicit "
            "TLS posture declaration. Set to 'off' (TLS handled by "
            "ingress/service mesh) or 'native' (uvicorn terminates TLS). "
            "env.template lists the related STRANDS_TLS_* settings."
        )
        sys.exit(1)

    if config.tls_mode == TlsMode.NATIVE:
        if not config.tls_keyfile:
            logger.error("STRANDS_TLS_KEYFILE is required when tls_mode=native")
            sys.exit(1)
        if not config.tls_certfile:
            logger.error("STRANDS_TLS_CERTFILE is required when tls_mode=native")
            sys.exit(1)

        keyfile_path = Path(config.tls_keyfile)
        certfile_path = Path(config.tls_certfile)

        if not keyfile_path.exists() or not keyfile_path.is_file():
            logger.error(
                "TLS key file does not exist or is not readable: %s",
                config.tls_keyfile,
            )
            sys.exit(1)
        if not certfile_path.exists() or not certfile_path.is_file():
            logger.error(
                "TLS cert file does not exist or is not readable: %s",
                config.tls_certfile,
            )
            sys.exit(1)

        if config.tls_ca_certfile:
            ca_certfile_path = Path(config.tls_ca_certfile)
            if not ca_certfile_path.exists() or not ca_certfile_path.is_file():
                logger.error(
                    "TLS CA cert file does not exist or is not readable: %s",
                    config.tls_ca_certfile,
                )
                sys.exit(1)

    if config.tls_mode == TlsMode.OFF:
        logger.info("TLS posture: off — TLS terminated by external ingress/service mesh. Uvicorn serving plain HTTP.")
    elif config.tls_mode == TlsMode.NATIVE:
        tls_extra: dict[str, str | None] = {
            "tls_keyfile": config.tls_keyfile,
            "tls_certfile": config.tls_certfile,
        }
        if config.tls_ca_certfile:
            tls_extra["tls_ca_certfile"] = config.tls_ca_certfile
        logger.info(
            "TLS posture: native — uvicorn terminating TLS%s",
            " (mTLS enabled)" if config.tls_ca_certfile else "",
            extra=tls_extra,
        )
