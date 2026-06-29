#!/usr/bin/env python3
"""Fail-closed checks for agent-role-orchestrator ledgers, prompts, and callbacks."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


CANONICAL_ROLES = [
    "总控",
    "架构",
    "开发",
    "UI/PPT",
    "测试",
    "QA",
    "安全",
    "DBA",
    "运维",
    "内容主编",
    "公众号发布",
    "小红书",
    "视频",
    "知识库",
    "技能维护",
    "文档/交付",
]

ALLOWED_STATUSES = {"未建立", "已建立", "接续中", "已关闭", "误开/废弃", "待确认"}
PLACEHOLDERS = {"", "TODO", "TBD", "<待填写>", "<todo>", "null", "None"}

PROMPT_REQUIRED_MARKERS = [
    "模型建议：",
    "角色树位置",
    "目标：",
    "请先阅读/检查：",
    "允许修改：",
    "禁止修改：",
    "验证：",
    "闭环状态：",
    "路由前检查",
    "技能路由台账",
    "回调/通知规则：",
    "结构化反馈格式",
    "压缩回调：",
    "技能命中回传：",
    "规则沉淀：",
]

CALLBACK_REQUIRED_MARKERS = [
    "压缩回调：",
    "当前状态：",
    "本轮变化：",
    "证据链接/文件/命令：",
    "需要决策：",
    "下一回流对象：",
    "技能命中回传：",
    "已加载并使用：",
    "来源窗口要求但未使用：",
    "临时发现应补用：",
    "误召/无效加载：",
    "影响产出的 skill：",
    "规则沉淀：",
    "可复用优化沉淀：",
]


@dataclass
class CheckResult:
    target: str
    errors: list[str]
    warnings: list[str]
    metrics: dict[str, object]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def has_placeholder_value(line: str) -> bool:
    stripped = line.strip()
    if "：" in line:
        value = line.split("：", 1)[1].strip()
    elif ":" in line:
        value = line.split(":", 1)[1].strip()
    else:
        return False
    if not value and not stripped.startswith("-"):
        return False
    return value in PLACEHOLDERS


def missing_markers(text: str, markers: list[str]) -> list[str]:
    return [marker for marker in markers if marker not in text]


def extract_field(text: str, field: str) -> str:
    pattern = re.compile(rf"{re.escape(field)}[ \t]*[:：][ \t]*(.*)")
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def split_skill_list(value: str) -> set[str]:
    value = value.strip()
    if not value or value in {"无", "不适用", "待确认", "无 / 待确认"}:
        return set()
    parts = re.split(r"[、,，;；\n]+", value)
    cleaned = set()
    for part in parts:
        item = part.strip().strip("- ").strip()
        if not item or item in {"无", "不适用", "待确认"}:
            continue
        if ":" in item:
            item = item.split(":", 1)[0].strip()
        if "：" in item:
            item = item.split("：", 1)[0].strip()
        cleaned.add(item)
    return cleaned


def validate_ledger(path: Path) -> CheckResult:
    errors: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, object] = {}

    if not path.is_file():
        return CheckResult(str(path), [f"ledger missing: {path}"], warnings, metrics)

    text = read_text(path)
    seen_roles = set()
    seen_statuses = set()

    for role in CANONICAL_ROLES:
        if role in text:
            seen_roles.add(role)

    for line_no, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        if has_placeholder_value(stripped):
            errors.append(f"line {line_no}: placeholder value is not allowed: {stripped}")
        for role in CANONICAL_ROLES:
            if role not in stripped:
                continue
            statuses = {status for status in ALLOWED_STATUSES if status in stripped}
            if statuses:
                seen_statuses.update(statuses)
            elif re.search(rf"(^|\s|-){re.escape(role)}\s*[:：]", stripped):
                errors.append(f"line {line_no}: role {role} has no allowed lifecycle status")
        if re.search(r"(thread|线程|thread id|thread_id)\s*[:：]\s*$", stripped, re.IGNORECASE):
            errors.append(f"line {line_no}: blank thread id; use 待确认 when unknown")

    if not seen_roles:
        errors.append("ledger does not mention any canonical role")
    for expected in ("总控", "架构"):
        if expected not in seen_roles:
            errors.append(f"ledger missing top-level role: {expected}")
    if not seen_statuses:
        errors.append("ledger does not contain any allowed lifecycle status")

    if "待确认" in text:
        warnings.append("ledger contains 待确认; confirm before creating/continuing affected windows")

    metrics["roles_seen"] = sorted(seen_roles)
    metrics["statuses_seen"] = sorted(seen_statuses)
    return CheckResult(str(path), errors, warnings, metrics)


def validate_prompt(path: Path) -> CheckResult:
    errors: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, object] = {}
    text = read_text(path)

    for marker in missing_markers(text, PROMPT_REQUIRED_MARKERS):
        errors.append(f"missing prompt marker: {marker}")

    model = extract_field(text, "model")
    thinking = extract_field(text, "thinking")
    if not model or model == "待确认":
        errors.append("模型建议.model is blank or 待确认")
    if not thinking or thinking == "待确认":
        errors.append("模型建议.thinking is blank or 待确认")

    source = extract_field(text, "本任务发起方")
    if not source:
        errors.append("callback source is missing")

    required = split_skill_list(extract_field(text, "必选 skill"))
    candidate = split_skill_list(extract_field(text, "候选 skill"))
    metrics["required_skills"] = sorted(required)
    metrics["candidate_skills"] = sorted(candidate)

    if "是否读取 agent-role-orchestrator：" in text and "是否读取 agent-role-orchestrator：是" not in text:
        warnings.append("prompt does not confirm agent-role-orchestrator was read")
    if "是否读取 .codex/role-windows.md：" in text and "是否读取 .codex/role-windows.md：是" not in text:
        warnings.append("prompt does not confirm .codex/role-windows.md was read")

    return CheckResult(str(path), errors, warnings, metrics)


def validate_callback(path: Path, required_skills: set[str]) -> CheckResult:
    errors: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, object] = {}
    text = read_text(path)

    for marker in missing_markers(text, CALLBACK_REQUIRED_MARKERS):
        errors.append(f"missing callback marker: {marker}")

    loaded = split_skill_list(extract_field(text, "已加载并使用"))
    declared_unused = split_skill_list(extract_field(text, "来源窗口要求但未使用"))
    missing_required = sorted(required_skills - loaded - declared_unused)

    if missing_required:
        errors.append("required skills neither loaded nor declared unused: " + "、".join(missing_required))

    if "下一回流对象：" in text and "下一回流对象：" + "\n" in text:
        errors.append("blank 下一回流对象; use a role name or 待确认 with reason")

    if "可复用优化沉淀：" not in text:
        errors.append("missing reusable sedimentation status")
    else:
        sediment = extract_field(text, "可复用优化沉淀")
        if sediment and not any(token in sediment for token in ("无", "建议", "已沉淀")):
            errors.append("可复用优化沉淀 must be one of: 无 / 建议 / 已沉淀")

    for line_no, line in enumerate(text.splitlines(), 1):
        if has_placeholder_value(line.strip()):
            errors.append(f"line {line_no}: placeholder value is not allowed: {line.strip()}")

    metrics["loaded_skills"] = sorted(loaded)
    metrics["declared_unused_required_skills"] = sorted(declared_unused)
    metrics["required_skill_count"] = len(required_skills)
    metrics["loaded_required_skill_count"] = len(required_skills & loaded)
    metrics["skill_hit_rate"] = 1.0 if not required_skills else round(len(required_skills & loaded) / len(required_skills), 4)
    if declared_unused:
        warnings.append("some required skills were declared unused: " + "、".join(sorted(declared_unused)))

    return CheckResult(str(path), errors, warnings, metrics)


def print_result(result: CheckResult) -> None:
    status = "PASS" if not result.errors else "FAIL"
    print(f"[{status}] {result.target}")
    for error in result.errors:
        print(f"  ERROR: {error}")
    for warning in result.warnings:
        print(f"  WARN: {warning}")
    if result.metrics:
        print("  METRICS: " + json.dumps(result.metrics, ensure_ascii=False, sort_keys=True))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate role-window ledgers, generated prompts, and callback messages. Exits non-zero on missing mechanical fields.",
    )
    parser.add_argument("--project", type=Path, help="Project root; validates .codex/role-windows.md by default.")
    parser.add_argument("--ledger", type=Path, help="Explicit role-windows ledger file.")
    parser.add_argument("--allow-missing-ledger", action="store_true", help="Do not fail when project ledger is absent.")
    parser.add_argument("--prompt", type=Path, action="append", default=[], help="Prompt file to validate. Repeatable.")
    parser.add_argument("--callback", type=Path, action="append", default=[], help="Callback file to validate. Repeatable.")
    parser.add_argument("--required-skill", action="append", default=[], help="Required skill expected in callback. Repeatable.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    targets = []
    results: list[CheckResult] = []

    if args.project:
        ledger = args.project / ".codex" / "role-windows.md"
        if ledger.exists() or not args.allow_missing_ledger:
            targets.append(("ledger", ledger))
    if args.ledger:
        targets.append(("ledger", args.ledger))
    for prompt in args.prompt:
        targets.append(("prompt", prompt))
    for callback in args.callback:
        targets.append(("callback", callback))

    if not targets:
        print("validate_role_loop failed: provide --project, --ledger, --prompt, or --callback", file=sys.stderr)
        return 2

    required_skills = set(args.required_skill)
    for kind, path in targets:
        if kind == "ledger":
            result = validate_ledger(path)
        elif kind == "prompt":
            result = validate_prompt(path)
            required_skills.update(result.metrics.get("required_skills", []))
        else:
            result = validate_callback(path, required_skills)
        results.append(result)

    if args.json:
        print(json.dumps([result.__dict__ for result in results], ensure_ascii=False, indent=2))
    else:
        for result in results:
            print_result(result)

    return 1 if any(result.errors for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
