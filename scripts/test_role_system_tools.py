#!/usr/bin/env python3
"""Regression tests for role-system fail-closed helper scripts."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
ENSURE = ROOT / "skills" / "agent-role-orchestrator" / "scripts" / "ensure_project_role_files.py"
VALIDATE_ROLE_SYSTEM = ROOT / "scripts" / "validate_role_system.py"


def run(args: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=str(cwd or ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"command failed ({result.returncode}): {' '.join(args)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return result


def test_project_role_file_bootstrap() -> None:
    with tempfile.TemporaryDirectory() as temp:
        project = Path(temp)

        dry_run = run([PYTHON, str(ENSURE), "--project", str(project)])
        assert "DRY-RUN" in dry_run.stdout
        assert not (project / "AGENTS.md").exists()
        assert not (project / ".codex" / "role-windows.md").exists()

        written = run([PYTHON, str(ENSURE), "--project", str(project), "--write"])
        assert "WRITE" in written.stdout

        agents = project / "AGENTS.md"
        ledger = project / ".codex" / "role-windows.md"
        assert agents.exists()
        assert ledger.exists()
        assert "BEGIN agent-role-orchestrator entry rule" in agents.read_text(encoding="utf-8")
        assert "总控/架构/多角色/派发/回调/台账类任务必须先使用 agent-role-orchestrator" in agents.read_text(encoding="utf-8")
        assert "| 总控 | 待确认 | 待确认 | 用户 | 入口分流" in ledger.read_text(encoding="utf-8")

        second = run([PYTHON, str(ENSURE), "--project", str(project), "--write"])
        assert "OK" in second.stdout
        assert agents.read_text(encoding="utf-8").count("BEGIN agent-role-orchestrator entry rule") == 1


def test_existing_agents_file_is_preserved() -> None:
    with tempfile.TemporaryDirectory() as temp:
        project = Path(temp)
        agents = project / "AGENTS.md"
        agents.write_text("# AGENTS.md\n\n- 原有项目规则\n", encoding="utf-8")

        run([PYTHON, str(ENSURE), "--project", str(project), "--write"])

        text = agents.read_text(encoding="utf-8")
        assert "- 原有项目规则" in text
        assert "BEGIN agent-role-orchestrator entry rule" in text


def test_role_system_validator() -> None:
    result = run([PYTHON, str(VALIDATE_ROLE_SYSTEM)])
    assert "Role system validation passed" in result.stdout


def main() -> int:
    tests = [
        test_project_role_file_bootstrap,
        test_existing_agents_file_is_preserved,
        test_role_system_validator,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
