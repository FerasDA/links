#!/usr/bin/env python3
"""Add a link entry to data/links.json.

This is the local building block for a future Hermes `/addlink <url>` flow:
Hermes can enrich the metadata, call this script, run validation/tests, and
open a PR with the resulting JSON change.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

try:
    from validate_links import ALLOWED_TYPES, load_links, normalize_url, validate_links
except ImportError:  # pragma: no cover - makes direct module execution friendlier
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from validate_links import ALLOWED_TYPES, load_links, normalize_url, validate_links


class MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_title = False
        self.title_parts: list[str] = []
        self.meta_description = ""
        self.og_title = ""
        self.og_description = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {name.lower(): value or "" for name, value in attrs}
        if tag.lower() == "title":
            self.in_title = True
            return
        if tag.lower() != "meta":
            return

        name = attrs_dict.get("name", "").lower()
        prop = attrs_dict.get("property", "").lower()
        content = clean_text(attrs_dict.get("content", ""))
        if not content:
            return
        if name == "description" and not self.meta_description:
            self.meta_description = content
        elif prop == "og:title" and not self.og_title:
            self.og_title = content
        elif prop == "og:description" and not self.og_description:
            self.og_description = content

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)

    @property
    def title(self) -> str:
        return self.og_title or clean_text(" ".join(self.title_parts))

    @property
    def description(self) -> str:
        return self.og_description or self.meta_description


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def truncate(value: str, max_length: int = 240) -> str:
    value = clean_text(value)
    if len(value) <= max_length:
        return value
    return value[: max_length - 1].rstrip() + "…"


def parse_tags(value: str) -> list[str]:
    tags: list[str] = []
    for raw in re.split(r"[,\s]+", value.strip()):
        tag = raw.strip().lower()
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def fallback_title_from_url(url: str) -> str:
    parsed = urlsplit(url)
    path = parsed.path.rstrip("/")
    candidate = path.rsplit("/", 1)[-1] if path else parsed.netloc
    candidate = re.sub(r"[-_]+", " ", candidate)
    candidate = re.sub(r"\.[a-zA-Z0-9]{1,6}$", "", candidate)
    return clean_text(candidate).title() or parsed.netloc


def fetch_metadata(url: str, timeout: float = 10.0) -> dict[str, str]:
    request = Request(
        url,
        headers={
            "User-Agent": "links-add-link/1.0 (+https://github.com/FerasDA/links)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - user-provided URL for personal CLI tool
            content_type = response.headers.get("Content-Type", "")
            if "html" not in content_type.lower():
                return {}
            body = response.read(512_000).decode(response.headers.get_content_charset() or "utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError, OSError):
        return {}

    parser = MetadataParser()
    parser.feed(body)
    return {
        "title": parser.title,
        "description": truncate(parser.description),
    }


def build_link(args: argparse.Namespace) -> dict:
    metadata = {} if args.no_fetch else fetch_metadata(args.url)
    title = clean_text(args.title or metadata.get("title", "") or fallback_title_from_url(args.url))
    description = truncate(args.description or metadata.get("description", "") or f"Saved web link from {urlsplit(args.url).netloc}.")
    category = clean_text(args.category or "Interesting Reads")
    tags = parse_tags(args.tags or "interesting-reads")

    return {
        "title": title,
        "url": args.url.strip(),
        "description": description,
        "category": category,
        "tags": tags,
        "type": args.type,
        "added": args.date,
        "status": "unchecked",
    }


def add_link(path: Path, new_link: dict) -> tuple[list[dict], list[str]]:
    links = load_links(path)
    normalized_new_url = normalize_url(new_link["url"])
    for existing in links:
        if normalize_url(existing.get("url", "")) == normalized_new_url:
            return links, [f"duplicate normalized url: {normalized_new_url}"]

    updated = [*links, new_link]
    return updated, validate_links(updated)


def write_links(path: Path, links: list[dict]) -> None:
    path.write_text(json.dumps(links, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Add one link to data/links.json")
    parser.add_argument("url", help="HTTP(S) URL to add")
    parser.add_argument("--data", default="data/links.json", help="Path to links JSON file")
    parser.add_argument("--title", help="Link title. If omitted, fetches page metadata or derives from URL.")
    parser.add_argument("--description", help="Short description. If omitted, fetches page metadata or uses a fallback.")
    parser.add_argument("--category", help="Display category. Defaults to Interesting Reads.")
    parser.add_argument("--tags", help="Comma- or space-separated kebab-case tags. Defaults to interesting-reads.")
    parser.add_argument("--type", default="article", choices=sorted(ALLOWED_TYPES), help="Link type")
    parser.add_argument("--date", default=date.today().isoformat(), help="Added date, YYYY-MM-DD")
    parser.add_argument("--no-fetch", action="store_true", help="Do not fetch page metadata")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print the new link without writing")
    args = parser.parse_args(argv)

    path = Path(args.data)
    if not path.exists():
        print(f"ERROR: {path} does not exist")
        return 1

    new_link = build_link(args)
    updated, errors = add_link(path, new_link)
    if errors:
        print("ERROR: could not add link:")
        for error in errors:
            print(f"- {error}")
        return 1

    if args.dry_run:
        print("Dry run OK. Link would be added:")
        print(json.dumps(new_link, indent=2, ensure_ascii=False))
        return 0

    write_links(path, updated)
    print(f"Added {new_link['title']} to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
