# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for where first-party dependencies resolve from.

Every foundry-* dependency must have a [tool.uv.sources] entry. Without one, uv
resolves the name from PyPI, where foundry-* names are unclaimed and could be
registered by anyone.
"""

import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"
FIRST_PARTY_PREFIX = "foundry-"


def _declared_dependencies(manifest: dict) -> set[str]:
    """Collect canonical dependency names from the project, its extras, and its dependency groups."""
    project = manifest.get("project", {})
    requirements = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        requirements.extend(extra)
    for group in manifest.get("dependency-groups", {}).values():
        requirements.extend(item for item in group if isinstance(item, str))
    return {canonicalize_name(Requirement(requirement).name) for requirement in requirements}


class TestFirstPartyDependencySources:
    """Every foundry-* dependency is pinned to a source in pyproject.toml."""

    def test_every_foundry_dependency_has_a_source_entry(self) -> None:
        manifest = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
        sources = manifest.get("tool", {}).get("uv", {}).get("sources", {})
        pinned = {canonicalize_name(name) for name in sources}
        first_party = {name for name in _declared_dependencies(manifest) if name.startswith(FIRST_PARTY_PREFIX)}

        missing = sorted(first_party - pinned)

        assert first_party, "expected at least one foundry-* dependency in pyproject.toml"
        assert not missing, (
            f"foundry-* dependencies without a [tool.uv.sources] entry: {missing}. "
            "Add an entry for each under [tool.uv.sources] in pyproject.toml, pointing at the same source "
            "as the existing foundry-* entries."
        )
