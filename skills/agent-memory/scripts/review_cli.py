# -*- coding: utf-8 -*-
"""
Review CLI - 审核协作命令

用法：
    python -m skills.agent-memory.scripts.review_cli request <experience_code> --reviewer-id <id> --comment <msg>
    python -m skills.agent-memory.scripts.review_cli submit <review_id> --reviewer-id <id> --decision approve --comment <msg>
    python -m skills.agent-memory.scripts.review_cli comment <review_id> --author-id <id> --comment <msg> --line 10
    python -m skills.agent-memory.scripts.review_cli list --reviewer-id <id> --status requested
    python -m skills.agent-memory.scripts.review_cli pending --reviewer-id <id>
    python -m skills.agent-memory.scripts.review_cli get <review_id>
    python -m skills.agent-memory.scripts.review_cli experience <code>
"""

import sys
import json
import argparse
from typing import Optional

# 导入 client（agent-memory 包，无 skills 前缀）
from agent_memory.scripts.client import (
    request_review,
    submit_review,
    add_review_comment,
    resolve_review_comment,
    get_review,
    list_reviews,
    list_pending_reviews,
    get_experience_full,
    get_experience,
    DatabaseError,
)


def cmd_request(args):
    """请求审核"""
    try:
        result = request_review(
            experience_code=args.experience_code,
            requester_id=args.requester_id,
            requester_name=args.requester_name,
            reviewer_id=args.reviewer_id,
            comment=args.comment,
            agent_id=args.agent_id or "cli",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except DatabaseError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


def cmd_submit(args):
    """提交审核决定"""
    try:
        result = submit_review(
            review_id=args.review_id,
            reviewer_id=args.reviewer_id,
            decision=args.decision,
            comment=args.comment,
            agent_id=args.agent_id or "cli",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (DatabaseError, ValueError) as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


def cmd_comment(args):
    """添加批注"""
    try:
        result = add_review_comment(
            review_id=args.review_id,
            author_id=args.author_id,
            comment=args.comment,
            author_name=args.author_name,
            line_number=args.line,
            field_name=args.field,
            severity=args.severity or "suggestion",
            agent_id=args.agent_id or "cli",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except DatabaseError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


def cmd_resolve(args):
    """标记批注已解决"""
    try:
        result = resolve_review_comment(
            comment_id=args.comment_id,
            resolved_by=args.resolved_by,
            agent_id=args.agent_id or "cli",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except DatabaseError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


def cmd_list(args):
    """列出 Review"""
    try:
        results = list_reviews(
            experience_code=args.experience_code,
            reviewer_id=args.reviewer_id,
            status=args.status,
            requester_id=args.requester_id,
            limit=args.limit or 50,
        )
        print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
        return 0
    except DatabaseError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


def cmd_pending(args):
    """列出待我审核的经验"""
    try:
        results = list_pending_reviews(reviewer_id=args.reviewer_id)
        print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
        return 0
    except DatabaseError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


def cmd_get(args):
    """获取 Review 详情"""
    try:
        result = get_review(review_id=args.review_id)
        if result is None:
            print(f"Review 不存在: {args.review_id}", file=sys.stderr)
            return 1
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0
    except DatabaseError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


def cmd_experience(args):
    """获取经验详情 + 所有 Review"""
    try:
        result = get_experience_full(code=args.code)
        if result is None:
            print(f"经验不存在: {args.code}", file=sys.stderr)
            return 1
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0
    except DatabaseError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Agent Memory - Review CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # request
    p = subparsers.add_parser("request", help="请求审核（提交经验供审核）")
    p.add_argument("experience_code", help="经验代码")
    p.add_argument("--requester-id", required=True, help="请求者 Agent ID（作者）")
    p.add_argument("--requester-name", help="请求者显示名")
    p.add_argument("--reviewer-id", help="指定审核人 ID")
    p.add_argument("--comment", help="附言")
    p.add_argument("--agent-id", help="当前 Agent 标识")
    p.set_defaults(func=cmd_request)

    # submit
    p = subparsers.add_parser("submit", help="提交审核决定")
    p.add_argument("review_id", help="Review ID")
    p.add_argument("--reviewer-id", required=True, help="审核人 Agent ID")
    p.add_argument("--decision", required=True, choices=["approve", "request_changes", "reject"], help="审核决定")
    p.add_argument("--comment", help="审核意见")
    p.add_argument("--agent-id", help="当前 Agent 标识")
    p.set_defaults(func=cmd_submit)

    # comment
    p = subparsers.add_parser("comment", help="添加批注")
    p.add_argument("review_id", help="Review ID")
    p.add_argument("--author-id", required=True, help="批注作者 ID")
    p.add_argument("--comment", required=True, help="批注内容")
    p.add_argument("--author-name", help="批注作者显示名")
    p.add_argument("--line", type=int, help="行号")
    p.add_argument("--field", help="字段名")
    p.add_argument("--severity", choices=["suggestion", "warning", "error"], help="严重程度")
    p.add_argument("--agent-id", help="当前 Agent 标识")
    p.set_defaults(func=cmd_comment)

    # resolve
    p = subparsers.add_parser("resolve", help="标记批注已解决")
    p.add_argument("comment_id", help="批注 ID")
    p.add_argument("--resolved-by", required=True, help="解决者 ID")
    p.add_argument("--agent-id", help="当前 Agent 标识")
    p.set_defaults(func=cmd_resolve)

    # list
    p = subparsers.add_parser("list", help="列出 Review")
    p.add_argument("--experience-code", help="经验代码过滤")
    p.add_argument("--reviewer-id", help="审核人过滤")
    p.add_argument("--requester-id", help="请求者过滤")
    p.add_argument("--status", choices=["requested", "approved", "changes_requested"], help="状态过滤")
    p.add_argument("--limit", type=int, default=50, help="返回数量")
    p.set_defaults(func=cmd_list)

    # pending
    p = subparsers.add_parser("pending", help="列出待我审核的经验")
    p.add_argument("--reviewer-id", required=True, help="审核人 ID")
    p.set_defaults(func=cmd_pending)

    # get
    p = subparsers.add_parser("get", help="获取 Review 详情")
    p.add_argument("review_id", help="Review ID")
    p.set_defaults(func=cmd_get)

    # experience
    p = subparsers.add_parser("experience", help="获取经验详情 + 所有 Review")
    p.add_argument("code", help="经验代码")
    p.set_defaults(func=cmd_experience)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
