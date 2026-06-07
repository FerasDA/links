#!/usr/bin/env python3
"""Normalize link taxonomy and light text hygiene.

This helper keeps the visible site compact while improving the structured data
Hermes uses for search, filtering, add-link enrichment, and maintenance.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_DATA = Path("data/links.json")

TAG_ALIASES = {
    "agile-and-project-management": "product-agile",
    "apis": "api",
    "business-and-startup": "business-startups",
    "business-startup": "business-startups",
    "data-and-statistics": "data-statistics",
    "music-and-learning": "music-learning",
    "product": "product-agile",
    "productivity-and-management": "productivity-leadership",
}

CATEGORY_TO_TAG = {
    "AI": "ai",
    "APIs": "api",
    "Business & Startups": "business-startups",
    "Civic / Social Impact": "civic-social-impact",
    "Data & Statistics": "data-statistics",
    "Design": "design",
    "Development Tools": "development-tools",
    "Engineering & Programming": "engineering-programming",
    "Fun": "fun",
    "Interesting Reads": "interesting-reads",
    "Local / Cleveland": "cleveland",
    "Maps": "maps",
    "Media & Talks": "media-talks",
    "Music & Learning": "music-learning",
    "Product & Agile": "product-agile",
    "Productivity & Leadership": "productivity-leadership",
    "Science": "science",
}


def compact_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return re.sub(r"\s+", " ", value).strip()


def slugify_tag(value: str) -> str:
    value = compact_text(value).lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return TAG_ALIASES.get(value, value)


def normalize_tags(category: str, tags: list[Any]) -> list[str]:
    normalized: list[str] = []
    category_tag = CATEGORY_TO_TAG.get(category)
    if category_tag:
        normalized.append(category_tag)

    for tag in tags:
        if not isinstance(tag, str):
            continue
        normalized_tag = slugify_tag(tag)
        if normalized_tag:
            normalized.append(normalized_tag)

    deduped: list[str] = []
    seen: set[str] = set()
    for tag in normalized:
        if tag not in seen:
            seen.add(tag)
            deduped.append(tag)
    return deduped


def normalize_link(link: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    updated = dict(link)
    for field in ("title", "url", "description", "category", "type", "added", "status", "redirect_url", "check_error"):
        if field in updated:
            updated[field] = compact_text(updated[field])

    tags = updated.get("tags")
    if not isinstance(tags, list):
        tags = []
    category_value = updated.get("category")
    category = category_value if isinstance(category_value, str) else ""
    updated["tags"] = normalize_tags(category, tags)

    return updated, updated != link


def normalize_links(links: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    normalized: list[dict[str, Any]] = []
    changed = 0
    for link in links:
        normalized_link, did_change = normalize_link(link)
        normalized.append(normalized_link)
        if did_change:
            changed += 1
    return normalized, changed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize link categories/tags/text")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="Path to links JSON file")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    links = json.loads(args.data.read_text(encoding="utf-8"))
    if not isinstance(links, list):
        raise SystemExit("Top-level link data must be a list")

    normalized, changed = normalize_links(links)
    if args.dry_run:
        print(f"Dry run: would update {changed} links in {args.data}")
        return 0

    args.data.write_text(json.dumps(normalized, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Updated {changed} links in {args.data}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
