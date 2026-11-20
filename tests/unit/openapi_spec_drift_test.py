# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""docs/openapi.yml must match what scripts/generate_openapi.py produces."""

import yaml

from scripts.generate_openapi import OUTPUT_PATH, build_schema


def test_committed_openapi_spec_matches_generated_schema() -> None:
    committed = yaml.safe_load(OUTPUT_PATH.read_text())
    assert committed == build_schema(), (
        "docs/openapi.yml is out of date. Run: uv run python scripts/generate_openapi.py"
    )
