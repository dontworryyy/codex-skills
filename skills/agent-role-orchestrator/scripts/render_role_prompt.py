#!/usr/bin/env python3
"""Render a fail-closed role-window prompt for agent-role-orchestrator."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


CANONICAL_ROLES = {
    "ceo": "总控",
    "总控": "总控",
    "cto": "架构",
    "架构": "架构",
    "开发": "开发",
    "ui": "UI/PPT",
    "ui/ppt": "UI/PPT",
    "ui/frontend": "UI/PPT",
    "UI/PPT": "UI/PPT",
    "UI/Frontend": "UI/PPT",
    "测试": "测试",
    "qa": "QA",
    "QA": "QA",
    "安全": "安全",
    "dba": "DBA",
    "DBA": "DBA",
    "运维": "运维",
    "内容主编": "内容主编",
    "公众号发布": "公众号发布",
    "小红书": "小红书",
    "视频": "视频",
    "知识库": "知识库",
    "技能维护": "技能维护",
    "文档/交付": "文档/交付",
    "文档": "文档/交付",
}

ROLE_TREE_POSITION = {
    "总控": "总控 / CEO",
    "架构": "总控 / CEO -> 架构 / CTO",
    "开发": "总控 / CEO -> 架构 / CTO -> 开发",
    "UI/PPT": "总控 / CEO -> 架构 / CTO 或 内容主编 -> UI/PPT / UI/Frontend",
    "测试": "总控 / CEO -> 架构 / CTO -> 测试",
    "QA": "总控 / CEO -> 架构 / CTO -> QA",
    "安全": "总控 / CEO -> 架构 / CTO -> 安全",
    "DBA": "总控 / CEO -> 架构 / CTO -> DBA",
    "运维": "总控 / CEO -> 架构 / CTO -> 运维",
    "内容主编": "总控 / CEO -> 内容主编",
    "公众号发布": "总控 / CEO -> 内容主编 -> 公众号发布",
    "小红书": "总控 / CEO -> 内容主编 -> 小红书",
    "视频": "总控 / CEO -> 内容主编 -> 视频",
    "知识库": "总控 / CEO -> 知识库",
    "技能维护": "总控 / CEO -> 技能维护",
    "文档/交付": "总控 / CEO -> 文档/交付",
}

TECHNICAL_ROLES = {"架构", "开发", "UI/PPT", "测试", "QA", "安全", "DBA", "运维"}
CONTENT_ROLES = {"内容主编", "公众号发布", "小红书", "视频"}


@dataclass(frozen=True)
class ModelRoute:
    model: str
    thinking: str
    escalation: str


def canonical_role(raw: str) -> str:
    role = CANONICAL_ROLES.get(raw, CANONICAL_ROLES.get(raw.lower()))
    if not role:
        choices = "、".join(sorted(set(CANONICAL_ROLES.values())))
        raise ValueError(f"unknown role {raw!r}; choose one of: {choices}")
    return role


def model_route(role: str, risk: str) -> ModelRoute:
    if role in {"总控", "架构"}:
        return ModelRoute("gpt-5.5", "xhigh", "降级仅限低风险摘要或已确认的机械同步。")
    if role == "开发":
        return ModelRoute("gpt-5.3-codex-spark", "xhigh", "复杂架构决策或跨系统高风险变更回流架构/总控。")
    if role == "QA":
        if risk == "critical":
            return ModelRoute("gpt-5.5", "xhigh", "普通验收可降级到 gpt-5.3-codex-spark + high。")
        return ModelRoute("gpt-5.3-codex-spark", "high", "关键 PR、对抗式审查、发布门禁升级到 gpt-5.5 + xhigh。")
    if role in {"技能维护", "文档/交付", "知识库"}:
        return ModelRoute("gpt-5.3-codex-spark", "high", "小型文档/registry 机械编辑可降级到 gpt-5.4-mini。")
    if role in CONTENT_ROLES:
        return ModelRoute("gpt-5.3-codex-spark", "high", "高风险公开定位、声明、合规或跨平台策略升级到 gpt-5.5 + xhigh。")
    return ModelRoute("gpt-5.3-codex-spark", "high", "涉及高风险决策或跨角色协调时回流总控/架构。")


def lines_or_default(values: list[str], default: str) -> str:
    if not values:
        return f"- {default}"
    return "\n".join(f"- {value}" for value in values)


def csv_or_default(values: list[str], default: str) -> str:
    return "、".join(values) if values else default


def route_check_value(value: bool) -> str:
    return "是" if value else "待确认"


def build_prompt(args: argparse.Namespace) -> str:
    role = canonical_role(args.role)
    route = model_route(role, args.risk)
    source_role = args.source_role or ("用户" if role in {"总控", "架构"} else "待确认")
    source_thread = args.source_thread or "待确认"
    project = args.project or "待确认"
    required_skills = args.required_skill or []
    optional_skills = args.optional_skill or []
    candidate_skills = args.candidate_skill or []
    skipped_skills = args.skipped_skill or []
    read_first = args.read_first or []
    allowed = args.allow or []
    forbidden = args.forbid or []
    validation = args.validation or []
    callback_target = f"{source_role} / thread id: {source_thread}"
    needs_technical = "必填" if role == "架构" else "不适用"
    needs_codegraph = "必填" if args.new_code_project or role == "架构" else "不适用"
    needs_scan = "必填" if role == "架构" else "不适用"

    return f"""【给 {role} 窗口的提示词】

你现在担任：
{role}

背景：
- 项目/路径：{project}
- 交接方式：{args.mode}
- 来源窗口：{callback_target}
- 当前已知上下文：{args.context or "待确认"}

模型建议：
- model：{route.model}
- thinking：{route.thinking}
- 升级/降级条件：{route.escalation}

角色树位置（总控/架构/内容主编/执行角色）：
{ROLE_TREE_POSITION[role]}

技术方案（架构/CTO 处理复杂技术需求必填；已选定则写明选型）：
- 状态：{needs_technical}
- 方案 A：待确认
- 方案 B：待确认
- 方案 C：待确认
- 推荐：待确认
- 待确认：待确认

目标：
{args.objective}

请先阅读/检查：
{lines_or_default(read_first, "agent-role-orchestrator/SKILL.md；项目 .codex/role-windows.md（若存在）；与目标直接相关的项目文件")}

允许修改：
{lines_or_default(allowed, "待确认；未确认前只读")}

禁止修改：
{lines_or_default(forbidden, "未授权的生产环境、账号设置、凭据、发布动作、数据库写操作、无关重构")}

实现/工作要求：
{args.work_requirements or "按角色边界推进；不确定信息写待确认；不要编造线程、事实、验证结果或发布状态。"}

验证：
{lines_or_default(validation, "说明无法验证的原因；可验证项必须给出命令、文件、截图或人工检查步骤")}

闭环状态：
- 当前状态：{args.loop_state}
- 上一轮反馈：{args.previous_feedback or "无 / 待确认"}
- 本轮退出条件：{args.exit_condition or "完成目标、阻塞并说明证据、或需要来源窗口决策"}

上下文预算：
- 不搬运完整聊天记录、长日志或大段源码；默认只传状态增量、证据句柄、决策需求和下一回流对象。
- 每次派发、回调、阻塞、完成或纠偏后，更新 .codex/role-windows.md；长任务同时刷新“压缩交接卡”。
- 当上下文接近过长、compact 失败、或任务跨越多个闭环时，先用台账、提交、PR、文件证据和压缩交接卡接续，不要求新窗口读取完整旧线程。

CodeGraph 状态（新本地代码项目必填；不适用时写明原因）：
- 可用性：{needs_codegraph}
- 初始化状态：待确认
- 索引路径/忽略策略：待确认
- 跳过或失败原因：待确认

路由前检查（总控、架构、内容主编和多角色派发必填）：
- 是否读取 agent-role-orchestrator：{route_check_value(args.read_orchestrator)}
- 是否读取 .codex/role-windows.md：{route_check_value(args.read_ledger)}
- 是否复用已有角色线程：{args.reuse_thread or "待确认"}
- 是否写清模型建议/覆盖：是
- 是否写清 source-window callback：是
- 是否写清允许/禁止范围：是
- 是否写清验证与提交要求：是
- 是否包含技能路由台账：是
- 是否需要更新 .codex/role-windows.md：{args.update_ledger or "待确认"}

技能路由台账（总控、架构、内容主编和多角色拆分必填；单一执行角色可写“不适用/继承来源台账”）：
- 候选 skill：{csv_or_default(candidate_skills, "待确认")}
- 必选 skill：{csv_or_default(required_skills, "无 / 待确认")}
- 可选 skill：{csv_or_default(optional_skills, "无 / 待确认")}
- 跳过 skill 及原因：{csv_or_default(skipped_skills, "无")}
- 预期加载角色：{role}

开源/可借鉴方案扫描（架构/CTO 技术窗口必填；非架构窗口仅在被明确指派时填写）：
- 状态：{needs_scan}
- 检索关键词：待确认
- 候选方案：待确认
- 可借鉴点：待确认
- 不采用/风险：待确认
- 对下游工作的约束：待确认

提交/PR 要求：
{args.commit_requirements or "遵循项目 AGENTS.md；未要求提交时先回报变更和验证证据。"}

回调/通知规则：
- 本任务发起方：{callback_target}。
- 完成、阻塞或需要发起方决策时，主动通知发起方窗口；不要只等待用户转述。
- 如无法直接发送到发起方窗口，请输出一段可复制的“给发起方的回调消息”。

结构化反馈格式（返工/验收失败/需要决策时必填）：
- 问题/缺口：
- 证据/复现：
- 影响等级：
- 建议回流对象：
- 需要决策：
- 下一闭环状态：

压缩回调：
- 当前状态：
- 本轮变化：
- 证据链接/文件/命令：
- 需要决策：
- 下一回流对象：

技能命中回传：
- 已加载并使用：
- 来源窗口要求但未使用：
- 临时发现应补用：
- 误召/无效加载：
- 影响产出的 skill：

规则沉淀：
- 可复用优化沉淀：无 / 建议 / 已沉淀
- 具体问题或优化：
- 目标位置：skill / README / 角色提示词 / QA 清单 / 验证命令 / registry / source policy / 项目文档 / 待确认
- 已执行变更或建议后续：

完成后请回传：
{args.return_requirements or "压缩回调、验证证据、技能命中回传、规则沉淀状态。"}

角色底线：
{args.boundary or "守住角色边界；不越权发布、写生产、改凭据、编造证据或扩大范围。"}
"""


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a copy-paste role prompt with mandatory loop, callback, skill-hit, and model-routing fields.",
    )
    parser.add_argument("--role", required=True, help="Canonical role or alias, e.g. 总控, 架构, 开发, QA, 内容主编.")
    parser.add_argument("--objective", required=True, help="Concrete task objective. Required to avoid blank prompts.")
    parser.add_argument("--project", help="Project path or scope.")
    parser.add_argument("--mode", default="新建", choices=["新建", "继承", "接续", "重置"])
    parser.add_argument("--risk", default="normal", choices=["normal", "critical"], help="Use critical for release gates, adversarial QA, compliance, or high-risk public claims.")
    parser.add_argument("--source-role", help="Source/callback role. Defaults to 用户 only for 总控/架构, otherwise 待确认.")
    parser.add_argument("--source-thread", help="Source thread id. Defaults to 待确认.")
    parser.add_argument("--context", help="Short known context.")
    parser.add_argument("--read-first", action="append", default=[], help="Required file/doc to read first. Repeatable.")
    parser.add_argument("--allow", action="append", default=[], help="Allowed file/surface. Repeatable.")
    parser.add_argument("--forbid", action="append", default=[], help="Forbidden file/surface/action. Repeatable.")
    parser.add_argument("--validation", action="append", default=[], help="Validation command or manual check. Repeatable.")
    parser.add_argument("--candidate-skill", action="append", default=[], help="Candidate skill. Repeatable.")
    parser.add_argument("--required-skill", action="append", default=[], help="Required skill. Repeatable.")
    parser.add_argument("--optional-skill", action="append", default=[], help="Optional skill. Repeatable.")
    parser.add_argument("--skipped-skill", action="append", default=[], help="Skipped skill with reason, e.g. skill: reason. Repeatable.")
    parser.add_argument("--loop-state", default="待确认")
    parser.add_argument("--previous-feedback")
    parser.add_argument("--exit-condition")
    parser.add_argument("--reuse-thread")
    parser.add_argument("--update-ledger")
    parser.add_argument("--work-requirements")
    parser.add_argument("--commit-requirements")
    parser.add_argument("--return-requirements")
    parser.add_argument("--boundary")
    parser.add_argument("--read-orchestrator", action="store_true", help="Mark orchestrator skill as read.")
    parser.add_argument("--read-ledger", action="store_true", help="Mark project role ledger as read.")
    parser.add_argument("--new-code-project", action="store_true", help="Require CodeGraph status fields.")
    parser.add_argument("--output", type=Path, help="Write prompt to file instead of stdout.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
        prompt = build_prompt(args)
    except Exception as exc:  # noqa: BLE001
        print(f"render_role_prompt failed: {exc}", file=sys.stderr)
        return 2

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(prompt, encoding="utf-8")
    else:
        print(prompt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
