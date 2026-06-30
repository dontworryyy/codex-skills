#!/usr/bin/env python3
"""Regression tests for role-system fail-closed helper scripts."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
ENSURE = ROOT / "skills" / "agent-role-orchestrator" / "scripts" / "ensure_project_role_files.py"
VALIDATE_LOOP = ROOT / "skills" / "agent-role-orchestrator" / "scripts" / "validate_role_loop.py"
CHECK_CODEGRAPH = ROOT / "skills" / "agent-role-orchestrator" / "scripts" / "check_codegraph.py"
AGGREGATE_SKILL_HITS = ROOT / "skills" / "agent-role-orchestrator" / "scripts" / "aggregate_skill_hits.py"
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
        agents_text = agents.read_text(encoding="utf-8")
        ledger_text = ledger.read_text(encoding="utf-8")
        assert "BEGIN agent-role-orchestrator entry rule" in agents_text
        assert "总控/架构/多角色/派发/回调/台账类任务必须先使用 agent-role-orchestrator" in agents_text
        machine_path_fragment = "\\".join(["C:", "Users"]) + "\\"
        assert machine_path_fragment not in agents_text
        assert "已安装的 agent-role-orchestrator/SKILL.md" in agents_text
        assert "| 总控 | 待确认 | 待确认 | 用户 | 入口分流" in ledger_text
        assert "## 压缩交接卡" in ledger_text

        run([PYTHON, str(VALIDATE_LOOP), "--project", str(project)])

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


def test_role_ledger_rejects_duplicate_threads_and_bad_status() -> None:
    with tempfile.TemporaryDirectory() as temp:
        project = Path(temp)
        ledger = project / ".codex" / "role-windows.md"
        ledger.parent.mkdir(parents=True)
        ledger.write_text(
            """# 角色窗口台账

| 角色 | 状态 | thread id | 来源窗口 | 当前职责 | 下一步 | 循环状态 |
| --- | --- | --- | --- | --- | --- | --- |
| 总控 | 已建立 | thread-1 | 用户 | 入口分流 | 继续验收 | 运行中 |
| 架构 | 已建立 | thread-1 | 总控 | 技术拆解 | 派发开发 | 运行中 |
| 内容主编 | 待确认 | 待确认 | 总控 | 内容分流 | 待确认 | 待确认 |
""",
            encoding="utf-8",
        )
        duplicate = run([PYTHON, str(VALIDATE_LOOP), "--project", str(project)], check=False)
        assert duplicate.returncode != 0
        assert "duplicate thread id" in duplicate.stdout

        ledger.write_text(
            """# 角色窗口台账

| 角色 | 状态 | thread id | 来源窗口 | 当前职责 | 下一步 | 循环状态 |
| --- | --- | --- | --- | --- | --- | --- |
| 总控 | 已建立 | thread-1 | 用户 | 入口分流 | 继续验收 | 运行中 |
| 架构 | 忙碌中 | thread-2 | 总控 | 技术拆解 | 派发开发 | 运行中 |
| 内容主编 | 待确认 | 待确认 | 总控 | 内容分流 | 待确认 | 待确认 |
""",
            encoding="utf-8",
        )
        bad_status = run([PYTHON, str(VALIDATE_LOOP), "--project", str(project)], check=False)
        assert bad_status.returncode != 0
        assert "invalid status" in bad_status.stdout


def test_check_codegraph_reports_state_without_guessing() -> None:
    with tempfile.TemporaryDirectory() as temp:
        project = Path(temp)
        missing = run([PYTHON, str(CHECK_CODEGRAPH), "--project", str(project), "--json"])
        missing_payload = json.loads(missing.stdout)
        assert missing_payload["project_exists"] is True
        assert missing_payload["initialized"] is False
        assert missing_payload["initialization_status"] == "未初始化"

        (project / ".codegraph").mkdir()
        initialized = run([PYTHON, str(CHECK_CODEGRAPH), "--project", str(project), "--json"])
        initialized_payload = json.loads(initialized.stdout)
        assert initialized_payload["initialized"] is True
        assert initialized_payload["initialization_status"] == "已初始化"


def test_aggregate_skill_hits_quantifies_required_actual_and_misfires() -> None:
    with tempfile.TemporaryDirectory() as temp:
        callbacks = Path(temp)
        (callbacks / "callback-1.md").write_text(
            """技能路由台账：
- 必选 skill：humanizer-zh、xhs-publish-assistant
技能命中回传：
- 已加载并使用：humanizer-zh
- 来源窗口要求但未使用：xhs-publish-assistant
- 临时发现应补用：cheat-on-content
- 误召/无效加载：story-deslop
- 影响产出的 skill：humanizer-zh
""",
            encoding="utf-8",
        )
        result = run([PYTHON, str(AGGREGATE_SKILL_HITS), str(callbacks), "--json"])
        payload = json.loads(result.stdout)
        assert payload["files_scanned"] == 1
        assert payload["required_skill_count"] == 2
        assert payload["loaded_required_skill_count"] == 1
        assert payload["declared_unused_required_skill_count"] == 1
        assert payload["missing_required_skill_count"] == 0
        assert payload["misfire_skill_count"] == 1
        assert payload["hit_rate"] == 0.5


def test_role_system_validator() -> None:
    result = run([PYTHON, str(VALIDATE_ROLE_SYSTEM)])
    assert "Role system validation passed" in result.stdout


def main() -> int:
    tests = [
        test_project_role_file_bootstrap,
        test_existing_agents_file_is_preserved,
        test_role_ledger_rejects_duplicate_threads_and_bad_status,
        test_check_codegraph_reports_state_without_guessing,
        test_aggregate_skill_hits_quantifies_required_actual_and_misfires,
        test_role_system_validator,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
