#!/usr/bin/env python3
"""Validate the structured link data used by the Astro site."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ALLOWED_STATUSES = {"unchecked", "ok", "redirected", "broken", "unknown"}
ALLOWED_TYPES = {"article", "tool", "video", "repo", "api", "dataset", "document", "other"}
TAG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def load_links(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("top-level JSON value must be a list")
    return data


def normalize_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    scheme = parsed.scheme.lower()
    host = parsed.netloc.lower()
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")

    tracking_prefixes = ("utm_",)
    tracking_names = {"fbclid", "gclid", "mc_cid", "mc_eid"}
    kept_params = []
    for part in parsed.query.split("&") if parsed.query else []:
        name = part.split("=", 1)[0].lower()
        if name in tracking_names or any(name.startswith(prefix) for prefix in tracking_prefixes):
            continue
        kept_params.append(part)
    query = "&".join(sorted(kept_params))

    return urlunsplit((scheme, host, path, query, ""))


def validate_date(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def validate_url(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    parsed = urlsplit(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate_links(links: list[dict]) -> list[str]:
    errors: list[str] = []
    seen_urls: dict[str, int] = {}
    category_counts: defaultdict[str, int] = defaultdict(int)

    for index, link in enumerate(links, start=1):
        prefix = f"link #{index}"
        if not isinstance(link, dict):
            errors.append(f"{prefix}: entry must be an object")
            continue

        title = link.get("title")
        url = link.get("url")
        description = link.get("description")
        category = link.get("category")
        tags = link.get("tags")
        added = link.get("added")
        status = link.get("status")
        link_type = link.get("type")

        if not isinstance(title, str) or not title.strip():
            errors.append(f"{prefix}: title is required")

        if not validate_url(url):
            errors.append(f"{prefix}: url must be an http(s) URL")
        else:
            assert isinstance(url, str)
            normalized = normalize_url(url)
            if normalized in seen_urls:
                errors.append(
                    f"{prefix}: duplicate normalized url also used by link #{seen_urls[normalized]}: {normalized}"
                )
            else:
                seen_urls[normalized] = index

        if not isinstance(description, str) or not description.strip():
            errors.append(f"{prefix}: description is required")
        elif len(description) > 240:
            errors.append(f"{prefix}: description should be 240 characters or fewer")

        if not isinstance(category, str) or not category.strip():
            errors.append(f"{prefix}: category is required")
        else:
            category_counts[category] += 1

        if not isinstance(tags, list) or not tags:
            errors.append(f"{prefix}: tags must be a non-empty list")
        else:
            for tag in tags:
                if not isinstance(tag, str) or not TAG_RE.match(tag):
                    errors.append(f"{prefix}: tag {tag!r} must be lowercase kebab-case")

        if not validate_date(added):
            errors.append(f"{prefix}: added must be an ISO date like 2026-06-06")

        if status not in ALLOWED_STATUSES:
            errors.append(f"{prefix}: status must be one of {', '.join(sorted(ALLOWED_STATUSES))}")

        if link_type not in ALLOWED_TYPES:
            errors.append(f"{prefix}: type must be one of {', '.join(sorted(ALLOWED_TYPES))}")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate data/links.json")
    parser.add_argument(
        "path",
        nargs="?",
        default="data/links.json",
        help="Path to links JSON file (default: data/links.json)",
    )
    args = parser.parse_args(argv)

    path = Path(args.path)
    if not path.exists():
        print(f"ERROR: {path} does not exist")
        return 1

    try:
        links = load_links(path)
        errors = validate_links(links)
    except Exception as exc:  # noqa: BLE001 - command-line diagnostics
        print(f"ERROR: {exc}")
        return 1

    if errors:
        print(f"Validation failed for {path}:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Validated {len(links)} links in {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
