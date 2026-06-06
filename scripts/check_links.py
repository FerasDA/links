#!/usr/bin/env python3
"""Check links and update their reviewable status metadata.

This script is intentionally deterministic and repo-local so a scheduled GitHub
Action can run it, update data/links.json, and open a PR for review. It never
deletes links.
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, build_opener

try:
    from validate_links import load_links, validate_links
except ImportError:  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from validate_links import load_links, validate_links


@dataclass(frozen=True)
class LinkCheckResult:
    status: str
    final_url: str | None = None
    error: str | None = None


class NoRedirectProcessor(__import__("urllib.request").request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_url(url: str, method: str, timeout: float) -> tuple[int, str | None]:
    opener = build_opener(NoRedirectProcessor)
    request = Request(
        url,
        method=method,
        headers={
            "User-Agent": "links-checker/1.0 (+https://github.com/FerasDA/links)",
            "Accept": "text/html,application/xhtml+xml,application/json,text/plain,*/*",
        },
    )
    try:
        with opener.open(request, timeout=timeout) as response:  # noqa: S310 - link checker intentionally checks stored URLs
            return response.status, response.geturl()
    except HTTPError as exc:
        if exc.code in {301, 302, 303, 307, 308}:
            return exc.code, exc.headers.get("Location")
        return exc.code, None


def check_url(url: str, timeout: float = 10.0) -> LinkCheckResult:
    try:
        status_code, location = request_url(url, "HEAD", timeout)
        if status_code in {405, 403}:
            status_code, location = request_url(url, "GET", timeout)
    except (TimeoutError, URLError, socket.timeout, OSError) as exc:
        return LinkCheckResult("unknown", error=str(exc))

    if 200 <= status_code < 300:
        return LinkCheckResult("ok")

    if status_code in {301, 302, 303, 307, 308}:
        assert location is not None
        return LinkCheckResult("redirected", final_url=urljoin(url, location))

    if status_code in {401, 403, 429}:
        return LinkCheckResult("unknown", error=f"HTTP {status_code}")

    if 400 <= status_code < 600:
        return LinkCheckResult("broken", error=f"HTTP {status_code}")

    return LinkCheckResult("unknown", error=f"HTTP {status_code}")


def apply_result(link: dict, result: LinkCheckResult, checked_date: str) -> dict:
    updated = dict(link)
    updated["status"] = result.status
    updated["last_checked"] = checked_date

    if result.status == "redirected" and result.final_url:
        updated["redirect_url"] = result.final_url
    else:
        updated.pop("redirect_url", None)

    if result.error:
        updated["check_error"] = result.error
    else:
        updated.pop("check_error", None)

    return updated


def check_links(links: list[dict], checked_date: str, timeout: float, limit: int | None = None) -> tuple[list[dict], list[str]]:
    updated_links: list[dict] = []
    lines: list[str] = []

    for index, link in enumerate(links):
        if limit is not None and index >= limit:
            updated_links.append(dict(link))
            continue

        title = str(link.get("title", f"link #{index + 1}"))
        url = str(link.get("url", ""))
        result = check_url(url, timeout=timeout)
        updated_links.append(apply_result(link, result, checked_date))
        detail = f" -> {result.final_url}" if result.final_url else ""
        error = f" ({result.error})" if result.error else ""
        lines.append(f"{title}: {result.status}{detail}{error}")

    return updated_links, lines


def write_links(path: Path, links: list[dict]) -> None:
    path.write_text(json.dumps(links, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check links and update data/links.json statuses")
    parser.add_argument("--data", default="data/links.json", help="Path to links JSON file")
    parser.add_argument("--date", default=date.today().isoformat(), help="Check date, YYYY-MM-DD")
    parser.add_argument("--timeout", type=float, default=10.0, help="Per-request timeout in seconds")
    parser.add_argument("--limit", type=int, help="Check only the first N links")
    parser.add_argument("--dry-run", action="store_true", help="Report results without writing")
    args = parser.parse_args(argv)

    path = Path(args.data)
    if not path.exists():
        print(f"ERROR: {path} does not exist")
        return 1

    links = load_links(path)
    updated_links, lines = check_links(links, args.date, timeout=args.timeout, limit=args.limit)
    errors = validate_links(updated_links)
    if errors:
        print("ERROR: checked links failed validation:")
        for error in errors:
            print(f"- {error}")
        return 1

    if args.dry_run:
        print(f"Dry run: checked {len(lines)} links; no file written.")
    else:
        write_links(path, updated_links)
        print(f"Checked {len(lines)} links and updated {path}.")

    for line in lines:
        print(f"- {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
