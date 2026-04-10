"""
Consistency tests for public-architecture-claude-code documentation.

Verifies that all markdown files use consistent terminology, endpoints,
and references across the repository.
"""
import os
import re
from pathlib import Path
from typing import Generator

import pytest

REPO_ROOT = Path(__file__).parent.parent
MD_FILES = sorted(REPO_ROOT.glob("**/*.md"))


def read_all_md() -> dict[str, str]:
    """Read all markdown files into a dict of {relative_path: content}."""
    result = {}
    for f in MD_FILES:
        if f.name == "test_consistency.py":
            continue
        rel = str(f.relative_to(REPO_ROOT))
        result[rel] = f.read_text(encoding="utf-8")
    return result


ALL_MD = read_all_md()


# --- OpenViking endpoint consistency ---

class TestOpenVikingEndpoints:
    """OpenViking endpoint references must be consistent."""

    def test_no_hardcoded_127_ip(self) -> None:
        """No file should use 127.0.0.1:1933 -- use localhost:1933 instead."""
        violations: list[tuple[str, int, str]] = []
        for path, content in ALL_MD.items():
            for i, line in enumerate(content.splitlines(), 1):
                if "127.0.0.1:1933" in line:
                    violations.append((path, i, line.strip()))

        assert not violations, (
            "Found 127.0.0.1:1933 references (use localhost:1933):\n"
            + "\n".join(f"  {p}:{n}: {l}" for p, n, l in violations)
        )

    def test_no_sessions_api_references(self) -> None:
        """No file should reference the old /api/v1/sessions endpoint."""
        violations: list[tuple[str, int, str]] = []
        for path, content in ALL_MD.items():
            for i, line in enumerate(content.splitlines(), 1):
                if "/api/v1/sessions" in line and "old" not in line.lower():
                    violations.append((path, i, line.strip()))

        assert not violations, (
            "Found /api/v1/sessions references (use temp_upload + add_resource):\n"
            + "\n".join(f"  {p}:{n}: {l}" for p, n, l in violations)
        )


# --- Cron schedule consistency ---

class TestCronSchedule:
    """Cron schedule must be consistent across files."""

    def test_ov_sync_cron_documented(self) -> None:
        """ov-session-sync.sh cron (06:30 UTC) must appear in all cron sections."""
        files_with_cron = []
        for path, content in ALL_MD.items():
            if "crontab" in content and "rotate-warm" in content:
                files_with_cron.append(path)

        assert files_with_cron, "No files with cron schedule found"

        for path in files_with_cron:
            content = ALL_MD[path]
            assert "ov-session-sync" in content, (
                f"{path} has cron schedule but missing ov-session-sync.sh"
            )

    def test_cron_order_correct(self) -> None:
        """Cron jobs must be in correct order within crontab blocks."""
        expected_order = [
            "rotate-warm",
            "trim-hot",
            "compress-warm",
            "ov-session-sync",
            "memory-rotate",
        ]

        for path, content in ALL_MD.items():
            if "crontab" not in content or "rotate-warm" not in content:
                continue

            # Extract only crontab code blocks to avoid matching
            # references in prose text
            crontab_blocks: list[str] = []
            in_crontab = False
            block_lines: list[str] = []
            for line in content.splitlines():
                if "```crontab" in line:
                    in_crontab = True
                    block_lines = []
                elif in_crontab and line.strip().startswith("```"):
                    crontab_blocks.append("\n".join(block_lines))
                    in_crontab = False
                elif in_crontab:
                    block_lines.append(line)

            for block in crontab_blocks:
                positions = {}
                for script in expected_order:
                    pos = block.find(script)
                    if pos >= 0:
                        positions[script] = pos

                if len(positions) < 2:
                    continue

                present = [(pos, name) for name, pos in positions.items()]
                present.sort()
                ordered_names = [name for _, name in present]

                for i in range(len(ordered_names) - 1):
                    a, b = ordered_names[i], ordered_names[i + 1]
                    a_idx = expected_order.index(a) if a in expected_order else -1
                    b_idx = expected_order.index(b) if b in expected_order else -1
                    if a_idx >= 0 and b_idx >= 0:
                        assert a_idx < b_idx, (
                            f"{path}: {a} should come before {b} in crontab block"
                        )


# --- OpenViking sync method consistency ---

class TestOpenVikingSyncMethod:
    """OpenViking sync must use temp_upload + add_resource, not sessions API."""

    def test_architecture_uses_batch_sync(self) -> None:
        """ARCHITECTURE.md must describe batch sync, not per-message push."""
        content = ALL_MD.get("ARCHITECTURE.md", "")
        assert "batch sync" in content.lower() or "temp_upload" in content, (
            "ARCHITECTURE.md should describe batch sync method"
        )
        assert "fire-and-forget after every message" not in content, (
            "ARCHITECTURE.md still contains old 'fire-and-forget' OpenViking description"
        )

    def test_memory_uses_resources_api(self) -> None:
        """MEMORY.md must reference resources API, not sessions API."""
        content = ALL_MD.get("MEMORY.md", "")
        assert "temp_upload" in content, (
            "MEMORY.md should document temp_upload method"
        )
        assert "add_resource" in content, (
            "MEMORY.md should document add_resource method"
        )

    def test_hooks_has_stop_example(self) -> None:
        """HOOKS.md must have a Stop hook example for OpenViking."""
        content = ALL_MD.get("HOOKS.md", "")
        assert "ov-session-sync" in content, (
            "HOOKS.md should have OpenViking Stop hook example"
        )


# --- HOT memory size consistency ---

class TestHotMemorySize:
    """HOT memory size claims must be consistent."""

    def test_hot_rolling_24h_not_48h(self) -> None:
        """HOT memory must be described as 24h rolling, never 48h or 72h."""
        violations: list[tuple[str, int, str]] = []
        for path, content in ALL_MD.items():
            for i, line in enumerate(content.splitlines(), 1):
                low = line.lower()
                # Skip skills that legitimately use 48h/72h for other purposes
                if "skills/" in path:
                    continue
                # Check for 48h/72h in HOT context
                if ("hot" in low or "trim" in low or "recent.md" in low) and (
                    "48h" in low or "48 h" in low or "72h" in low or "72 h" in low
                ):
                    violations.append((path, i, line.strip()))

        assert not violations, (
            "Found 48h/72h references in HOT memory context (should be 24h):\n"
            + "\n".join(f"  {p}:{n}: {l}" for p, n, l in violations)
        )

    def test_hot_size_warning_clarified(self) -> None:
        """80KB+ warning must mention it's before cron, not typical size."""
        content = ALL_MD.get("MEMORY.md", "")
        # Find the 80KB mention
        if "80KB+" in content:
            # Find the line with 80KB+
            for line in content.splitlines():
                if "80KB+" in line:
                    assert "before cron" in line.lower() or "before" in line.lower() or "cron" in line.lower(), (
                        f"80KB+ warning should clarify it's before cron runs: {line}"
                    )
                    break


# --- Cross-reference integrity ---

class TestCrossReferences:
    """Files referencing other files must reference existing files."""

    def test_no_mirrors_references(self) -> None:
        """No file should reference the deprecated mirrors/ directory."""
        violations: list[tuple[str, int, str]] = []
        for path, content in ALL_MD.items():
            for i, line in enumerate(content.splitlines(), 1):
                if "mirrors/" in line and ("OLD" in line or "old" in line or "→" in line):
                    continue  # Skip migration comparison lines
                if re.search(r"mirrors/\w+\.sh", line):
                    violations.append((path, i, line.strip()))

        assert not violations, (
            "Found mirrors/ script references (deprecated):\n"
            + "\n".join(f"  {p}:{n}: {l}" for p, n, l in violations)
        )


# --- Model version consistency ---

class TestModelVersions:
    """Model version references should be consistent."""

    def test_opus_version_consistent(self) -> None:
        """All Opus references should use the same version."""
        versions: set[str] = set()
        pattern = re.compile(r"Opus\s+(\d+\.\d+)")

        for path, content in ALL_MD.items():
            for match in pattern.finditer(content):
                versions.add(match.group(1))

        assert len(versions) <= 1, (
            f"Multiple Opus versions found: {versions}. Should be consistent."
        )

    def test_sonnet_version_consistent(self) -> None:
        """All Sonnet references should use the same version."""
        versions: set[str] = set()
        pattern = re.compile(r"Sonnet\s+(\d+\.\d+)")

        for path, content in ALL_MD.items():
            for match in pattern.finditer(content):
                versions.add(match.group(1))

        assert len(versions) <= 1, (
            f"Multiple Sonnet versions found: {versions}. Should be consistent."
        )
