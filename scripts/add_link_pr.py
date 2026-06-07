#!/usr/bin/env python3
"""Create a reviewable add-link pull request.

This is the deterministic shell around the future Hermes `/addlink <url>` flow.
Hermes still chooses/enriches the title, category, tags, type, and description;
this script turns that enriched request into a branch, validation run, commit,
push, and GitHub PR.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path
from urllib.parse import urlsplit


def slugify(value: str, fallback: str = "link") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    return slug[:60].strip("-") or fallback


def branch_name(title: str, url: str) -> str:
    if title.strip():
        seed = title
    else:
        parsed = urlsplit(url)
        path = parsed.path.strip("/")
        seed = f"{parsed.netloc} {path}".strip()
    return f"addlink/{slugify(seed)}"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add a link and open a reviewable PR")
    parser.add_argument("url", help="HTTP(S) URL to add")
    parser.add_argument("--title", required=True, help="Enriched link title")
    parser.add_argument("--description", required=True, help="Short enriched description")
    parser.add_argument("--category", required=True, help="Display category")
    parser.add_argument("--tags", required=True, help="Comma-separated kebab-case tags")
    parser.add_argument("--type", default="article", help="Link type passed to add_link.py")
    parser.add_argument("--date", help="Added date, YYYY-MM-DD. Defaults to add_link.py's today.")
    parser.add_argument("--no-fetch", action="store_true", help="Pass --no-fetch to add_link.py")
    parser.add_argument("--base", default="master", help="Base branch to update and PR against")
    parser.add_argument("--branch", help="Branch name. Defaults to addlink/<slugified title>")
    parser.add_argument("--remote", default="origin", help="Git remote name")
    parser.add_argument("--dry-run", action="store_true", help="Print the command plan without running it")
    return parser.parse_args(argv)


def addlink_command(args: argparse.Namespace) -> list[str]:
    command = [
        "npm",
        "run",
        "addlink",
        "--",
        args.url,
        "--title",
        args.title,
        "--description",
        args.description,
        "--category",
        args.category,
        "--tags",
        args.tags,
        "--type",
        args.type,
    ]
    if args.date:
        command.extend(["--date", args.date])
    if args.no_fetch:
        command.append("--no-fetch")
    return command


def build_command_plan(args: argparse.Namespace) -> list[list[str]]:
    branch = args.branch or branch_name(args.title, args.url)
    commit_message = f"add link: {args.title}"
    pr_title = f"Add link: {args.title}"
    pr_body = (
        "Adds a new link to `data/links.json` via the addlink workflow.\n\n"
        "Validation/test/build should pass before review."
    )

    return [
        ["git", "checkout", args.base],
        ["git", "pull", "--ff-only", args.remote, args.base],
        ["git", "checkout", "-b", branch],
        addlink_command(args),
        ["npm", "run", "validate"],
        ["npm", "test"],
        ["npm", "run", "build"],
        ["git", "add", "data/links.json"],
        ["git", "commit", "-m", commit_message],
        ["git", "push", "-u", args.remote, "HEAD"],
        [
            "gh",
            "pr",
            "create",
            "--base",
            args.base,
            "--head",
            branch,
            "--title",
            pr_title,
            "--body",
            pr_body,
        ],
    ]


def format_command(command: list[str]) -> str:
    return " ".join(command)


def run(args: argparse.Namespace, runner=subprocess.run) -> int:
    commands = build_command_plan(args)
    if args.dry_run:
        print("Dry run: addlink PR command plan")
        for command in commands:
            print(f"- {format_command(command)}")
        return 0

    for command in commands:
        print(f"$ {format_command(command)}")
        runner(command, check=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return run(args)
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: command failed with exit code {exc.returncode}: {format_command(exc.cmd)}")
        return exc.returncode or 1


if __name__ == "__main__":
    raise SystemExit(main())
